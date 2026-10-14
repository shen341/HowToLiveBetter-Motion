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
3. **OpenAI SDK 规范接入 Muse AI 与黄金 6 幕叙事脉冲**：
   - 使用 `muse-spark` 规划黄金 6 幕脉冲式叙事曲线（痛点钩子 $\to$ 认知颠覆 $\to$ 危害机理 $\to$ 权威证据 $\to$ 极低成本 $\to$ 金句定格），单镜 4.0~5.2s 消除呆滞长镜头，全片 28~32s 黄金节奏。
   - 自动生成 9:16（1024×1792）高精艺术原画（`muse-image`）或动态切片。
4. **Cloudflare Edge-TTS 原生讲解与音画精准同步**：
   - 调用 Edge-TTS 云端服务，采用 **`"zh-CN-YunzeNeural"`**（云泽·男声解说，沉稳富有说服力）。
   - **以声定景（Audio-Driven Duration）**：分镜时长与下部黄金分割点文字展示自动对齐语音时长（语音时长 + 0.5s 舒适呼吸留白）。
5. **自定义背景音乐（BGM）与微音量混音**：
   - 自动读取根目录 `backgroup_music/` 下的 MP3 音乐（内置 `01_country_music.mp3`, `02_NastelBom.mp3`, `03_AbsoluteSound.mp3` 等）。
   - 背景音乐音量精确压低至 **0.09（-20dB 舒适弱音）**，搭配 1.0s 淡入与 2.0s 淡出，**纯衬底、绝不抢戏或干扰人声解说**！
6. **短视频专属高辨识度封面卡片引擎 (Cover Card Generator)**：
   - 纯 Python Pillow 实现 1080×1920 竖屏封面生成引擎（`src/cover_generator.py`），解决直接截帧对比度低痛点。
   - 包含超大加粗标题、痛点钩子、3 维度权威标签（证据等级/执行成本/收益），并自动规避 Emoji 乱码方块。
7. **独立外挂 SRT 字幕导出引擎 (SRT Generator)**：
   - 实现 `src/srt_generator.py`，精确镜像转场叠化时间轴，输出标准 UTF-8 毫秒级 `.srt` 字幕。
   - 支持分镜级 1:1 精确对齐与断句级自适应比例切分，成片同名自动外挂，剪映一键导入二次精修。
8. **社交平台码率自适应压缩与流式秒开预设 (Platform Bitrate Presets)**：
   - 内置主流自媒体平台（小红书 `xhs` 抗二压、抖音 `douyin` 高清、微信 `wechat` 秒开、`bilibili`、`default`）编码矩阵。
   - 采用 CRF (19~22) + VBV 峰值限速双控，将 30s 成片严格锁死在 **10~20MB** 最优传输区间，注入 `-movflags +faststart` 保证移动端即点即播。
9. **多平台爆款营销文案与高权重标签生成器 (Social Copywriting & Hashtags)**：
   - 实现 `src/copywriter.py`，针对小红书（爆款候选标题、痛点导语、📌 Emoji 分点、利他 CTA、高权重标签）、抖音短视频（18字短标题、黄金3秒完播 Hook）、微信视频号（公信力标题、朋友圈转发推荐语）量身定制提示词与清洗体系。
   - 机器可读 `copywriting.json` 与运营发布四件套同名 `{clean_name}_copywriting.txt` 双轨落盘。
10. **图生视频 (I2V) 混合动态微动演进与自适应尾帧定格 (Hybrid Motion & Freeze-and-Drift)**：
   - 突破二维仿射运镜限制，以原画为首帧调用 `muse-video` 赋予关键分镜真实物理微动。
   - 独创自适应尾帧缓动定格算法（Freeze-and-Drift），在 $T_{video} < T_{scene}$ 时自适应延展缓动推拉，兼顾高保真音画同步与成本控制（节约 70% 预算）。
11. **本地响应式 Web 审核看板与人机协作质检 (Web Review Dashboard)**：
   - 基于 Streamlit 构建极简本地看板（`04_review_dashboard.py` / `dashboard.py`），全览 677 篇短视频生命周期。
   - 集中核验 1080×1920 竖屏成片、专属封面、SRT 软字幕、分镜微动矩阵与三平台营销文案一键复制，支持一键工单流转。

---

## 📚 核心文档导航 (Documentation Hub)

- 📖 **[运用手册与运维指南 (Operations Manual)](file:///c:/develop/HowToLiveBetter-Motion/docs/OPERATIONS_MANUAL.md)**：包含前置环境安装、SOP 操作命令、画风调度、BGM 定制、SQLite 运维、剪映二次微调及发布前质检清单。
- 🏛️ **[架构决策记录 (ADR 索引)](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/README.md)**：包含 14 项关键 ADR（[ADR-001 ~ ADR-014](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/README.md)），系统性沉淀状态持久化、美学理念、Pillow 渲染、以声定景、弱音混音、自主选风、专属封面、黄金 6 幕、独立 SRT、I2V 混合微动、令牌桶限流、社交平台码率预设、Web 审核看板及多平台营销文案架构。
- 📋 **[项目路线图与待办任务 (TODO & Roadmap)](file:///c:/develop/HowToLiveBetter-Motion/docs/TODO.md)**：记录已完成里程碑、近期高优先任务及远期规划。
- 📐 **[系统架构设计与技术选型 (System Design)](file:///c:/develop/HowToLiveBetter-Motion/docs/system_design.md)**：包含数据 Schema、MoviePy 架构、提示词编译工程与交付四件套标准。

---

## 📂 项目工程目录

```
HowToLiveBetter-Motion/
├── .env.example               # 环境变量配置模板 (Muse API & TTS 配置)
├── .gitignore                 # Git 忽略配置
├── README.md                  # 项目总览说明
├── requirements.txt           # Python 依赖清单 (含 Streamlit)
├── pipeline.db                # SQLite 状态数据库 (本地自动生成)
├── progress.json              # 全局进度追踪快照 (677 条完整状态)
│
├── docs/                      # 核心文档中枢
│   ├── OPERATIONS_MANUAL.md   # [核心运用手册] 全流程操作与运维指南
│   ├── TODO.md                # [任务清单] 路线图与待办 Backlog
│   ├── system_design.md       # 系统架构设计、Schema 与技术选型文档
│   └── decisions/             # [ADR 架构决策记录]
│       ├── README.md          # ADR 索引与状态表 (ADR-001 ~ ADR-014)
│       └── ADR-001 ~ ADR-014  # 架构决策记录全文
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
│   ├── muse_client.py         # Muse AI API 客户端与离线模拟器 (I2V 支持)
│   ├── rate_limiter.py        # 令牌桶并发限流与指数退避重试执行器
│   ├── tts_client.py          # Cloudflare Edge-TTS 语音生成与时长测量
│   ├── cover_generator.py     # 1080x1920 竖屏专属封面卡片生成器
│   ├── srt_generator.py       # 独立外挂 SRT 字幕生成与时间轴对齐引擎
│   ├── copywriter.py          # 多平台营销文案与高权重标签生成引擎
│   └── assembler.py           # MoviePy 运镜、转场、黄金分割字幕与混音引擎
│
├── tests/                     # 自动化单元测试套件
│   ├── test_copywriter.py     # 营销文案与双轨产物测试
│   ├── test_i2v_motion.py     # I2V 混合微动与尾帧缓动测试
│   ├── test_rate_limiter.py   # 限流与退避重试测试
│   └── test_review_dashboard.py # 看板与业务流转测试
│
├── 01_data_extractor.py       # 步骤 1: 数据拉取、结构化抽取与状态入库
├── 02_ai_generator.py         # 步骤 2: 大模型分镜规划、素材生成、TTS语音、封面与字幕
├── 03_video_assembler.py      # 步骤 3: 运镜转场与双轨混音全自动合成输出 (平台预设+I2V)
├── 04_review_dashboard.py     # 步骤 4: Streamlit 本地可视化质检看板与工单流转
├── dashboard.py               # 看板极简快捷启动脚本
│
├── data/                      # 原始数据源
│   └── HowToLiveBetter/       # 克隆的知识库仓库 (book/*.md)
│
└── output/                    # 产物输出目录
    ├── raw_assets/            # 各条目素材包 (storyboard.json, cover.png, subtitles.srt, copywriting.json, scene_01~06, motion_01~06, voice_01~06)
    └── final_videos/          # 最终交付四件套 ({id}.mp4 成片, {id}.srt 独立字幕, {id}_cover.png 发布首图, {id}_copywriting.txt 营销文案)
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

# 图片与模型备选路线配置 (OpenAI 兼容协议)
# 当 muse-image 遇到限速 (429) 或服务端拥堵 (502/超时) 时自动无缝切换备用路线
YOURSELFAI_API_KEY=your_yourselfai_api_key_here
YOURSELFAI_BASE_URL=https://yourselfai.org/v1
YOURSELFAI_MODEL=gemini-3.8-flash-high
YOURSELFAI_IMAGE_MODEL=gemini-3.1-flash-image

# 接口单次请求超时时长 (秒, 避免服务端拥堵时无限挂起, 默认: 45.0)
API_TIMEOUT_SECONDS=45.0

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
# 1. 默认模式：AI 自主决策最佳画风 + 黄金 6 幕叙事脉冲 (--style auto --scenes 6)
python 02_ai_generator.py --entry-id 01_003

# 2. 章节统一模式：按所属章节统一画风系列 (--style chapter)
python 02_ai_generator.py --entry-id 01_001 --style chapter

# 3. 指定分镜幕数：支持 4/6/8 幕分镜（默认 6 幕黄金节奏）
python 02_ai_generator.py --entry-id 01_001 --scenes 6

# 4. 强制指定画风模式：手动测试对比特定艺术风格 (如 y2_vox, y1_kurzgesagt, 13_pop, 24_hopper, 25_ghibli, 17_ink, 14_pixel)
python 02_ai_generator.py --entry-id 01_001 --style y2_vox --force

# 5. 批量处理前 5 个待处理条目 (全自动智能选风与素材生成)
python 02_ai_generator.py --limit 5
```

产物保存在：`output/raw_assets/{entry_id}/`
- `storyboard.json`：包含选定艺术风格（`art_style_id`）、选风依据（`art_style_reason`）、分镜、Prompt、精确语音时长与动态同步时长
- `cover.png`：1080×1920 竖屏高辨识度专属封面卡片（大字标题、痛点钩子与 3 维度徽章）
- `subtitles.srt`：独立标准 SRT 字幕文件（毫秒级精准对齐音频时间轴）
- `scene_01.png` ~ `scene_06.png`：高清 9:16 分镜艺术原画 (1024×1792)
- `voice_01.mp3` ~ `voice_06.mp3`：各分镜解说语音 MP3

---

### 步骤 3：音视频全自动合成、平台码率压缩与交付四件套 (`03_video_assembler.py`)

使用 `moviepy` 动态加载 6 幕分镜与语音轨，支持纯原画运镜或 I2V 真实物理微动切片（配合尾帧缓动定格 Freeze-and-Drift）、0.5s 叠化转场、上下黄金分割点文字卡片，混入 `backgroup_music/` 背景音乐，并自动将成片、封面、字幕与营销文案组装输出至交付目录：

```bash
# 1. 合成指定条目的短视频 (默认 default 通用码率)
python 03_video_assembler.py --entry-id 01_003

# 2. 针对目标平台指定码率预设与流式秒开 (xhs/douyin/wechat/bilibili)
python 03_video_assembler.py --entry-id 01_001 --preset xhs

# 3. 启用 I2V 混合微动合成
python 03_video_assembler.py --entry-id 01_001 --motion-mode i2v-tier1

# 4. 批量合成所有已就绪的条目
python 03_video_assembler.py --limit 5

# 5. 指定自定义 BGM
python 03_video_assembler.py --entry-id 01_001 --bgm backgroup_music/01_country_music.mp3

# 6. 导出断句级细分 SRT 字幕（自适应标点符号比例切分，适合剪映逐句跳字）
python 03_video_assembler.py --entry-id 01_001 --force --split-srt
```

产物保存在：`output/final_videos/` 标准化交付四件套：
- `{clean_name}.mp4`：1080×1920 竖屏成片（约 28~32 秒，10~20MB，`-movflags +faststart` 保证流式秒开）
- `{clean_name}.srt`：同名独立外挂字幕（播放器与剪映自动关联）
- `{clean_name}_cover.png`：配套发布首图封面卡片
- `{clean_name}_copywriting.txt`：配套多平台发布营销文案

---

### 步骤 4：多平台营销文案与高权重标签生成 (`src/copywriter.py`)

为解决短视频分发至小红书、抖音、微信视频号时的文案编写痛点，调用大模型或离线模版自动提炼爆款标题、完播钩子、Emoji 分点正文与垂直话题标签：

```bash
# 1. 单条生成 (调用 muse-spark 大模型)
python -m src.copywriter --entry-id 01_001

# 2. 离线快速生成 (使用内置高拟真模版，无需消耗 Token)
python -m src.copywriter --entry-id 01_001 --mock

# 3. 批量为所有已有产物的条目生成营销文案
python -m src.copywriter --all --mock
```

产物保存在：
- 机器可读：`output/raw_assets/{entry_id}/copywriting.json`
- 运营可复制：`output/final_videos/{clean_name}_copywriting.txt`

---

### 步骤 5：创作者可视化 Web 审核看板 (`04_review_dashboard.py` / `dashboard.py`)

流水线生产完毕后，创作者可通过本地响应式 Web 看板对 677 篇短视频进行高效质检与生命周期管理：

```bash
# 方式 1：直接运行 Python 快捷入口（自动拉起浏览器 http://localhost:8501）
python dashboard.py
# 或
python 04_review_dashboard.py

# 方式 2：标准 Streamlit 命令启动
streamlit run 04_review_dashboard.py
```

**看板核心特性**：
- 📊 **全局 KPI 与进度条**：全书 677 条知识库进度、各状态分布（Pending, Media_Generated, Completed, Approved, Failed）；
- 🎥 **发布四件套视听播放**：内嵌 1080×1920 竖屏播放器、封面卡片预览、独立外挂 SRT 软字幕实时查阅与一键下载；
- 📢 **多平台营销文案面板**：小红书/抖音/微信视频号三大选项卡、爆款标题、Emoji 排版正文与垂直标签**一键全选复制**；
- 🎨 **分镜多模态排查矩阵**：逐幕核验黄金分割大字、AI 选风依据、TTS 口播音频与 I2V 微动切片同屏对比；
- 🛠️ **人机审核工单流转**：支持一键「⭐ 审核通过 (Mark Approved)」、输入修改意见「📝 标记需修订 (Needs Revision)」与「🔄 状态弹性重置 (Reset)」。

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