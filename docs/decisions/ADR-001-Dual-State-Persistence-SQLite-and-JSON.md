# ADR-001: 双轨状态持久化架构 (SQLite + progress.json)

## 状态 (Status)
**Accepted (已采纳实施)**

## 日期 (Date)
2026-10-11

## 背景与上下文 (Context)
本项目需要批量将开源仓库 `HowToLiveBetter` 中的 34 个章节、677 条生活建议全自动转换为 30 秒短视频。在全自动流水线中，面临以下现实挑战：
1. **数据规模较大**：全书 677 条小条目，各条目包含成本（钱/时间/毅力/收益/口径）、说人话正文、证据等级、文献来源等多维度元数据。
2. **多阶段耗时与 API 限制**：分镜规划（大模型）、生图/生视频（多模态 API）、语音合成（TTS）、视频渲染（本地 CPU/GPU）每个条目需耗时 10~60 秒，易遇网络超时或调用限流。
3. **断点续传与防重复生成**：必须严格记录每个条目的当前阶段状态（`Pending` $\to$ `Script_Generated` $\to$ `Media_Generated` $\to$ `Completed`），支持随时中断和恢复，杜绝重复产生模型扣费。
4. **人类直观可读性**：创作者在日常开发和排查时，希望不需要每次都写 SQL 查询，能用 VSCode 打开即看到全局概况。

## 架构决策 (Decision)
采用 **SQLite 主状态库 + 自动导出 `progress.json` 镜像快照** 的双轨持久化设计：
1. **SQLite (`pipeline.db`) 作为主数据源**：
   - 创建 `entries` 表，使用单一全局唯一键 `id`（如 `01_001`）。
   - 利用 SQLite 本地 ACID 事务机制与行级锁，确保多脚本、多任务运行状态写入的原子性与可靠性。
   - 记录重试计数 `retry_count`、最新错误堆栈 `error_message`、生图目录 `raw_assets_dir`、成片路径 `final_video_path`。
2. **`progress.json` 作为只读/镜像快照**：
   - 每次条目状态流转（成功或失败）后，通过 `export_progress_json()` 自动将数据库当前全量状态导出至根目录的 `progress.json`。
   - 包含统计摘要块（`summary`）与明细字典（`entries`），方便直接搜索与监控。

## 备选方案评估 (Alternatives Considered)

### 备选方案 A：纯单个 JSON 文件 (`progress.json`)
- **优点**：结构简单，无需引入数据库驱动。
- **缺点**：当包含 677 条详细数据和长 JSON 分镜脚本时，并发写入容易损坏文件，更新单条需重读全量重写全量，I/O 开销随条目增加而恶化；断电或进程强退可能导致文件截断变为空文件。
- **结论**：**否决**。

### 备选方案 B：外部服务型数据库 (MySQL / PostgreSQL / Redis)
- **优点**：支持多机并发、功能丰富。
- **缺点**：对于单机自动化短视频生成工具而言属于过度设计（Over-engineering），增加了 Docker 或远程数据库运维依赖，降低了本地开箱即用性。
- **结论**：**否决**。

## 实施后果与收益 (Consequences)
- **正向收益**：
  - 零外部服务依赖，Python 原生 `sqlite3` 标准库即可运行。
  - 支持精准的命令行筛选（如 `--chapter 1 --status Pending --limit 5`）。
  - 支持故障隔离与失败重试（`update_status(..., status="Failed", error_message=...)`）。
  - `progress.json` 能够直接纳入 Git 跟踪或提供给前端/看板展示。
- **注意事项**：
  - Windows 环境下多进程读写 SQLite 时偶现锁竞争，采用上下文管理器并确保连接及时关闭。
  - 将 `*.db-shm` 和 `*.db-wal` 纳入 `.gitignore`，防止临时缓存污染版本库。
