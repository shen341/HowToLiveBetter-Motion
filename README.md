# HowToLiveBetter-Motion (高性价比人生指南 · 短视频自动化流水线)

> 基于知识库 [HowToLiveBetter](https://github.com/eternity4719/HowToLiveBetter) 与 [huashu-art-motion](https://github.com/alchaincyf/huashu-art-motion) 艺术美学理念，通过 Muse AI（`muse-spark`, `muse-image`, `muse-video`）与 MoviePy 全自动批量生成 30 秒移动端竖屏短视频。

---

## 🌟 核心特性与架构亮点

1. **结构化数据自动抽取与断点续传**：
   - 自动解析 `HowToLiveBetter` 中 34 个章节、677 条生活建议。
   - 提取成本标签（钱/时间/毅力/收益/口径）、说人话释义、权威证据等级（A/B/C 级）。
   - SQLite 工业级持久化（`pipeline.db`）+ 人类可读状态镜像快照（`progress.json`）。
2. **深度融入 `huashu-art-motion` 艺术美学**：
   - **绝无 AI Slop**：坚决摒弃廉价的蓝紫霓虹、抽象发光球体、无脸白模人偶，全片锁定单一高级艺术画风（吉卜力水彩手绘、Vox 调查剪报、Kurzgesagt 扁平科普、霍珀现实主义等）。
   - **具体的“物”与“动作”**：每个分镜必须围绕现实中的物理实体（安全带卡扣、燃气阀门、血压计仪表、药盒标签）和具体动作展开。
   - **脉冲式解说节奏**：停住阐释 -> 0.28秒快推/横移重音 -> 停住消化，彻底消除 PPT 幻灯片般的催眠慢推感。
3. **OpenAI SDK 规范无缝接入 Muse AI**：
   - 使用 `muse-spark` 提炼 30 秒精炼口播与四幕紧凑分镜。
   - 自动适配生成高画质 9:16（1080×1920）竖屏图像素材（`muse-image`）或动态切片（`muse-video`）。
4. **现代化音视频装配管线**：
   - 纯 Python + MoviePy + Pillow 离线高质量文字光栅化，**彻底摆脱 Windows 环境对 ImageMagick 的繁琐配置依赖**，中文排版零乱码。
   - 包含顶部胶囊标识卡、中间重音浮现大字卡片（Kinetic Typography）、底部自适应磨砂两行旁白字幕。
   - 自动混入 `assets/bgm/` 背景轻音乐，支持音量智能侧链（0.4 适中音量）、自动淡入与淡出。

---

## 📂 项目工程目录

```
HowToLiveBetter-Motion/
├── .env.example               # 环境变量配置模板
├── .gitignore                 # Git 忽略配置
├── README.md                  # 项目全景使用指南
├── requirements.txt           # Python 依赖清单
├── pipeline.db                # SQLite 状态数据库 (运行后自动创建)
├── progress.json              # 全局进度追踪快照 (677 条完整状态)
│
├── docs/                      # 架构与设计规范
│   └── system_design.md       # 系统架构设计、Schema 与技术选型文档
│
├── assets/                    # 本地静态资产库
│   ├── bgm/                   # 预设背景轻音乐 (内置 default_ambient.wav)
│   └── fonts/                 # 本地中文字体 (自动兼容 Windows 微软雅黑)
│
├── src/                       # 核心业务组件
│   ├── __init__.py
│   ├── config.py              # 配置加载与路径常量
│   ├── db.py                  # 数据库初始化、状态流转与导出
│   ├── extractor.py           # Markdown 正则与 AST 解析器
│   ├── prompt_builder.py      # huashu 风格美学与 Prompt 编译器
│   ├── muse_client.py         # Muse AI API 客户端与离线模拟器
│   └── assembler.py           # MoviePy 视频串联、字幕排版与混音引擎
│
├── 01_data_extractor.py       # 步骤 1: 数据拉取、结构化抽取与状态入库
├── 02_ai_generator.py         # 步骤 2: 大模型分镜规划与多模态资产生成
├── 03_video_assembler.py      # 步骤 3: 视频全自动合成渲染与成片输出
│
├── data/                      # 原始数据源
│   └── HowToLiveBetter/       # 克隆的知识库仓库 (book/*.md)
│
└── output/                    # 产物输出目录
    ├── raw_assets/            # 各条目分镜脚本与图片/视频素材 (output/raw_assets/{id}/)
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

在 `.env` 中填入你的 Muse AI 密钥（代码严格从 `os.getenv` 读取，绝无硬编码）：

```ini
# Muse API 配置
MUSE_API_KEY=your_actual_muse_api_key_here
MUSE_BASE_URL=https://yourselfai.org/muse/v1

# 模型定义
MODEL_TEXT=muse-spark
MODEL_IMAGE=muse-image
MODEL_VIDEO=muse-video

# 视频产物配置
VIDEO_WIDTH=1080
VIDEO_HEIGHT=1920
VIDEO_FPS=30
```

> 💡 **提示**：若暂无 `MUSE_API_KEY`，所有脚本均内置 `--mock` 离线测试模式，支持在本地全流程闭环验证！

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

运行后将生成：
- `pipeline.db`：SQLite 数据库
- `progress.json`：全局进度追踪快照

---

### 步骤 2：大模型分镜规划与视觉素材生成 (`02_ai_generator.py`)

将建议条目结合 `huashu-art-motion` 风格卡，调用 `muse-spark` 生成 30 秒分镜与旁白，并调用 `muse-image` 生成分镜关键帧：

```bash
# 指定条目 ID 生成素材 (例如 01_001 系安全带)
python 02_ai_generator.py --entry-id 01_001

# 批量处理前 5 个 Pending 状态条目
python 02_ai_generator.py --limit 5

# 离线模拟测试 (无需消耗 API Key，生成高质感测试素材)
python 02_ai_generator.py --entry-id 01_001 --mock
```

产物保存在：`output/raw_assets/{entry_id}/`
- `storyboard.json`：包含视频标题、旁白、浮现字、生图 Prompt
- `scene_01.png` ~ `scene_04.png`：高清 9:16 分镜画面

---

### 步骤 3：音视频全自动合成与配乐排版 (`03_video_assembler.py`)

利用 `moviepy` 串联画面、添加动态文字特效、顶部胶囊标识、磨砂字幕并混入 BGM：

```bash
# 合成指定条目的短视频 (例如 01_001)
python 03_video_assembler.py --entry-id 01_001

# 批量合成所有状态为 Media_Generated 的条目
python 03_video_assembler.py --limit 5

# 指定自定义 BGM
python 03_video_assembler.py --entry-id 01_001 --bgm assets/bgm/my_music.mp3
```

产物保存在：`output/final_videos/{entry_id}_{标题}.mp4`
合成完成后，条目状态自动流转为 `Completed`。

---

## 📊 状态机生命周期流转

```
[Markdown 原文]
       │
       ▼ (01_data_extractor.py)
   Pending (待处理)
       │
       ▼ (02_ai_generator.py - muse-spark)
Script_Generated (分镜脚本已生成)
       │
       ▼ (02_ai_generator.py - muse-image)
Media_Generated (视觉素材已就绪)
       │
       ▼ (03_video_assembler.py - moviepy)
   Completed (视频已合成，可发布)
```

如在任何阶段发生网络波动或异常，系统将标记为 `Failed` 并保留完整异常堆栈，支持修复后直接对指定 ID 重新执行。

---

## 🎨 视觉风格配方卡（huashu-art-motion 深度映射）

| 风格 ID | 风格名称 | 适用领域 | 美学特征 |
|---|---|---|---|
| `25_ghibli` | 吉卜力暖调手绘风 | 意外预防、家庭安全、身体健康 | 温暖阳光漫射、质朴生活细节、温润治愈手绘水彩 |
| `y2_vox` | Vox 调查剪报风 | 法律红线、金融防骗、合同维权 | 真实纸纹拼贴、红线指引、高对比度黑白档案感 |
| `y1_kurzgesagt` | Kurzgesagt 扁平科普 | 精力管理、时间分配、常识机制 | 鲜明纯色平涂色块、几何轮廓、无复杂蓝紫渐变 |
| `24_hopper` | 霍珀现实主义风 | 情绪压力、重大变故、人生哲学 | 斜射几何光块、市井现实主义、克制沉静构图 |

---

## 📜 许可证与数据来源

- 知识库内容遵循 CC BY 4.0 协议，数据源来自 [eternity4719/HowToLiveBetter](https://github.com/eternity4719/HowToLiveBetter)。
- 艺术动画方法论参考自 [alchaincyf/huashu-art-motion](https://github.com/alchaincyf/huashu-art-motion)。
- 本项目代码遵循 MIT License 开源协议。