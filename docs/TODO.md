# HowToLiveBetter-Motion 项目任务与演进路线图 (TODO & Roadmap)

本文档系统梳理 `HowToLiveBetter-Motion`（高性价比人生指南 · 短视频自动化流水线）的里程碑进度、待办任务（Backlog）以及技术债务维护清单。

---

## 📊 里程碑整体进度概览

```
[Milestone 1] 核心基建与数据抽取   [████████████████████] 100% (已完成)
[Milestone 2] 多模态资产与影视级组装 [████████████████████] 100% (已完成)
[Milestone 3] 语音解说与智能选风     [████████████████████] 100% (已完成)
[Milestone 4] 批量生产、质检与平台化 [████████████░░░░░░░░]  60% (当前重点)
[Milestone 5] 人工审核工作台与发布辅助 [░░░░░░░░░░░░░░░░░░░░]   0% (未来规划)
```

---

## 🏆 已完成里程碑 (Completed Milestones)

### Milestone 1: 核心基建与数据持久化 (Phase 1)
- [x] **数据自动拉取与 AST 解析**：克隆并解析 `HowToLiveBetter` 34 个章节、677 条完整生活建议（`01_data_extractor.py`）。
- [x] **双轨状态持久化引擎**：SQLite 数据库 `pipeline.db`（支持事务与行级锁）+ 自动同步的人类可读 `progress.json` 快照（`src/db.py`）。
- [x] **断点续传与防重复执行**：完整状态机流转设计（`Pending` $\to$ `Script_Generated` $\to$ `Media_Generated` $\to$ `Completed`）。

### Milestone 2: 视觉美学与影视级组装 (Phase 2)
- [x] **融入 `huashu-art-motion` 哲学**：制定“防 AI Slop 原则”，四幕脉冲节奏与具象物体/动作要求（`src/prompt_builder.py`）。
- [x] **摆脱 ImageMagick 依赖**：纯 Python Pillow 11.x 字体排版与抗锯齿渲染，支持 Windows 系统字体（`src/assembler.py`）。
- [x] **上下黄金分割点防遮挡排版**：
  * 上部黄金分割点（$Y \approx 733\text{px}$）：核心浮现大字徽章（Kinetic Typography）。
  * 下部黄金分割点（$Y \approx 1186\text{px}$）：深色磨砂半透明胶囊字幕，彻底避开抖音/小红书底部交互 UI。
- [x] **Ken Burns 连续运镜与 0.5s 交叉溶解**：平滑镜头推拉与叠化转场。

### Milestone 3: 语音解说与智能自主选风 (Phase 3)
- [x] **Cloudflare Edge-TTS 接入**：集成 `"zh-CN-YunzeNeural"` 男声解说，沉稳公信力（`src/tts_client.py`）。
- [x] **“以声定景”动态时长同步**：以真实解说语音时长反向驱动分镜画面展示时长（$T_{scene} = T_{audio} + 0.5\text{s}$）。
- [x] **自定义 BGM 弱音混音**：扫描 `backgroup_music/` 目录，限制弱音倍率 0.09 (-20dB)，保障解说人声清晰度。
- [x] **AI 语义理解自主选风**：内置 7 种风格卡配方库，`muse-spark` 具备导演级选风决策权，支持 `--style auto/chapter/<id>`。

### Milestone 4: 批量生产与平台化适配 (Phase 4 进展)
- [x] **TASK-4.1 短视频专属封面卡片自动生成 (Cover Card Generator)**：实现 1080×1920 竖屏高辨识度首图生成引擎（`src/cover_generator.py`），支持大字标题、核心痛点钩子、3 维度权威与成本徽章，并在分镜与合成流水线中全自动触发。
- [x] **TASK-4.2 导出独立 SRT 字幕文件 (Standalone SRT Subtitle Generator)**：实现标准 SRT 导出引擎（`src/srt_generator.py`），根据 0.5s 交叉溶解与音频绝对时间轴精准生成分镜级/断句级字幕，自动落盘并同步至 `output/raw_assets/{entry_id}/subtitles.srt` 与 `output/final_videos/{clean_name}.srt`，便于剪映二次精修与播放器直接外挂。

---

## 🚀 进行中与近期高优先任务 (Milestone 4: 批量生产与平台化适配)

| 任务编号 | 任务标题 | 优先级 | 状态 | 估算工时 | 详细说明与验收标准 (Acceptance Criteria) |
|---|---|---|---|---|---|
| **TASK-4.1** | **短视频专属封面卡片自动生成 (Cover Card Generator)** | P1 (高) | **已完成** | 1.5 天 | • 为每个条目生成 1 张 1080×1920 竖屏高辨识度静态封面（可作为小红书/抖音发布首图）。<br>• 居中突出超大章节主题与小条目标题，标注“证据等级 A 级”、“0 成本”徽章。<br>• 产物保存为 `output/raw_assets/{entry_id}/cover.png` 及 `output/final_videos/{id}_cover.png`。 |
| **TASK-4.2** | **导出独立 SRT 字幕文件 (Standalone SRT Subtitles)** | P1 (高) | **已完成** | 0.5 天 | • 根据各分镜的精确时间戳与文本，自动输出标准的 `.srt` 字幕文件到 `output/final_videos/{clean_name}.srt` 与 `output/raw_assets/{entry_id}/subtitles.srt`。<br>• 支持分镜级精准时间轴（1:1 匹配语音）与 `--split` 断句级自适应比例切分。<br>• 方便创作者在剪映/快剪辑中二次精修，或直接上传平台作为软字幕。 |
| **TASK-4.3** | **批量生成速率控制与指数退避重试 (Rate Limiting & Backoff)** | P2 (中) | 待排期 | 1 天 | • 在执行 `--limit 50` 大批量生成时，针对 Muse API 与 Edge-TTS 添加每分钟请求数限制（Token Bucket）。<br>• 遇到 429 或 503 网络抖动时自动进行 3 次指数退避重试（Backoff: 2s $\to$ 4s $\to$ 8s），防止整批任务中断。 |
| **TASK-4.4** | **社交平台码率自适应压缩 (Platform Preset Compression)** | P2 (中) | 待排期 | 1 天 | • 小红书对大于 50MB 视频易二次压缩导致画质劣化。<br>• 支持 `--preset xhs/douyin/wechat` 参数，使用 ffmpeg CRF=20~22 与 AAC 128k 自动将 30 秒成片控制在 10~20MB 最优画质体积区间。 |

---

## 🔮 远期探索规划 (Milestone 5: 人工审核工作台与发布辅助)

| 任务编号 | 任务标题 | 优先级 | 状态 | 详细说明 |
|---|---|---|---|---|
| **TASK-5.1** | **轻量级 Web 审核看板 (Web Review Dashboard)** | P3 (低) | 规划中 | • 基于 Streamlit 或轻量 HTML 建立本地审核页面。<br>• 创作者可直观看到所有已生成的成片视频播放器、文案对照、原画查看。<br>• 提供「通过（Mark Approved）」与「重抽此镜（Regenerate Scene）」一键按钮。 |
| **TASK-5.2** | **多平台文案与标签生成器 (Social Copywriting & Tags)** | P3 (低) | 规划中 | • 调用大模型自动生成适用于小红书（含 Emoji、爆款标题、#生活指南 #科普 标签）与抖音（含话题挑战）的发布文案。 |
| **TASK-5.3** | **发布脚本或草稿箱同步辅助** | P4 (远期) | 探索中 | • 研究小红书/视频号创作者中心草稿箱同步或半自动上传方案。 |

---

## 🛠️ 技术债务与维护清单 (Technical Debt & Maintenance)

- [ ] **自动化测试套件 (Pytest)**：为 `extractor.py`（正则匹配）、`prompt_builder.py`（风格卡选择）、`db.py`（SQLite CRUD）编写自动化单元测试，防止迭代代码破坏既有逻辑。
- [ ] **跨平台字体兼容增强**：除了 Windows 系统的微软雅黑，针对 Linux (Docker) 与 macOS 补充自动下载开源思源黑体（Source Han Sans）的兜底脚本。
- [ ] **API 额度与耗时统计监控**：在数据库中增加记录每个条目调用的 Token 消耗量、生图耗时、TTS 耗时，并在 `progress.json` 汇总报表中展示。
