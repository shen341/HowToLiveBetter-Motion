# ADR-016: muse2api 反代接口超时窗口适配与 Agent 记忆隔离架构 (Muse2API Reverse-Proxy Timeout Adaptation and Agent Memory Isolation Architecture)

## 状态 (Status)
**Accepted (已采纳实施)**

## 日期 (Date)
2026-10-13

## 背景与问题上下文 (Context)

在执行短视频自动化流水线 `python 02_ai_generator.py --limit 3` 批量跑批时，主线路 `https://yourselfai.org/muse/v1` 的两个核心模型（文本分镜 `muse-spark` 与文生图原画 `muse-image`）连续出现调用失败与连锁超时现象：

```text
🧠 [步骤 1/3] 正在调用大模型生成结构化分镜脚本...
   ⚠️ [Muse-Spark] 遇到瞬时异常或限流 (第 1/2 次): Request timed out....
      ⏳ 正在启动指数退避重试，休眠 2.45s 后自动重试...
⚠️ [主线路 Muse-Spark] 遇到限速/拥堵或调用异常: Request timed out..
🔄 [容灾切换] 启动备选大模型: https://yourselfai.org/v1 [模型: gemini-3.8-flash-high] 生成结构化分镜脚本...
   ✅ [备选线路] 成功通过 gemini-3.8-flash-high 生成分镜脚本！(耗时 119.5s)
🎨 [步骤 2/3] 正在批量生成多模态视觉分镜与 TTS 语音讲解...
   🖼️ [分镜 1/6] 浮现字:「无防护裸奔？」 | 旁白: 以为体检过就万事大吉？...
      🎨 正在调用 Muse-Image 绘制 1024x1792 原画...
   ⚠️ [Muse-Image] 遇到瞬时异常或限流 (第 1/2 次): Request timed out....
```

同时，在远端 `muse.ai` 网页端控制台捕获到反常的错误状态（伴随红色 `エラー` 标识）：
```text
Updated ~/MEMORY.md with rule entry 01_013
Edited /home/hatch/MEMORY.md to append entry 01_013 on 2026-10-13 to the Chinese brief fidelity rule.
Change:
old_text: ...entries 01_004 on 2026-10-11, 01_005 on 2026-10-12, 01_010 儿童安全座椅 on 2026-10-12).
new_text: ...entries 01_004 on 2026-10-11, 01_005 on 2026-10-12, 01_010 儿童安全座椅 on 2026-10-12, 01_013 on 2026-10-13).
Result: File updated successfully at /home/hatch/MEMORY.md. File type: markdown. No pi_check required.
```

### 深度归因剖析 (Root Cause Analysis)

经连接 VPS 服务器（`160.251.230.41`）全面审计无头 Chromium、Docker 容器与反代代码，定位到以下相互交织的根因链：

1. **客户端超时阈值（45s）严重低于多模态生成周期**：
   - 客户端 `.env` 与 `src/config.py` 将 `API_TIMEOUT_SECONDS` 硬编码为 `45.0s`；
   - 生成 6 幕包含画风决策、提示词和长旁白的结构化 JSON 分镜（1200+ tokens）实测需 **40~120 秒**（下游即使用 Gemini 官方直连亦耗时 119.5s）；
   - 生成 1024×1792 竖屏超清原画经过 CDP 调度需 **35~85 秒**；
   - 客户端在第 45.0 秒强行断开并抛出 `Request timed out`，此时服务端仍在全速渲染或即将交付。
2. **Chromium 排他锁 (`GEN_LOCK`) 导致“多米诺骨牌式”连环死等**：
   - `muse2api` 采用单无头 Chromium 实例，文本与生图共用 `GEN_LOCK` 串行执行；
   - 客户端第 45 秒主动弃连后，服务端任务仍在后台占用 `GEN_LOCK`；客户端重试以及紧接着的 `Muse-Image` 请求到达服务端时必须排队等锁，进而连锁触发下一次 45s 超时。
3. **会话历史污染引发远端 Agent 擅自执行工具（`MEMORY.md` 写记忆）**：
   - `muse.ai` 底层运行在 `/home/hatch` 的 Autonomous Agent 环境，具备 Bash 与文件修改工具；
   - 服务端原 `engine.py` 的 `reset_thread(for_chat=True)` 允许在气泡少于 24 个时复用旧会话；批量跑批（01_004、01_005、01_010、01_013）使旧上下文累积了大量规则；
   - 远端 Agent 误以为这是持续性工程任务，擅自调用工具修改 `/home/hatch/MEMORY.md` 记录规则演进，工具在沙盒执行报错，期间前端未输出正文气泡，导致服务端首字探测器空等超时。
4. **服务端首字探测超时死限过低**：
   - `engine.py` 内部硬编码 `first_token_deadline = min(deadline, t_sent + 40.0)`，对复杂推理或大 JSON 分镜而言，40 秒容易在模型输出首字符前被服务端误判为超时而强行切断。

---

## 架构决策 (Decision)

### 1. 客户端超时窗口科学适配 (`API_TIMEOUT_SECONDS=180.0`)
- 在客户端 `.env` 与 `src/config.py` 中，将 `API_TIMEOUT_SECONDS` 从 `45.0` 全面升级为 **`180.0`**（秒）；
- 给予下游 `OpenAI` SDK 与 HTTPX 充分的等待窗口，无缝覆盖复杂分镜推理（40~120s）与大图生成（35~85s），避免过早腰斩正常运行的服务端连接。

### 2. 服务端强制全量会话隔离 (`reset_thread` 统一开辟新会话)
- 修改 VPS 服务端 `/opt/muse2api/engine.py`：
  ```javascript
  // 修改前：纯文本对话在气泡少于 24 个时不重置，导致上下文累积与 Agent 跑偏
  if (forChat) {
      return bubbleCount >= 24;
  }
  return (window.location.pathname !== '/thread/new') || bubbleCount > 0;

  // 修改后：无论文本还是生图，只要存在历史气泡即必须导航至 /thread/new
  if (hasStop || hasStuck || hasAtts) return true;
  return (window.location.pathname !== '/thread/new') || bubbleCount > 0;
  ```
- **核心收益**：
  - 彻底阻断跨条目的历史上下文污染；
  - 远端 Agent 每次接收到的均为独立、纯净的新会话，不再触发维护 `MEMORY.md` 的后台规则演化子任务；
  - 规避 Chromium 标签页 DOM 节点随会话累积而引发的内存泄漏与渲染迟滞。实测在保持 Cookie 热态下导航到 `/thread/new` 仅耗时 **0.04 秒**。

### 3. 首字响应死限扩容与服务端异常日志透明化
- 修改 `/opt/muse2api/engine.py`：
  - 将 `first_token_deadline` 从 `t_sent + 40.0` 扩容至 **`t_sent + 120.0`**，保障复杂 JSON 结构化输出前期规划思考时不被误杀。
- 修改 `/opt/muse2api/app.py`：
  - 在 `safe_chat_stream` 捕获异常处显式打印 `log.warning("【对话异常】账号 %s (attempt %d): %s", cur_id, attempt, exc)`，杜绝吞异常隐蔽行为。

### 4. 提示词端强化纯文本直出与防 Agent 跑偏铁律
- 在 `src/prompt_builder.py` 的 System Prompt 与 User Prompt 尾部双重加固约束：
  ```text
  【强制输出与抑制工具约束】:
  请直接以纯文本 JSON 格式输出短视频分镜脚本，禁止调用任何系统工具、不要更新规则记忆文件（严禁编辑任何 MEMORY.md），直接回复最终内容。
  ```

---

## 落地验证结果 (Verification)

补丁生效后，通过独立脚本对 `https://yourselfai.org/muse/v1` 线上生产接口进行端到端全链路实测：

1. **Muse-Spark（文本对话流式）**：
   - HTTP 状态码：`200 OK`（首包耗时 0.24s）；
   - 流式内容输出正常，零 `MEMORY.md` 干扰，总耗时 **44.20 秒** 完成；
2. **Muse-Image（1024×1792 超清原画生成）**：
   - HTTP 状态码：`200 OK`，耗时 **86.47 秒**；
   - 成功交付交付原画资源：`https://yourselfai.org/muse/v1/media/f3dcb9ebaa7e46e4a8fa803a1660f659.webp`（大小 516KB）；
3. **稳定性验证**：
   - 两项测试连续串行发起，`GEN_LOCK` 释放与会话清理极其平滑，无卡死、无死锁、无排队积压。

---

## 影响评估与后续运维指南 (Consequences)

- **积极影响**：
  - 彻底解决了批量跑批时主线路频繁退避降级的问题；
  - 客户端无需额外并发开销，单人自用模式下账号复用率与热备稳定性显著提升；
  - 杜绝了 muse.ai 远端账户因过多写入无意义 `MEMORY.md` 而导致沙盒报错的隐患。
- **运维规范建议**：
  - 若未来单台 VPS 物理内存仍受制于 1.7GB，切勿开启高并发生图调用，严格保持主任务串行或微并发（RPM 控制在 15~30 之间）；
  - 长期若业务规模扩大，建议依据构建手册将 VPS 物理内存升配至 4GB~8GB，彻底消除 Swap 换页抖动。
