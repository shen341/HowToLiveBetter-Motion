# ADR-013: 轻量级 Web 审核看板与人机协作质检架构 (Lightweight Web Review Dashboard Architecture)

## 状态 (Status)
**Accepted (已采纳实施 · 2026-10-12)**

## 日期 (Date)
2026-10-12

## 背景与上下文 (Context)
在项目完成 Milestone 1~4 以及 TASK-5.0 图生视频 (I2V) 混合动效后，系统已具备工业化批量生成能力（支持 34 章节、677 条生活指南的脚本规划、原画生图、TTS 口播合成与 MoviePy 视频导出）。

然而，面对数百条全自动化生产的短视频，创作者面临以下质检与运维挑战：
1. **纯命令行与文件系统核验的低效性**：创作者必须深入 `output/final_videos/` 与 `output/raw_assets/{id}/` 手工打开 MP4、PNG、SRT 和 JSON 文件，缺少集中视听对比工具；
2. **多模态素材链路断裂排查难**：成片一旦出现音画不协调或大字遮挡，创作者需要逐个排查是 TTS 时长问题、首帧原画问题还是 I2V 微动问题；
3. **缺少人机协同的审核状态闭环**：流水线目前仅有程序状态（`Pending`, `Script_Generated`, `Media_Generated`, `Completed`, `Failed`），缺乏创作者明确标记“已过审准予发布”的业务终态（`Approved`），也缺乏针对瑕疵成片“一键标记需重制（Needs Revision）”或“重置回上一步”的简便交互。

为此，需建立一个轻量、开箱即用、零额外复杂运维开销的本地可视化审核看板（TASK-5.1）。

---

## 架构决策 (Decision)

### 1. 技术选型：基于 Streamlit 构建本地极简交互看板
- **选用 Streamlit**：纯 Python 编写，天然与现有的 SQLite (`pipeline.db`)、Pillow、MoviePy、JSON 状态库深度整合，无需维护额外的前端构建打包工具链（如 Node.js / Vite / React）与跨域 CORS 协议；
- **自适应入口设计**：支持 `streamlit run 04_review_dashboard.py`，同时在直接执行 `python 04_review_dashboard.py` 或 `python dashboard.py` 时自动检测运行时上下文并无缝拉起 Streamlit，消除开发者的操作认知负担。

### 2. 交付物三位一体视听核验体验
主工作区左侧直接集成标准化发布三件套：
- **竖屏视频播放器 (`st.video`)**：原生内嵌播放 1080×1920 成片，实时展示体积 (MB)、时长与流式秒开支持；提供一键下载 MP4；
- **高辨识度专属封面展示 (`st.image`)**：即时预览 1080×1920 封面卡片，提供一键下载 PNG；
- **独立外挂 SRT 字幕预览与下载 (`st.download_button`)**：预览带毫秒级时间戳的软字幕，一键下载供剪映二次精修。

### 3. 分镜级多模态深度排查矩阵
主工作区右侧以选项卡（Tabs）形式展开黄金 6 幕细节：
- **艺术风格卡与 AI 决策依据**：直观展示所选风格（如吉卜力暖调手绘风）及大模型自主决策推理理由；
- **分镜粒度质检**：
  - 黄金分割浮现大字（Kinetic Typography）与口播台词明细；
  - 独立 TTS 音频播放器（`st.audio`），对比音频时长与画面时长，核验「以声定景」对齐度；
  - 首帧高精原画大图与 I2V 微动切片视频播放器同屏对比，明确动效模式（`I2V 物理微动 (Freeze-and-Drift)` 或 `Ken Burns 运镜`）。

### 4. 创作者审核与工单生命周期流转
在数据库层与看板交互中引入创作者状态流转闭环：
- **`⭐ 审核通过 (Mark Approved)`**：将条目推进至业务终态 `Approved`，触发庆祝特效，同步更新 `pipeline.db` 与 `progress.json` 进度快照；
- **`📝 标记需修订 (Needs Revision)`**：支持创作者输入审核批注（如“第 3 幕原画手部畸变，建议重抽”），记录至数据库 `notes` 字段并流转状态至 `Needs_Revision`；
- **`🔄 弹性状态重置 (Reset Entry)`**：支持一键回退至 `Pending`（完全重做）或 `Script_Generated`（保留脚本重做视觉素材），助力增量试跑。

---

## 备选方案评估 (Alternatives Considered)

### 备选方案 A：独立开发 React / Vue 前端 + FastAPI 后端
- **优点**：UI 组件库极度灵活，可设计复杂的拖拽排版界面。
- **缺点**：引入庞大的 Node.js、npm 依赖树与前后端双进程运维成本，对于本地桌面级创作者审核工具过于繁重，背离轻量原则。
- **结论**：**否决**。

### 备选方案 B：纯静态 HTML 页面生成器
- **优点**：无需任何后台服务，静态页面直接双击打开。
- **缺点**：无法进行交互式写回（无法在页面上点击按钮修改 SQLite 状态、无法记录审核批注、无法动态触发重装）。
- **结论**：**否决**。

---

## 实施后果与收益 (Consequences)

### 正面收益
1. **极大提升质检效率**：从文件系统翻找变成直观的 Web 界面点选播放，成片、封面、字幕、分镜一览无余；
2. **人机协作闭环建立**：引入 `Approved` 与 `Needs_Revision` 状态，流水线具备明确的人工复核准出标准；
3. **开箱即用无感知启动**：支持 `python dashboard.py` 或 `streamlit run 04_review_dashboard.py`，极简跨平台体验；
4. **全链路状态自愈与导出**：任何审核状态修改均即时镜像导出到 `progress.json`，保障下游 Agent 协同可读性。

---

## 实施与工程落地成果 (Implementation & Verification)

1. **核心看板脚本**：
   - [`04_review_dashboard.py`](file:///c:/develop/HowToLiveBetter-Motion/04_review_dashboard.py)：包含全局 KPI、多维侧边栏筛选、成片播放器、分镜多模态质检与审核工具箱；
   - [`dashboard.py`](file:///c:/develop/HowToLiveBetter-Motion/dashboard.py)：便捷重定向入口。
2. **状态机与数据层扩展**：
   - [`src/db.py`](file:///c:/develop/HowToLiveBetter-Motion/src/db.py)：扩展 `mark_approved()`、`reset_entry()`，并在 `get_statistics()` 中纳管 `Approved` 与 `Needs_Revision` 计数。
3. **自动化测试守门**：
   - [`tests/test_review_dashboard.py`](file:///c:/develop/HowToLiveBetter-Motion/tests/test_review_dashboard.py)：4 项针对审核标记、批注持久化、状态重置与路径解析鲁棒性的测试全部通过（总测试集 25 项全绿）。
