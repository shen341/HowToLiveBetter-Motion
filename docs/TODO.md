# HowToLiveBetter-Motion 项目任务与演进路线图 (TODO & Roadmap)

> 本文档依据 [`documentation-and-adrs`](file:///C:/Users/13700-4070/.gemini/config/plugins/agent-skills/skills/documentation-and-adrs/SKILL.md) 规范维护。文档不仅记录“要做什么 (What)”，更沉淀关键任务的**背景上下文 (Context)、架构决策依据 (Why / ADR Mapping)、权衡取舍 (Trade-offs) 与验收标准 (Acceptance Criteria)**，确保工程演进历史对人类开发者与 AI Agent 均具备高度可追溯性。

---

## 📊 里程碑整体进度概览 (Milestone Overview)

```
[Milestone 1] 核心基建与数据抽取   [████████████████████] 100% (已完成 · 2026-10-11)
[Milestone 2] 视觉美学与影视级组装 [████████████████████] 100% (已完成 · 2026-10-11)
[Milestone 3] 语音解说与智能选风   [████████████████████] 100% (已完成 · 2026-10-11)
[Milestone 4] 批量生产、质检与平台化 [████████████████████] 100% (已完成 · 2026-10-12)
[Milestone 5] 人工审核工作台与混合微动 [███████████████░░░░░]  75% (进行中 · 2026-10-12)
```

---

## 🏛️ 架构决策追溯矩阵 (Architecture Decision Traceability Matrix)

项目中每一项核心能力与重大变更均有对应的 ADR（架构决策记录）提供决策背景与备选方案评估，确保关键设计不可反悔且随时可查：

| ADR 编号 | 决策标题 | 对应里程碑 / 模块 | 决策状态 | 核心权衡与设计原因 (The "Why") |
|---|---|---|---|---|
| [ADR-001](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-001-Dual-State-Persistence-SQLite-and-JSON.md) | 双轨状态持久化架构 | Milestone 1 (`src/db.py`) | **Accepted** | 采用 SQLite 支撑行级锁事务并发与断点续传；镜像导出 `progress.json` 保证人类与 Agent 纯文本可读性。 |
| [ADR-002](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-002-Huashu-Art-Motion-Style-Cards-and-Prompt-Engineering.md) | huashu-art-motion 美学与防 AI Slop | Milestone 2 (`src/prompt_builder.py`) | **Accepted** | 硬编码排斥蓝紫霓虹/抽象悬浮等低质 AI 感；强制锁定具象物理载体与微动作，保障科普严肃性。 |
| [ADR-003](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-003-MoviePy-and-Pillow-Video-Assembly-Architecture.md) | 视频组装引擎与黄金分割排版 | Milestone 2 (`src/assembler.py`) | **Accepted** | 废除 Windows 易崩溃的 ImageMagick 外部依赖，采用纯 Pillow 渲染；文字放置于黄金分割点彻底避开手机 UI 遮挡。 |
| [ADR-004](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-004-Edge-TTS-Integration-and-Audio-Driven-Timing.md) | Edge-TTS 接入与「以声定景」同步 | Milestone 3 (`src/tts_client.py`) | **Accepted** | 接入云泽沉稳男声；以实际音频时长反向决定分镜画面展示时长（$T_{scene} = T_{audio} + 0.5\text{s}$），彻底根绝音画脱节。 |
| [ADR-005](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-005-Custom-BGM-Directory-and-Audibility-Mixing.md) | 自定义背景音乐与弱音混音 | Milestone 3 (`backgroup_music/`) | **Accepted** | 支持任意外部 MP3 拖入即用；音量限制在 0.09 (-20dB) 舒适弱音，纯衬底绝不干扰口播理解。 |
| [ADR-006](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-006-Autonomous-Visual-Style-Selection.md) | AI 语义理解自主选风与风格调度 | Milestone 3 (`src/prompt_builder.py`) | **Accepted** | 赋予大模型导演级决策权，根据条目情绪基调从 7 种风格卡中自主匹配最合适画风，并沉淀决策依据。 |
| [ADR-007](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-007-Cover-Card-Generation-Architecture.md) | 竖屏专属封面卡片自动生成架构 | Milestone 4 (`src/cover_generator.py`) | **Accepted** | 解决视频首帧自然截图 CTR 低与信息不清晰痛点；生成 1080×1920 竖屏专属封面，集成大字标题与 3 维度硬核标签。 |
| [ADR-008](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-008-Golden-6-Scenes-Narrative-Pulse-Rhythm.md) | 黄金 6 幕叙事脉冲曲线与节律升级 | Milestone 2 (`02_ai_generator.py`) | **Accepted** | 淘汰单张图长停 8 秒的死板幻灯片感；确立 6 阶段完整论证闭环（单镜头 4.0~5.2s），总时长稳定在 28~32s。 |
| [ADR-009](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-009-Standalone-SRT-Subtitle-Architecture.md) | 独立外挂 SRT 字幕导出引擎 | Milestone 4 (`src/srt_generator.py`) | **Accepted** | 契合 MoviePy 转场叠化精准计算毫秒级物理波形时间戳；支持分镜级与断句级双模式，交付同名软字幕供剪映精修。 |
| [ADR-010](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-010-I2V-Hybrid-Motion-Architecture.md) | 图生视频 (I2V) 混合微动演进路线 | Milestone 5 (`src/assembler.py` / `src/muse_client.py`) | **Accepted** | 首帧原画锁定画风底色，局部关键镜启用 I2V 物理微动，尾帧自适应定格呼吸 (Freeze-and-Drift)，兼顾视觉动效、画风可控与批量成本。 |
| [ADR-011](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-011-Rate-Limiting-and-Exponential-Backoff.md) | 令牌桶速率控制与多级指数退避重试容灾架构 | Milestone 4 (`src/rate_limiter.py`) | **Accepted** | 纯 Python 实现线程安全 TokenBucketLimiter 限制发包并发，智能分类 429/503/超时异常执行 2s->4s->8s 指数退避，保障大批量跑批稳定性。 |
| [ADR-012](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-012-Social-Platform-Bitrate-Presets.md) | 社交平台码率自适应压缩与流式秒开预设架构 | Milestone 4 (`src/assembler.py`) | **Accepted** | 建立小红书抗二压、抖音高清、微信秒开等 CRF+VBV 平台矩阵预设，注入 movflags=+faststart 元数据实现移动端流式秒开。 |
| [ADR-013](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-013-Web-Review-Dashboard-Architecture.md) | 轻量级 Web 审核看板与人机协作质检架构 | Milestone 5 (`04_review_dashboard.py`) | **Accepted** | 基于 Streamlit 构建本地直观看板，展示成片播放器、封面、SRT、分镜微动排查矩阵，提供一键审核通过与工单流转。 |
| [ADR-014](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-014-Social-Copywriting-and-Hashtags-Engine.md) | 多平台爆款营销文案与高权重标签生成引擎架构 | Milestone 5 (`src/copywriter.py`) | **Accepted** | 面向小红书、抖音、微信视频号构建定制化提示词模板与清洗引擎，交付同名 _copywriting.txt 运营四件套并在 Web 看板一键复制。 |

---

## 🏆 已完成里程碑与技术交付 (Completed Milestones & Deliverables)

### Milestone 1: 核心基建与数据持久化 (Phase 1)
*关联决策：[ADR-001](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-001-Dual-State-Persistence-SQLite-and-JSON.md)*
- [x] **数据自动拉取与 AST 精准抽取**：自动拉取 `HowToLiveBetter` 仓库，正则 + AST 解析 34 章节、677 条完整生活建议（`01_data_extractor.py`）。
- [x] **双轨状态机与并发持久化**：SQLite 数据库 `pipeline.db`（支持事务行锁与状态流转机）+ 自动导出的 `progress.json` 纯文本快照（`src/db.py`）。
- [x] **断点续传与幂等性保障**：支持随时中断，重启后自动过滤 `Pending` 条目继续执行，提供 `--force` 强制全量重置。

### Milestone 2: 视觉美学、运镜与影视级组装 (Phase 2)
*关联决策：[ADR-002](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-002-Huashu-Art-Motion-Style-Cards-and-Prompt-Engineering.md), [ADR-003](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-003-MoviePy-and-Pillow-Video-Assembly-Architecture.md), [ADR-008](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-008-Golden-6-Scenes-Narrative-Pulse-Rhythm.md)*
- [x] **huashu-art-motion 提示词工程**：落地防 AI Slop 铁律，负向排除霓虹紫/抽象球，强制要求具体的物理物件与微动作（`src/prompt_builder.py`）。
- [x] **纯 Python Pillow 抗锯齿排版引擎**：彻底摒弃 ImageMagick 依赖，自动发现 Windows 微软雅黑与思源黑体，支持多行排版、圆角磨砂胶囊框与投影渲染。
- [x] **竖屏黄金分割视觉防遮挡布局**：上部黄金分割点（$Y \approx 733\text{px}$）放置琥珀金浮现大字徽章；下部黄金分割点（$Y \approx 1186\text{px}$）放置旁白解说胶囊，彻底避开抖音/小红书底部交互 UI。
- [x] **Ken Burns 连续运镜与 0.5s 叠化转场**：矩阵式实现 `zoom_in`、`zoom_out`、`pan_left`、`pan_right` 与相邻镜头交叉溶解。
- [x] **黄金 6 幕叙事脉冲曲线升级**：全片由 4 幕扩充为 6 幕紧凑剪辑（单镜头 4.0~5.2s），形成“痛点 $\to$ 颠覆 $\to$ 机理 $\to$ 证据 $\to$ 成本 $\to$ 金句”完整论证闭环，全片 28~32s（[ADR-008](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-008-Golden-6-Scenes-Narrative-Pulse-Rhythm.md)）。

### Milestone 3: 沉浸式语音解说与智能自主选风 (Phase 3)
*关联决策：[ADR-004](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-004-Edge-TTS-Integration-and-Audio-Driven-Timing.md), [ADR-005](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-005-Custom-BGM-Directory-and-Audibility-Mixing.md), [ADR-006](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-006-Autonomous-Visual-Style-Selection.md)*
- [x] **Cloudflare Edge-TTS 专有服务集成**：调用 `zh-CN-YunzeNeural` 沉稳男声，生成高公信力专业口播音频流（`src/tts_client.py`）。
- [x] **“以声定景”毫秒级动态音画同步**：以 TTS 真实音频时长 $T_{audio} + 0.5\text{s}$ 反向驱动分镜画面展示时长，杜绝音画不同步。
- [x] **自定义 BGM 目录与弱音侧链混音**：检索 `backgroup_music/` 目录，限制弱音倍率 0.09 (-20dB)，配合 1.0s 淡入与 2.0s 淡出，突出人声主体。
- [x] **AI 语义理解自主选风引擎**：内置 7 种风格配方卡（吉卜力、Vox剪报、Kurzgesagt矢量、波普、霍珀现实主义、水墨、像素风），`muse-spark` 依据内容情绪自主决策并说明理由。

### Milestone 4: 批量生产与平台化交付 (Phase 4 完美收官)
*关联决策：[ADR-007](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-007-Cover-Card-Generation-Architecture.md), [ADR-009](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-009-Standalone-SRT-Subtitle-Architecture.md), [ADR-011](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-011-Rate-Limiting-and-Exponential-Backoff.md), [ADR-012](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-012-Social-Platform-Bitrate-Presets.md)*
- [x] **TASK-4.1 短视频专属封面卡片自动生成引擎 (Cover Card)**：实现 1080×1920 竖屏高辨识度封面卡片（`src/cover_generator.py`），生成首图发布卡，产物输出至 `output/final_videos/{id}_cover.png`。
- [x] **TASK-4.2 独立外挂 SRT 字幕导出引擎 (Standalone SRT)**：实现毫秒级绝对时间轴对齐引擎（`src/srt_generator.py`），支持分镜级与断句级双模式，导出同名 `{clean_name}.srt` 软字幕，剪映开箱即用。
- [x] **TASK-4.3 批量生成速率控制与指数退避重试 (Rate Limiting & Backoff)**：实现基于线程安全 TokenBucket 算法的请求限流器与指数退避执行器（`src/rate_limiter.py`）。智能分类 HTTP 429/500/502/503/504 与超时异常，按 $2\text{s} \to 4\text{s} \to 8\text{s}$ 自动重试并加 Jitter 抖动，支持 `Retry-After`，并在 `02_ai_generator.py` 中支持命令行参数调度（`--rpm-muse`, `--rpm-tts`, `--max-retries`），单元测试通过（[ADR-011](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-011-Rate-Limiting-and-Exponential-Backoff.md)）。
- [x] **TASK-4.4 社交平台码率自适应压缩预设 (Platform Preset Compression)**：实现各大主流平台（小红书 `xhs`、抖音 `douyin`、微信视频号 `wechat`、B站 `bilibili`、通用 `default`）码率参数矩阵库。采用 CRF（19~22）+ VBV 峰值限速双控，将 30s 成片严格锁死在 **10~20MB** 最优画质与传输区间；强制注入 `-movflags +faststart` 前置元数据实现移动端流式秒开播放；规范 8-bit YUV420P 消除黑屏兼容故障；支持 `--preset` 命令行调度与单元测试（[ADR-012](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-012-Social-Platform-Bitrate-Presets.md)）。

---

## 🚀 进行中与近期高优先任务 (Active & Near-Term Backlog)

### Milestone 5: 人工审核工作台、混合动效与自动化分发 (当前重点阶段)

| 任务编号 | 任务标题 | 优先级 | 状态 | 估算工时 | 关联 ADR / 模块 | 核心背景与验收标准 (Acceptance Criteria) |
|---|---|---|---|---|---|---|
| **TASK-5.0** | **图生视频 (I2V) 混合动态微动流水线试验 (Hybrid Motion Pipeline)** | P2 (中) | **已完成**<br>(2026-10-12) | 3 天 | `src/muse_client.py`<br>`src/assembler.py`<br>[ADR-010](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-010-I2V-Hybrid-Motion-Architecture.md)<br>`docs/system_design.md` §9 | **【背景】** 突破二维仿射运镜限制，赋予具象生活物件物理级真实微动，同时避免全片生成视频导致的成本飙升与画风漂移。<br>**【验收标准】** *(全部达成)*<br>1. ✅ 实现以 `muse-image` 生成的高精原画作为首帧，调用 `muse-video` 进行 Image-to-Video 驱动，支持真实视频切片合成与 API 容灾重试；<br>2. ✅ 落地分镜分级策略（Tier-1: 仅第 1 幕抓眼钩子与第 5 幕行动示范生成 3s 微动，其余幕保持 Ken Burns 运镜，节约 70% 成本）；<br>3. ✅ 落地“自适应尾帧缓动定格 (Freeze-and-Drift)”算法，在 $T_{video} < T_{scene}$ 时提取末帧进行 1.2% 微幅呼吸推拉，完美对齐 [ADR-004](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-004-Edge-TTS-Integration-and-Audio-Driven-Timing.md) 的音画同步与外挂 SRT 时间戳；<br>4. ✅ 提供 `--motion-mode static/i2v-tier1/i2v-all` 调度控制与超时降级机制；9 项单元测试通过（`tests/test_i2v_motion.py`）。 |
| **TASK-5.1** | **轻量级 Web 审核看板 (Web Review Dashboard)** | P3 (低) | **已完成**<br>(2026-10-12) | 2 天 | `04_review_dashboard.py`<br>`dashboard.py`<br>`src/db.py`<br>[ADR-013](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-013-Web-Review-Dashboard-Architecture.md) | **【背景】** 677 条知识库量产后，创作者需要高效的可视化操作界面核验成片质量。<br>**【验收标准】** *(全部达成)*<br>1. ✅ 基于 Streamlit 构建本地响应式审核看板（`04_review_dashboard.py` / `dashboard.py`），支持 `streamlit run` 与直接 `python` 双模拉起；<br>2. ✅ 集中呈现 1080×1920 竖屏成片播放器（含体积/秒开指标与 MP4 下载）、高辨识度专属封面预览与独立 SRT 字幕实时查阅/下载；<br>3. ✅ 呈现黄金 6 幕多模态排查矩阵（浮现大字、AI 选风依据、分镜 TTS 音频播放器、原画首帧大图与 I2V 微动切片播放器同屏质检）；<br>4. ✅ 落地创作者工单流转：支持一键「⭐ 审核通过 (Mark Approved)」、输入批注「📝 标记需修订 (Needs Revision)」与「🔄 状态弹性重置 (Reset)」；单元测试通过（`tests/test_review_dashboard.py`）。 |
| **TASK-5.2** | **多平台营销文案与标签生成器 (Social Copywriting & Hashtags)** | P3 (低) | **已完成**<br>(2026-10-12) | 1 天 | `src/copywriter.py`<br>`04_review_dashboard.py`<br>[ADR-014](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-014-Social-Copywriting-and-Hashtags-Engine.md) | **【背景】** 视频成品产出后，创作者与运营人员在分发至各社交平台时，需针对平台调性编写具有高打开率的标题、完播钩子、Emoji 正文排版与高权重垂直标签，避免人工重复编写。<br>**【验收标准】** *(全部达成)*<br>1. ✅ 建立针对主流三大平台（📕 小红书 XHS、🎵 抖音短视频 Douyin、🟢 微信视频号 WeChat Channels）的结构化 Prompt 提示词工程，具备离线模板降级（`--mock`）与大模型生成能力；<br>2. ✅ 规范交付「双轨持久化」：机器可读 `output/raw_assets/{id}/copywriting.json` 与运营发布同名四件套 `output/final_videos/{clean_name}_copywriting.txt`；<br>3. ✅ 深度集成至 Web 审核看板（`04_review_dashboard.py`），提供三平台专属面板、标题/正文/标签模块化展示与一键复制；<br>4. ✅ 完善单元测试（`tests/test_copywriter.py`，覆盖 Prompt 构建、格式落盘与 Markdown 代码块清洗容错），全量测试 100% 绿灯。 |
| **TASK-5.3** | **平台草稿箱半自动同步辅助 (Creator Studio Draft Helper)** | P4 (远期) | 探索中 | 待定 | `output/final_videos/` | **【背景】** 降低人工逐个上传 600+ 视频的重复劳动。<br>**【验收标准】**<br>1. 探索小红书/微信视频号创作者助手本地草稿箱数据协议；<br>2. 尝试半自动化脚本填充视频文件、封面图、标题与字幕。 |

---

## 🛠️ 技术债务与工程健康度清单 (Technical Debt & Engineering Health)

> **原则**：技术债务不是“等有空再做”，而是保障多 Agent 协作和持续重构底线防线的工程基石。

| 债务项 | 影响范围 | 优先级 | 为什么必须解决 (The "Why") | 解决计划与目标 |
|---|---|---|---|---|
| **DEBT-01: Pytest 自动化测试套件** | `src/extractor.py`<br>`src/prompt_builder.py`<br>`src/db.py` | **P2 (中)** | 目前正则解析 34 章节与风格卡映射均依靠手工测试。一旦修改 Prompt 结构或 Markdown 解析规则，极易悄然引入非预期回归错误。 | 建立 `tests/` 目录，针对 Markdown 结构提取、JSON Schema 容错清洗、SQLite 状态流转编写自动化单元测试。 |
| **DEBT-02: 跨平台无头字体兼容增强** | `src/assembler.py`<br>`src/cover_generator.py` | **P2 (中)** | Windows 原生自带 `msyh.ttc`（微软雅黑），但在 Linux (Docker) 或 macOS CI 流程中缺失中文字体，会导致 Pillow 降级为默认位图字体或报错。 | 在 `src/config.py` 中增加开源思源黑体（Source Han Sans）轻量字体包自动下载/解压脚本，实现全平台零配置字体对齐。 |
| **DEBT-03: API 额度与开销可观测性监控** | `src/muse_client.py`<br>`pipeline.db` | **P3 (低)** | 工业化量产 677 条视频时，当前缺乏对各条目的 Token 消耗量、Muse 生图耗时、TTS 请求时长的系统性统计。 | 在 `entries` 数据库表中扩展 `cost_metrics` 字段，并在 `progress.json` 头部输出总消耗报表，实现生产成本透明化。 |

---

## 📋 任务状态流转规范 (Task Lifecycle Protocol)

根据项目规范，所有任务遵循以下生命周期：

```
[待排期 (Backlog)] ──► [进行中 (In Progress)] ──► [已完成 (Completed)] ──► 归档至对应 Milestone
                               │
                               └──► [阻塞/需决策] ──► 产出 ADR 决策讨论
```

- **任务完成定义 (Definition of Done, DoD)**：
  1. 代码逻辑实现且具备异常防护与容灾降级；
  2. 运行实际条目验证产物（音视频/图片/SRT）质量无异常；
  3. 文档同步更新：若涉及重大架构或数据协议调整，必须同步编写/更新对应的 ADR 并归档至 [`docs/decisions/`](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/)。
