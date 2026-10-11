# HowToLiveBetter-Motion (高性价比人生指南 · 短视频自动化流水线)

> 基于知识库 [HowToLiveBetter](https://github.com/eternity4719/HowToLiveBetter) 与 [huashu-art-motion](https://github.com/alchaincyf/huashu-art-motion) 艺术美学理念，通过 Muse AI（`muse-spark`, `muse-image`, `muse-video`）、Cloudflare Worker Edge-TTS（`zh-CN-YunzeNeural`）与 MoviePy 全自动批量生成高质量科普短视频。

---

## 🌟 核心特性与架构亮点

1. **结构化数据自动抽取与断点续传**：
   - 自动解析 `HowToLiveBetter` 中 34 个章节、677 条生活建议。
   - 提取成本标签（钱/时间/毅力/收益/口径）、说人话释义、权威证据等级（A/B/C 级）。
   - SQLite 工业级持久化（`pipeline.db`）+ 人类可读状态镜像快照（`progress.json`）。
2. **深度融入 `huashu-art-motion` 艺术美学与黄金分割布局**：
   - **绝无 AI Slop**：坚决摒弃廉价的蓝紫霓虹、抽象发光球体、无脸白模人偶，全片锁定单一高级艺术画风（吉卜力水彩手绘、Vox 调查剪报、Kurzgesagt 扁平科普、霍珀现实主义等）。
   - **上部黄金分割点（$Y \approx 733\text{px}$）**：核心浮现关键词/重音数字卡片（Kinetic Typography），琥珀金高亮徽章与浮现动效。
   - **下部黄金分割点（$Y \approx 1186\text{px}$）**：高级深色磨砂半透明胶囊字幕（Frosted Dark Glass），避开抖音/小红书底部评论与操作区遮挡。
   - **连续动态运镜与平滑转场**：集成 Ken Burns 镜头推拉/平移运镜与 0.5s 电影感交叉溶解（Cross-dissolve）叠化过渡。
3. **OpenAI SDK 规范接入 Muse AI**：
   - 使用 `muse-spark` 提炼 30 秒精炼口播与四幕紧凑分镜。
   - 自动生成 9:16（1024×1792）高精艺术画作（`muse-image`）或动态切片。
4. **Cloudflare Edge-TTS 原生讲解与音画精准同步**：
   - 调用 Edge-TTS 云端服务，采用 **`"zh-CN-YunzeNeural"`**（云泽·男声解说，沉稳富有说服力）。
   - **以声定景（Audio-Driven Duration）**：分镜时长与下部黄金分割点文字展示自动对齐语音时长（语音时长 + 0.5s 舒适呼吸留白）。
5. **自定义背景音乐（BGM）与微音量混音**：
   - 自动读取根目录 `backgroup_music/` 下的 MP3 音乐（内置 `01_country_music.mp3`, `02_NastelBom.mp3`, `03_AbsoluteSound.mp3` 等）。
   - 背景音乐音量精确压低至 **0.09（-20dB 舒适弱音）**，搭配 1.0s 淡入与 2.0s 淡出，**纯衬底、绝不抢戏或干扰人声解说**！

---

## 📚 核心文档导航 (Documentation Hub)

- 📖 **[运用手册与运维指南 (Operations Manual)](file:///c:/develop/HowToLiveBetter-Motion/docs/OPERATIONS_MANUAL.md)**：包含前置环境安装、SOP 操作命令、画风调度、BGM 定制、SQLite 运维及发布前质检清单。
- 🏛️ **[架构决策记录 (ADR 索引)](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/README.md)**：包含 6 项关键 ADR，详细阐述双轨状态、画风理念、Pillow 渲染、以声定景、弱音混音与 AI 自主选风的决策理由。
- 📋 **[项目路线图与待办任务 (TODO & Roadmap)](file:///c:/develop/HowToLiveBetter-Motion/docs/TODO.md)**：记录已完成里程碑、近期高优先任务（封面卡片/SRT字幕/批量限流）及远期规划。
- 📐 **[系统架构设计与技术选型 (System Design)](file:///c:/develop/HowToLiveBetter-Motion/docs/system_design.md)**：包含数据 Schema、MoviePy 架构与提示词编译工程标准。

---

## 📂 项目工程目录

```
HowToLiveBetter-Motion/
├── .env.example               # 环境变量配置模板 (Muse API & TTS 配置)
├── .gitignore                 # Git 忽略配置
├── README.md                  # 项目总览说明
├── requirements.txt           # Python 依赖清单
├── pipeline.db                # SQLite 状态数据库 (本地自动生成)
├── progress.json              # 全局进度追踪快照 (677 条完整状态)
│
├── docs/                      # 核心文档中枢
│   ├── OPERATIONS_MANUAL.md   # [核心运用手册] 全流程操作与运维指南
│   ├── TODO.md                # [任务清单] 路线图与待办 Backlog
│   ├── system_design.md       # 系统架构设计、Schema 与技术选型文档
│   └── decisions/             # [ADR 架构决策记录]
│       ├── README.md          # ADR 索引与状态表
│       ├── ADR-001-Dual-State-Persistence-SQLite-and-JSON.md
│       ├── ADR-002-Huashu-Art-Motion-Style-Cards-and-Prompt-Engineering.md
│       ├── ADR-003-MoviePy-and-Pillow-Video-Assembly-Architecture.md
│       ├── ADR-004-Edge-TTS-Integration-and-Audio-Driven-Timing.md
│       ├── ADR-005-Custom-BGM-Directory-and-Audibility-Mixing.md
│       └── ADR-006-Autonomous-Visual-Style-Selection.md
│
├── backgroup_music/           # 自定义背景音乐库 (放入任意 .mp3 音乐)
│   ├── 01_country_music.mp3
│   ├── 02_NastelBom.mp3
│   └── 03_AbsoluteSound.mp3
│
├── assets/                    # 本地静态资产库
│   ├── fonts/                 # 本地中文字体 (自动兼容 Windows 微软雅黑)
│   └── bgm/                   # 预设备用音频
│
├── src/                       # 核心业务组件
│   ├── __init__.py
│   ├── config.py              # 配置加载与路径常量
│   ├── db.py                  # 数据库初始化、状态流转与导出
│   ├── extractor.py           # Markdown 正则与 AST 解析器
│   ├── prompt_builder.py      # huashu 风格美学与 Prompt 编译器
│   ├── muse_client.py         # Muse AI API 客户端与离线模拟器
│   ├── tts_client.py          # Cloudflare Edge-TTS 语音生成与时长测量
│   ├── cover_generator.py     # [TASK-4.1] 1080x1920 竖屏高辨识度专属封面卡片生成器
│   └── assembler.py           # MoviePy 运镜、转场、黄金分割字幕与混音引擎
│
├── 01_data_extractor.py       # 步骤 1: 数据拉取、结构化抽取与状态入库
├── 02_ai_generator.py         # 步骤 2: 大模型分镜规划、素材生成与 TTS 语音合成
├── 03_video_assembler.py      # 步骤 3: 运镜转场与双轨混音全自动合成输出
│
├── data/                      # 原始数据源
│   └── HowToLiveBetter/       # 克隆的知识库仓库 (book/*.md)
│
└── output/                    # 产物输出目录
    ├── raw_assets/            # 各条目分镜脚本、原画与语音 (output/raw_assets/{id}/)
    └── final_videos/          # 最终交付的 1080x1920 MP4 成片
```

---

## 🚀 快速上手与运行指南

### 1. 环境准备与依赖安装

建议使用 Python 3.10+ 环境：

```bash
# 1. 克隆或进入本项目
cd c:/develop/HowToLiveBetter-Motion

# 2. 安装 Python 依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 并重命名为 `.env`：

```bash
cp .env.example .env
```

在 `.env` 中配置你的 Muse AI 密钥与 TTS 设置：

```ini
# Muse API 配置
MUSE_API_KEY=your_actual_muse_api_key_here
MUSE_BASE_URL=https://yourselfai.org/muse/v1

# 模型定义
MODEL_TEXT=muse-spark
MODEL_IMAGE=muse-image
MODEL_VIDEO=muse-video

# TTS 语音生成配置 (Cloudflare Worker Edge-TTS)
TTS_API_URL=https://tts-voice-magic.shimizuhiro874-28e.workers.dev/v1/audio/speech
TTS_VOICE=zh-CN-YunzeNeural
TTS_SPEED=1.0
TTS_PITCH=0
TTS_STYLE=general

# 视频产物配置
VIDEO_WIDTH=1080
VIDEO_HEIGHT=1920
VIDEO_FPS=30
```

---

## 🛠️ 三步自动化流水线运行说明

### 步骤 1：数据抓取与状态管理初始化 (`01_data_extractor.py`)

自动检测并克隆 `HowToLiveBetter` 仓库，精准拆解 34 个章节中的 677 条建议并录入 SQLite：

```bash
# 解析全书所有 677 条条目并入库
python 01_data_extractor.py

# 仅解析指定章节（如第 1 章《不要早死》）
python 01_data_extractor.py --chapter 1

# 强制重置所有条目状态为 Pending（默认会保留现有工作流状态）
python 01_data_extractor.py --force
```

---

### 步骤 2：大模型分镜规划、原画与 TTS 语音生成 (`02_ai_generator.py`)

将建议条目结合 `huashu-art-motion` 风格卡，调用 `muse-spark` 生成分镜，调用 `muse-image` 生成艺术原画，并调用 TTS 服务合成 `zh-CN-YunzeNeural` 语音。**现已全面支持 AI 自主语义选风与自定义风格控制**：

```bash
# 1. 默认模式：AI 根据内容语义与情绪基调自主决策最佳画风 (--style auto)
python 02_ai_generator.py --entry-id 09_001

# 2. 章节统一模式：按所属章节统一画风系列 (--style chapter)
python 02_ai_generator.py --entry-id 01_001 --style chapter

# 3. 强制指定画风模式：手动测试对比特定艺术风格 (如 y2_vox, y1_kurzgesagt, 13_pop, 24_hopper, 25_ghibli, 17_ink, 14_pixel)
python 02_ai_generator.py --entry-id 01_001 --style y2_vox --force

# 4. 批量处理前 5 个待处理条目 (全自动智能选风)
python 02_ai_generator.py --limit 5
```

产物保存在：`output/raw_assets/{entry_id}/`
- `storyboard.json`：包含选定艺术风格（`art_style_id`）、选风依据（`art_style_reason`）、分镜、Prompt、精确语音时长与动态同步时长
- `scene_01.png` ~ `scene_04.png`：高清 9:16 分镜艺术原画
- `voice_01.mp3` ~ `voice_04.mp3`：各分镜解说语音 MP3

---

### 步骤 3：音视频全自动合成、运镜转场与配乐混音 (`03_video_assembler.py`)

使用 `moviepy` 动态加载分镜与语音轨，添加 Ken Burns 运镜、0.5s 叠化转场、上下黄金分割点文字卡片，并混入 `backgroup_music/` 背景音乐：

```bash
# 合成指定条目的短视频 (例如 01_001)
python 03_video_assembler.py --entry-id 01_001

# 批量合成所有已就绪的条目
python 03_video_assembler.py --limit 5

# 指定自定义 BGM
python 03_video_assembler.py --entry-id 01_001 --bgm backgroup_music/01_country_music.mp3
```

产物保存在：`output/final_videos/{entry_id}_{标题}.mp4`
合成完成后，条目状态自动流转为 `Completed`。

---

## 🎨 视觉风格配方卡（huashu-art-motion 深度映射，支持 `--style auto` 智能自主决策）

| 风格 ID | 风格名称 | 适用领域 | 美学特征 |
|---|---|---|---|
| `25_ghibli` | 吉卜力暖调手绘风 | 意外预防、家庭安全、身体健康 | 温暖阳光漫射、质朴生活细节、温润治愈手绘水彩 |
| `y2_vox` | Vox 调查剪报风 | 法律红线、金融防骗、合同维权 | 真实纸纹拼贴、红线指引、高对比度黑白档案感 |
| `y1_kurzgesagt` | Kurzgesagt 扁平科普 | 精力管理、时间分配、科学机制 | 鲜明纯色平涂色块、几何轮廓、无复杂蓝紫渐变 |
| `13_pop` | 利希滕斯坦波普风 | 反直觉痛点、消费陷阱、人际冲突 | 本戴点网格纹理、粗重黑色描边、经典美漫原色冲击 |
| `24_hopper` | 霍珀现实主义风 | 情绪压力、重大变故、人生哲学 | 斜射几何光块、市井现实主义、克制沉静构图 |
| `17_ink` | 新中式东方水墨风 | 处世哲学、心态调适、中式养生 | 水墨晕染留白、淡雅矿物设色、宁静从容意境 |
| `14_pixel` | 8-Bit 像素复古游戏风| 习惯打卡、微小行动积累、目标达成 | 精致复古像素点阵、街机闯关成就感、轻松趣味 |