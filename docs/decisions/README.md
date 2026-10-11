# Architecture Decision Records (ADR 架构决策记录)

本文档记录了 `HowToLiveBetter-Motion`（高性价比人生指南 · 短视频自动化流水线）在架构设计与迭代演进过程中的关键技术决策、上下文约束、备选方案评估与最终结论。

## ADR 索引与状态列表

| 编号 | 决策标题 | 状态 | 决策日期 | 核心结论摘要 |
|---|---|---|---|---|
| [ADR-001](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-001-Dual-State-Persistence-SQLite-and-JSON.md) | 双轨状态持久化架构 (SQLite + progress.json) | **Accepted** | 2026-10-11 | 采用 SQLite 作为主状态引擎保障并发事务与断点续传，配合自动导出的 `progress.json` 提供人类直观可读性。 |
| [ADR-002](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-002-Huashu-Art-Motion-Style-Cards-and-Prompt-Engineering.md) | huashu-art-motion 美学理念与防 AI Slop 提示词工程 | **Accepted** | 2026-10-11 | 拒斥廉价霓虹科幻感，全片统一艺术风格卡，镜头绑定具体的物理器物与动作，脉冲节奏四幕分镜。 |
| [ADR-003](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-003-MoviePy-and-Pillow-Video-Assembly-Architecture.md) | 视频组装引擎与黄金分割排版架构 (Pillow + MoviePy) | **Accepted** | 2026-10-11 | 废除 ImageMagick 依赖，采用 Pillow 高清抗锯齿文字渲染，上下黄金分割点防遮挡排版，Ken Burns 运镜与 0.5s 转场。 |
| [ADR-004](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-004-Edge-TTS-Integration-and-Audio-Driven-Timing.md) | Edge-TTS 语音解说接入与「以声定景」动态音画同步 | **Accepted** | 2026-10-11 | 接入 Cloudflare Edge-TTS (`zh-CN-YunzeNeural`)，以真实语音时长加呼吸留白反向驱动分镜画面时长，彻底杜绝音画不同步。 |
| [ADR-005](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-005-Custom-BGM-Directory-and-Audibility-Mixing.md) | 自定义背景音乐库与人声避让弱音混音规范 | **Accepted** | 2026-10-11 | 设立 `backgroup_music/` 目录供随时放入 MP3，程序自动选曲并将音量严格限制在 0.09 (-20dB)，保障解说人声清晰度。 |
| [ADR-006](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-006-Autonomous-Visual-Style-Selection.md) | AI 语义理解自主选风与多模态风格调度 | **Accepted** | 2026-10-11 | 赋予 `muse-spark` 导演级选风决策权，根据内容情绪自主匹配风格卡并输出理由，同时保留章节统一与手动指定模式。 |

## ADR 生命周期与规范

```
PROPOSED (拟定中) ──► ACCEPTED (已采纳实施) ──► SUPERSEDED (已被新决策取代) / DEPRECATED (已弃用)
```

- **不删除历史 ADR**：即使某个决策在后续被替代，也保留原始记录并标记 `Superseded by ADR-XXX`，以此记录项目的真实演进脉络。
- **不可反悔记录**：每个重要技术变更都应在此新增记录，帮助未来协作者和 AI Agent 快速理解项目上下文。
