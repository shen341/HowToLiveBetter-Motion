# ADR-017: 原生 CDP 文件上传注入与多语言 DOM 容灾架构

## 1. 状态
**已接受 (Accepted)** - 2026-10-13

## 2. 背景与问题陈述
在 HowToLiveBetter-Motion 的多模态生图与图生视频 (I2V) 流水线中，主路由通过反向代理网关 `https://yourselfai.org/muse/v1` 调用远端无头 Chromium 驱动的 `muse2api` 服务。

在近期实际生成与测试过程中，管理后台出现全账号标红报警：
1. **报错现象**：
   - 账号池内多个账号批量显示 `任务异常: 参考图上传未确认，已停止生成`。
   - 伴随出现 `任务异常: 提示词发送未确认，已停止生成`。
   - 下游客户端因全局锁 (`GEN_LOCK`) 长时间被失败任务霸占而遭遇 `Request timed out....`。
2. **根本原因追溯**：
   - **浏览器安全沙箱拦截前端 JS 注入**：旧版 `_attach_image` 使用网页端 JavaScript `DataTransfer` 模拟向 `<input type="file">` 赋值（`input.files = dt.files`）。现代 Chromium 实施了严格的输入保护策略，在非真实用户交互（Drag & Drop）脚本执行流中，程序化对 `input.files` 的赋值会被浏览器 C++ 内核静默丢弃，导致 `input.files.length` 恒为 0，页面未能触发上传。
   - **DOM 结构与多语言差异漂移**：
     - 远端 muse.ai 更新后，composer 输入区移除了外层 `<form>` 标签包裹，导致原有基于 `closest('form')` 的选择器全部返回 `null`。
     - 确认按钮的选择器仅匹配中英双语（`remove attachment`/`移除附件`），在绑定日文语言偏好的账号下（`添付ファイルを削除`/`添付`）无法被检测到。
     - 发送按钮在日文 UI 下为 `aria-label="送信"`，旧版正则 `/发送|send/i` 无法命中，且回退的合成 Enter 键因 React 受控状态未被清空而无法提交，抛出 `提示词发送未确认`。
   - **账号池多米诺骨牌连锁污染**：单任务遇到上传异常失败后，服务端自动切号重试机制连续尝试池内下一个账号，导致池内所有账号相继失败并持久化错误 Note，给管理员造成“所有账号均失效”的严重错觉。

---

## 3. 架构设计与技术方案

### 3.1 原生 CDP 协议文件注入 (DOM.setFileInputFiles)
彻底淘汰不可靠的 DOM 级 JavaScript `DataTransfer` 模拟，改为借助 Chrome DevTools Protocol (CDP) 的底层调试权限：
1. **临时落盘**：服务端接收 Base64/URL 参考图后，按真实 MIME 校验并暂存为容器内物理文件（如 `/data/tmp_uploads/ref_xxx.png`）；
2. **定位输入节点**：通过 `Runtime.evaluate` 获取目标 `<input type="file">` 的 `RemoteObjectId`；
3. **CDP 原生挂载**：调用 `DOM.setFileInputFiles`，由 Chromium 浏览器底层直接将物理文件路径挂载至文件输入节点：
   ```python
   self.page.send("DOM.enable")
   self.page.send("DOM.setFileInputFiles", {
       "files": [tmp_file_path],
       "objectId": obj_id
   })
   ```
4. **事件补偿与生命周期管理**：挂载后主动向节点派发 `change` 与 `input` 冒泡事件触发 React SyntheticEvent 调度，并在 `finally` 块中立即安全删除临时文件，防止磁盘碎片泄漏。

### 3.2 全模态与多语言 DOM 韧性适配 (Multilingual Resilience)
全面升级 DOM 查询器，支持中/英/日三语及无标签图标按钮兜底：
- **发送按钮识别**：
  ```javascript
  return /发送|send|送信/i.test(al)
      || /发送|send|送信/i.test(tid)
      || /^(发送|send|送信)$/i.test(txt);
  ```
  若仍未匹配，向上寻找输入容器内的末尾提交操作按钮（排除附件按钮）。
- **附件清除与确认**：
  扩展匹配 `/remove\s*attachment|移除附件|删除附件|添付ファイルを削除|添付|remove/i`；同时以 `inp.files.length > 0` 和缩略图作为双重确认兜底，彻底杜绝虚假超时。
- **停止按钮与下载按钮**：
  补齐日文 `ストップ`、`ダウンロード` 识别，确保生成结束检测与媒体下载 100% 畅通。

### 3.3 账号池状态防护与空值清洗
- **入参空值防御**：在 `/v1/images/generations` 与 `/v1/videos` 顶层统一清洗 `reference_image` / `image`，若为空字符串或空白字符直接重置为 `None`，防止文本任务误入带图逻辑。
- **自动恢复与保活**：引入自动保活守护进程定期巡检唤醒 VM，当账号成功产出结果时立即自动清除旧有异常 Note，恢复健康绿色状态。

### 3.4 交互式建议按钮自动嗅探采纳与源头合规化 (Self-Healing Auto-Click & Safety Guardrails)
针对 Meta Hatch 在生图敏感词拦截后返回建议选项卡（如 `生成替代版：倒扣的空烟灰缸 + 胸片 + 窗光`，提示“点下面就行”）的场景，实施端到端闭环方案：
1. **反代引擎自动嗅探并点击（Self-Healing Auto-Click）**：
   在 `_wait_attachment` 轮询中注入探测脚本，自动寻找未禁用的建议交互按钮：
   ```javascript
   var suggestionBtn = candidateButtons.find(function(b) {
       if (b.getAttribute('data-selected') === 'true' || b.getAttribute('aria-disabled') === 'true') return false;
       var t = (b.innerText || '').trim();
       return /生成替代版|替代版|换个方向|尝试此方案|生成建议|Try alternative|代替バージョン|別の方向性/i.test(t);
   });
   if (suggestionBtn) {
       suggestionBtn.click();
       suggestionBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
   }
   ```
   检测并点击后，服务端自动延长 120 秒超时并开启 35 秒宽限期（`suggestion_grace_until`），暂时抑制纯文本快速失败检查，确保模型有充分时间执行替代生图。
2. **上游分镜提示词源头合规化（Prompt Safety Filter Avoidance）**：
   在 `src/prompt_builder.py` 补充第 8 条规则，从源头禁止在 `image_prompt` 中直接出现烟草/吸烟（`cigarette`, `smoking`, `ashtray filled with ashes`）、创伤血液（`blood`, `wound`）等高危词，强制转化为“倒扣洁净空烟灰缸”、“无烟生活日历”、“温和问诊报告”等积极合规意象。

---

## 4. 实施验证结果

| 测试项 | 测试路径 | 耗时 | 验证结果 |
| :--- | :--- | :--- | :--- |
| **文本对话 (Muse-Spark)** | `/v1/chat/completions` | **22.2s** | **200 OK**（准确回答，热重启后首调正常） |
| **超清生图 (Muse-Image)** | `/v1/images/generations` | **53.3s** | **200 OK**（生成 1024×1792 WebP 并正常落盘） |
| **CDP 文件注入** | `DOM.setFileInputFiles` | **< 0.5s** | **成功**（Chromium 原生挂载，触发 React 上传） |
| **多语言界面兼容** | 日文账号 `c1daa6ab9039` 等 | 立即响应 | **成功识别 `送信` / `添付` 按钮** |
| **建议按钮自动采纳** | `_wait_attachment` 探针 | **< 1.0s** | **成功**（自动点击“生成替代版”，防断连防超时） |
| **账号池状态** | 5 个账号全景监测 | 持续 | **全绿恢复**（`healthy: 5, error: 0`） |

---

## 5. 影响与后续考量
- **稳定性**：彻底攻克了多模态生图与图生视频因底层权限与审核拒答建议导致的卡死瓶颈。
- **自动化完整性**：消除了“模型出建议、人工去点选”的半自动化痛点，真正实现无人值守。
- **资源开销**：临时文件即用即销，对服务器磁盘零侵占。
- **排障成本**：消除了“一人报错、全池连坐”的误报污染，运维看板真实反映账号健康度。
