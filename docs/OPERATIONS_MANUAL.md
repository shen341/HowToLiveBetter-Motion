# HowToLiveBetter-Motion 全流程运用手册 (Operations Manual)

> 本手册为 `HowToLiveBetter-Motion`（高性价比人生指南 · 短视频自动化流水线）的标准运维与操作指南。涵盖环境配置、标准生产流程（SOP）、高级调度技巧、配乐与画风定制、数据库状态运维及平台发布质检清单。

---

## 1. 系统环境与前置准备 (Prerequisites)

### 1.1 运行环境要求
- **操作系统**：Windows 10 / 11（已内置微软雅黑字体与 UTF-8 终端适配）或 Linux / macOS
- **Python 版本**：Python 3.10 ~ 3.14
- **硬件要求**：
  - CPU：4 核以上
  - 内存：8GB RAM 以上（MoviePy 视频渲染单条峰值占用约 1~2GB；若具备 32GB 内存则支持高并发批量合成）
  - 显卡 (GPU)：当前标准流程**无需独立显卡**（大模型、生图与 TTS 全流程走云端 API，视频默认采用 CPU 软编）。若本机配备 NVIDIA 独立显卡（如 RTX 4070 12GB），已在底层支持 NVENC 秒级硬件压缩，并规划了未来纯离线本地化 AI 演进，详见 [ADR-015 (本地化 AI 演进路线与 RTX 4070 适配架构)](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-015-Local-AI-Roadmap-and-RTX4070-Adaptation.md)
  - 磁盘空间：至少保留 5GB 剩余空间（存放高清素材与导出成片）

### 1.2 依赖安装
打开终端（Windows 推荐 PowerShell），进入工程根目录：

```powershell
cd c:\develop\HowToLiveBetter-Motion

# 安装项目依赖
pip install -r requirements.txt
```

> **注意**：本项目已自主研发 Pillow 抗锯齿文字渲染引擎，**不需要安装 ImageMagick**，亦无须配置复杂的操作系统注册表！底层视频编码依赖 `imageio-ffmpeg`，首次运行时会自动准备 ffmpeg 运行时。

---

## 2. 配置文件说明 (`.env`)

在项目根目录创建或编辑 `.env` 文件（可参考 `.env.example`）：

```ini
# ==========================================
# 1. Muse AI 大模型配置 (用于文案分镜与高清生图)
# ==========================================
MUSE_API_KEY=your_muse_api_key_here
MUSE_BASE_URL=https://yourselfai.org/muse/v1
MODEL_TEXT=muse-spark
MODEL_IMAGE=muse-image
MODEL_VIDEO=muse-video

> 💡 **模型说明**：当前标准生产使用 `muse-spark` 规划分镜、`muse-image` 生成高精艺术原画，并由 MoviePy 渲染运镜。`MODEL_VIDEO` 为项目预留演进接口，详见 [ADR-010 (I2V 混合动态微动架构)](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-010-I2V-Hybrid-Motion-Architecture.md) 与 [系统设计文档 §9](file:///c:/develop/HowToLiveBetter-Motion/docs/system_design.md#9-视觉动态演进路线图生视频-image-to-video-i2v-混合驱动架构-hybrid-motion-architecture)。

# ==========================================
# 2. TTS 语音讲解服务配置 (基于 Cloudflare Edge-TTS)
# ==========================================
TTS_API_URL=https://tts-voice-magic.shimizuhiro874-28e.workers.dev/v1/audio/speech
TTS_VOICE=zh-CN-YunzeNeural
TTS_SPEED=1.0
TTS_PITCH=0
TTS_STYLE=general
```

> 💡 **密钥安全提示**：`.env` 文件已被 `.gitignore` 自动忽略，**切勿将真实密钥提交至公共代码仓库**。

---

## 3. 标准生产作业流程 (Standard SOP)

整个短视频自动化生产流水线由结构化解耦的步骤组成，支持随时中断、断点续传与离线降级：

```
[01_data_extractor.py] ──► [02_ai_generator.py] ──► [03_video_assembler.py] ──► [src.copywriter] ──► [04_review_dashboard.py]
      (数据抽取)                 (分镜+生图+TTS)            (运镜+字幕+压缩预设)         (多平台营销文案)           (本地Web质检流转)
                                                                                                        │
                                                                                                        ▼
                                                                                           最终交付标准化发布四件套
```

---

### 步骤 1：数据抽取与状态初始化 (`01_data_extractor.py`)

本步骤负责拉取开源知识库并精准解析条目元数据（成本/说人话/收益/证据等级），存入本地 SQLite。

```powershell
# 1.1 首次全量抽取全书 34 个章节、677 个条目
python 01_data_extractor.py

# 1.2 仅抽取特定章节（例如第 1 章《不要早死》）
python 01_data_extractor.py --chapter 1

# 1.3 强制重新拉取最新仓库并重置状态
python 01_data_extractor.py --force
```

- **输出产物**：本地状态数据库 `pipeline.db` 和全局快照 `progress.json`。

---

### 步骤 2：大模型分镜、素材与语音生成 (`02_ai_generator.py`)

本步骤调用 `muse-spark` 生成紧凑分镜（**默认黄金 6 幕叙事脉冲曲线**：痛点钩子 -> 认知颠覆 -> 机理危害 -> 权威证据 -> 极低成本 -> 金句定格），调用 `muse-image` 生成 9:16 原画，并调用 Edge-TTS 生成解说音频及自动生成独立 SRT 字幕。

```powershell
# 2.1 单条生成（默认 AI 自主选风，默认黄金 6 幕，最推荐）
python 02_ai_generator.py --entry-id 01_001

# 2.2 批量生成待处理的前 3 个条目
python 02_ai_generator.py --limit 3

# 2.3 指定分镜幕数（可选 4 幕、6 幕或 8 幕，默认为 6 幕）
python 02_ai_generator.py --entry-id 01_001 --scenes 6

# 2.4 强制覆盖重跑已生成条目
python 02_ai_generator.py --entry-id 01_001 --force

# 2.5 批量高速生成并自定义速率限制与重试策略 (TASK-4.3)
python 02_ai_generator.py --limit 10 --rpm-muse 30 --rpm-tts 60 --max-retries 3

# 2.6 离线/模拟测试模式 (不消耗 API 额度，快速验证流程)
python 02_ai_generator.py --entry-id 01_001 --mock --force

# 2.7 图生视频 (I2V) 混合动态微动模式调度 (ADR-010)
# static: 纯静态原画+运镜(默认); i2v-tier1: 仅第1/5幕物理微动(推荐高性价比); i2v-all: 全片6幕微动
python 02_ai_generator.py --entry-id 01_001 --motion-mode i2v-tier1

# 2.8 极简手绘白板全动效模式 (TASK-5.4)
# 自动匹配具象 SVG 矢量图形（如汽车、安全带、天平等），并由纯金属触控笔以 30fps 逐帧实时勾勒
python 02_ai_generator.py --entry-id 01_001 --motion-mode whiteboard --force
```

- **输出产物**（存放于 `output/raw_assets/{entry_id}/`）：
  - `cover.png`：1080×1920 竖屏高辨识度专属封面卡片（小红书/抖音首选发布首图）。
  - `subtitles.srt`：标准独立 SRT 字幕文件（分镜精准对齐时间戳）。
  - `copywriting.json`：[新增] 包含小红书、抖音、微信视频号三大平台的结构化营销文案与标签。
  - `storyboard.json`：分镜脚本、Prompt、动态微动提示词、所选画风与选风理由、精准语音与分镜时长。
  - `scene_01.png` ~ `scene_06.png`：1024×1792 竖屏原画素材。
  - `motion_01.mp4` ~ `motion_06.mp4`：(I2V 模式下) 生成的 3s 物理微动作视频切片。
  - `voice_01.mp3` ~ `voice_06.mp3`：各分镜解说音频。

> 💡 **独立重制封面卡片与字幕命令**：
> - 重新排版渲染封面图：`python -m src.cover_generator --entry-id 01_001`
> - 重新导出独立 SRT 字幕：`python -m src.srt_generator --entry-id 01_001 [--split]`

---

### 步骤 3：影视级视频组装、码率压缩与交付四件套 (`03_video_assembler.py`)

本步骤将图片或 I2V 微动切片、自适应尾帧缓动定格 (Freeze-and-Drift)、转场溶解、黄金分割点文字卡片及 BGM 进行渲染，输出最终 MP4，并自动将发布首图、独立 SRT 字幕与营销文案同步复制至交付目录。

```powershell
# 3.1 合成指定条目的最终成片 (默认 default 通用码率)
python 03_video_assembler.py --entry-id 01_001

# 3.2 批量合成已完成素材生成的全部视频
python 03_video_assembler.py --limit 5

# 3.3 针对目标社交平台启用定制化码率压缩预设与流式秒开 (ADR-012)
# 可选预设: xhs (小红书抗二压), douyin (抖音高清), wechat (微信秒开), bilibili, default
python 03_video_assembler.py --entry-id 01_001 --preset xhs

# 3.4 启用 I2V 混合微动合成
python 03_video_assembler.py --entry-id 01_001 --motion-mode i2v-tier1

# 3.5 强制重新渲染合成
python 03_video_assembler.py --entry-id 01_001 --force

# 3.6 导出断句级细分字幕（按标点自适应比例切分长句）
python 03_video_assembler.py --entry-id 01_001 --force --split-srt
```

- **输出产物**（存放于 `output/final_videos/`）：
  - `{entry_id}_{章节名}之{小条目标题}.mp4`：1080×1920 竖屏成片（约 28~32 秒，10~20MB 最优画质与体积，注入 faststart 流式秒开）。
  - `{entry_id}_{章节名}之{小条目标题}_cover.png`：配套的高清专属发布首图。
  - `{entry_id}_{章节名}之{小条目标题}.srt`：配套的标准独立外挂字幕（媒体播放器与剪映自动关联）。
  - `{entry_id}_{章节名}之{小条目标题}_copywriting.txt`：[新增] 配套的多平台营销文案与高权重标签发布文件。

---

### 步骤 4：多平台营销文案与高权重标签生成 (`src/copywriter.py`)

本步骤调用大模型（或离线高拟真模板）针对条目提炼适合小红书、抖音、微信视频号的爆款标题、痛点导语、Emoji 分点正文与垂直话题标签，直接生成运营一键复制发布的四件套之一。

```powershell
# 4.1 单条条目生成营销文案 (默认使用 muse-spark)
python -m src.copywriter --entry-id 01_001

# 4.2 离线快速生成 (使用内置高拟真模版，无需 API 额度)
python -m src.copywriter --entry-id 01_001 --mock

# 4.3 批量为所有已有产物的条目生成营销文案
python -m src.copywriter --all --mock

# 4.4 强制覆盖已存在的文案
python -m src.copywriter --entry-id 01_001 --force
```

- **输出产物**：
  - 机器可读：`output/raw_assets/{entry_id}/copywriting.json`
  - 运营可复制：`output/final_videos/{clean_name}_copywriting.txt`


---

## 4. 艺术画风定制与调度技巧 (Art Styles)

系统内置 7 款基于开源 `huashu-art-motion` 研发的艺术画风，通过 `--style` 参数灵活调度：

| 风格代号 (`style_id`) | 风格名称 | 核心美学特征 | 适用内容场景推荐 |
|---|---|---|---|
| **`25_ghibli`** | 吉卜力暖调手绘风 | 水彩洗染、自然阳光漫射、质朴器物细节 | 生活好习惯、家庭温情、日常防护、治愈健康 |
| **`w1_whiteboard`** | 极简手绘白板风 | 暖调米白宣纸底板、极简黑线线稿、大面积呼吸留白、理性思维导图 | 法律避坑、规则拆解、硬核科普、决策权衡、设计取舍 |
| **`y1_kurzgesagt`** | Kurzgesagt 扁平科普风 | 高饱和明快色块、极简几何轮廓、科学图解 | 生理机制、注意力拆解、科学数据、技能学习 |
| **`13_pop`** | 利希滕斯坦波普艺术风 | 本戴点网格纹理、粗重黑边、美漫经典原色冲击 | 强烈反常识痛点、消费陷阱、人际冲突破防 |
| **`24_hopper`** | 霍珀美国现实主义风 | 强烈斜射几何光影、市井生活写实、克制沉思 | 都市打工人、独处与内心压力、人际交往 |
| **`17_ink`** | 新中式东方水墨风 | 水墨晕染留白、淡雅设色、东方哲学从容意境 | 处世哲学、断舍离、心态调适、中式养生 |
| **`14_pixel`** | 8-Bit 像素复古游戏风 | 精致复古像素点阵、街机闯关界面感、轻松有趣 | 习惯打卡、微小行动积累、目标达成游戏化 |

### 调度命令范式：
```powershell
# 模式 A：【AI 自主决策】（默认，强烈推荐）
# AI 通读条目语义后自动挑选最契合风格，并给出理由
python 02_ai_generator.py --entry-id 05_001 --style auto

# 模式 B：【章节系列统一】
# 遵循章节归属统一风格（例如整套《不要早死》均采用吉卜力风格）
python 02_ai_generator.py --entry-id 01_001 --style chapter

# 模式 C：【人工强制指定】
# 强制采用极简手绘白板风做视觉效果对比
python 02_ai_generator.py --entry-id 01_001 --style w1_whiteboard --force
```

---

## 4.5 极简手绘白板全动效模式操作指南 (Zen Whiteboard Motion Guide)

### 4.5.1 核心设计理念
- **突破 I2V 瓶颈**：传统图生视频 (I2V) 存在高算力成本与 AI 画面文字畸变（AI Slop）问题；静态图文容易产生视觉疲劳。
- **禅意美学与留白**：画幅保持 $\ge 65\%\sim 75\%$ 呼吸留白，米白宣纸底板（`#FAF8F5`），避免任何视觉冗余与画面拥挤，让观众更容易深入沉思。
- **去拟真手模，纯金属触控笔**：去除矩形硬切边的人类手模与多余遮挡，采用轻量现代的**纯金属触控笔（Metallic Stylus）**在纸面上优雅书写，笔尖微动自然（带有 $\pm0.6\text{px}$ 有机微抖动与落笔升空过渡）。
- **标点意群完整闭合**：采用智能标点规整算法，杜绝从句腰部硬切截断，每幕旁白皆为语义自洽、干脆有力的完整句子。

### 4.5.2 具象 SVG 矢量图库与名词语义自动联想
白板模式突破了纯几何图形（圆、方、三角）的单调局限，实现了**基于分镜关键词的实体名词具象写画**：
1. **语义倒排联想匹配**：系统解析分镜标题、关键词、分镜主体及口播文本（例如：“安全带”、“车祸” -> 自动联想并匹配 **`automobile`（汽车）**；“权威认证” -> 匹配 **`shield_badge`（盾牌）**；“投入产出” -> 匹配 **`balance_scale`（天平）**）。
2. **纯 Python SVG 路径解析器 (`src/whiteboard/svg_parser.py`)**：零外部依赖，直接解析标准 SVG 中的 Path 贝塞尔曲线、圆、矩形与折线，自适应等比缩放并居中投影到 1080×1920 竖屏画布。
3. **内置矢量资产目录 (`assets/whiteboard/svg/`)**：
   - `automobile.svg`：精致小轿车侧身轮廓、车窗分隔与轮毂线稿；
   - `seatbelt.svg`：对角斜拉安全带织带与插舌卡扣；
   - `crash_warning.svg`：警示三角与感叹号；
   - `shield_badge.svg`：权威证据等级盾牌与缎带；
   - `balance_scale.svg`：成本与收益轻重对比天平；
   - `clock_time.svg`：2 秒快速习惯秒表；
   - `checkmark_circle.svg`：行动是唯一解圆形对勾；
   - `heart_pulse.svg`：生命健康心跳脉冲。

### 4.5.3 像素图（PNG/JPG）转 SVG 矢量图与写画工作流
创作者常问：*“这个手绘图形很棒，是像素图生成的吗？能否将本地 SD 生成的像素图转为 SVG 后驱动写画？”*
- **现有机制说明**：成片中绘制的图形**直接来源于高精度的 SVG 矢量数学曲线**，因此在 1080×1920 高清竖屏下放大毫无马赛克毛边，触控笔能严格顺着矢量控制点逐帧描画。
- **从 SD/LoRA 像素图到 SVG 动画的完整扩充工作流**：
  ```
  [SD / ComfyUI LoRA] ──► [高反差白底黑线 PNG] ──► [矢量化工具 (vtracer/potrace)] ──► [*.svg 存入 assets/whiteboard/svg/] ──► [触控笔逐帧写画]
  ```
  1. **步骤 1：本地 SD/LoRA 生成线稿**：在本地 ComfyUI 中使用白板线稿 LoRA（如 `whiteboard_doodle_v1.safetensors`），生成纯白底（`#FFFFFF`）、高对比度黑色单线稿 PNG。
  2. **步骤 2：自动矢量化提取**：
     - 工具推荐：使用开源 `vtracer`（`pip install vtracer`）或 `potrace` 命令行工具：
       ```powershell
       vtracer --input input_sketch.png --output assets/whiteboard/svg/new_icon.svg --colormode binary
       ```
  3. **步骤 3：注册语义关键词**：在 [`src/whiteboard/svg_library.py`](file:///c:/develop/HowToLiveBetter-Motion/src/whiteboard/svg_library.py) 的 `SEMANTIC_KEYWORD_MAP` 中添加该图素的中文/英文关联词即可。

### 4.5.4 白板模式一键生产 SOP
```powershell
# 1. 抽取数据（若尚未初始化）
python 01_data_extractor.py --chapter 1

# 2. 生成手绘白板分镜与写画切片
python 02_ai_generator.py --entry-id 01_001 --motion-mode whiteboard --force

# 3. 合成 1080x1920 完整 MP4 视频
python 03_video_assembler.py --entry-id 01_001
```

---

## 5. 背景音乐 (BGM) 定制指南

### 5.1 音乐库管理
- 所有背景音乐统一存放在根目录 **`backgroup_music/`** 下。
- 支持直接放入任意标准 `.mp3` 文件。
- 当前内置三首精选轻音乐：
  - `01_country_music.mp3`（轻松欢快乡村风，适合习惯与日常）
  - `02_NastelBom.mp3`（沉浸氛围感，适合情感与心理沉思）
  - `03_AbsoluteSound.mp3`（现代律动感，适合机制科普与规则）

### 5.2 音乐调度与音量控制
- **自动随机**：默认未指定 `--bgm` 时，程序会在 `backgroup_music/` 目录中随机挑选一首，保障视频听觉新鲜感。
- **手动指定**：
  ```powershell
  python 03_video_assembler.py --entry-id 01_001 --bgm backgroup_music/01_country_music.mp3
  ```
- **音量保护原则**：程序内部已将 BGM 音量硬性缩放至 `0.09`（约 -20dB），并附加 $1.0\text{s}$ 淡入与 $2.0\text{s}$ 淡出，**纯衬底、绝不会干扰或掩盖人声解说**！如需微调，可在 `src/assembler.py` 中修改 `bgm_volume`。

---

## 6. 数据库状态与批处理运维

### 6.1 查看当前进度概览
直接打开根目录下的 `progress.json`，头部包含全局统计：
```json
{
  "last_updated": "2026-10-11T14:47:44",
  "summary": {
    "Total": 677,
    "Pending": 675,
    "Script_Generated": 0,
    "Media_Generated": 1,
    "Completed": 1,
    "Failed": 0
  }
}
```

### 6.2 常用 SQLite 运维查询命令
在 PowerShell 中运行以下命令可快速排查：

```powershell
# 查询处于 Failed 失败状态的条目及错误信息
python -c "import sqlite3; c=sqlite3.connect('pipeline.db').cursor(); print(c.execute('SELECT id, title, error_message FROM entries WHERE status=\"Failed\"').fetchall())"

# 查询已成功完成视频渲染 (Completed) 的条目
python -c "import sqlite3; c=sqlite3.connect('pipeline.db').cursor(); print(c.execute('SELECT id, title, final_video_path FROM entries WHERE status=\"Completed\"').fetchall())"

# 将某个出错条目重置为 Pending 重新执行
python -c "import sqlite3; conn=sqlite3.connect('pipeline.db'); conn.execute('UPDATE entries SET status=\"Pending\", retry_count=0, error_message=NULL WHERE id=\"01_001\"'); conn.commit()"
```

---

## 7. 平台发布前人工质检清单 (Publishing Checklist)

在上传至**小红书**、**微信视频号**、**抖音**前，请创作者进行 10 秒快速质检：

- [ ] **1. 时长核验**：视频总长是否在 25 ~ 35 秒以内？（短视频黄金完播区间）
- [ ] **2. 标题规范**：视频开头及标题是否符合 `"{章节名}之{小条目标题}"` 格式？
- [ ] **3. 上部黄金分割点文字**：各分镜第 0.2 秒弹出的琥珀金色大字徽章是否字数精简（2~8字）、是否有乱码或截断？
- [ ] **4. 下部黄金分割点字幕**：深色胶囊字幕框中的文字是否与云泽解说语音字字对齐？是否位于屏幕垂直偏中下位置（真机测试不被平台底部按钮遮挡）？
- [ ] **5. 人声清晰度**：云泽的声音是否洪亮饱满？背景音乐是否处于柔和衬底状态（0.09 / -20dB）？
- [ ] **6. 画面质感**：画面是否统一遵循指定艺术风格？各分镜切换是否自然无突兀卡顿？
- [ ] **7. 专属封面卡片**：交付目录是否已包含配套的 `{clean_name}_cover.png`？标题排版无误、无方块符号乱码，可作为发布首图。
- [ ] **8. 独立外挂字幕**：交付目录是否已包含同名 `{clean_name}.srt`？播放器外挂或导入剪映时时间轴无偏差。
- [ ] **9. 多平台营销文案与标签**：交付目录是否已包含配套的 `{clean_name}_copywriting.txt`？在 Web 审核看板中确认小红书爆款排版、抖音短标题和视频号转发语无违禁词且标签垂直精准。

---

## 7.5 创作者本地可视化 Web 审核看板 (Web Review Dashboard)

为杜绝创作者在 Windows 资源管理器与命令行中低效翻找上千个文件，系统提供了基于 Streamlit 的极简本地响应式审核看板（**ADR-013**, **ADR-014**）：

```powershell
# 极简双击/单行启动（自动打开默认浏览器访问 http://localhost:8501）
python dashboard.py

# 或使用标准 Streamlit 命令
streamlit run 04_review_dashboard.py
```

### 审核看板核心操作场景：
1. **全书 677 篇大盘透视**：顶部实时 KPI 汇报总条目、成片数、审核通过数、各章节进度条；
2. **发布四件套集中核验**：左侧一键点播 1080×1920 竖屏成片（含体积/码率预设与秒开参数展示）、预览高清封面卡片、在线查阅带毫秒级时间戳的 SRT 软字幕并提供一键下载；
3. **📢 多平台爆款营销文案与标签面板**：
   - 支持 **📕 小红书专属**、**🎵 抖音短视频**、**🟢 微信视频号** 三大平台分 Tab 预览；
   - 包含吸睛候选标题、痛点导语、Emoji 分点易读正文与垂直话题标签；
   - 提供**一键全选发布文案代码块**，直接复制即可粘贴至平台创作者中心，告别繁重手工编辑；
   - 未生成文案的条目支持在看板内点击「✨ 立即生成多平台文案」就地补齐。
4. **分镜级多模态深度排查**：右侧逐幕核验黄金分割大字、AI 自主选风决策依据、独立播放各幕 TTS 语音对比音画对齐度、同屏排查首帧原画与 I2V 微动切片；
5. **一键工单流转**：
   - 点击 **`⭐ 审核通过 (Mark Approved)`**：将条目推进至业务终态 `Approved`，同步更新数据库与 `progress.json`；
   - 点击 **`📝 标记需修订 (Needs Revision)`**：输入具体批注（如“第 3 幕原画需重抽”），持久化至条目 notes；
   - 点击 **`🔄 重置状态`**：可将条目一键回退至 `Pending` 或 `Script_Generated`，方便流水线增量重新生成。

---

## 8. 常见问题排查与 FAQ (Troubleshooting)

### Q1: 在 Windows PowerShell 运行脚本时出现中文乱码或 `UnicodeEncodeError`？
- **原因**：Windows 默认控制台代码页为 CP936 或 CP932，无法正确显示个别 UTF-8 生僻字符。
- **解决**：在命令前设置环境变量，或在 PowerShell 中执行：
  ```powershell
  $env:PYTHONIOENCODING="utf-8"
  [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
  ```

### Q2: 提示 `Live muse-spark error` 或 `Live image generation warning`？
- **原因**：网络波动、境外 API 访问超时，或 `.env` 中的 `MUSE_API_KEY` 未配置。
- **处理**：
  1. 检查 `.env` 文件中的 `MUSE_API_KEY` 是否有效。
  2. 脚本具备高健壮性降级机制，如果 API 偶尔报错，会自动降级采用结构化规则脚本与优雅占位图保护流程不中断。
  3. 可加 `--force` 参数对该条目重新生成。

### Q3: 生成的视频在哪里？如何直接播放预览？
- **位置**：`output/final_videos/` 目录下。
- **预览**：在 Windows 文件资源管理器中直接双击 `.mp4` 文件即可通过系统播放器播放。同目录下的同名 `.srt` 文件会被 PotPlayer、VLC 自动识别加载为外挂软字幕。

### Q4: 如何在剪映 (CapCut) 或 Premiere 中导入成片与 .srt 进行二次精修？
- **操作方式**：
  1. 打开剪映专业版，创建新草稿（画幅设置为 9:16 竖屏）；
  2. 将 `output/final_videos/{clean_name}.mp4` 拖入视频主轨道；
  3. 点击顶部导航「文本」 ➔ 「本地字幕」 ➔ 「导入」，选择同名的 `{clean_name}.srt`；
  4. 字幕将自动精确吸附至解说音轨，可直接一键批量应用剪映热门的花字模板、关键词变色（标黄/放大）、入场飞入动画或 AI 智能配图。

### Q5: 如何单独重新排版封面卡片或重新导出断句级 SRT 字幕？
- **无需重新跑大模型或生图**，直接调用底层专用生成器：
  ```powershell
  # 重新排版渲染封面卡片
  python -m src.cover_generator --entry-id 01_001

  # 重新导出分镜级 SRT
  python -m src.srt_generator --entry-id 01_001

  # 导出自适应断句级细分 SRT（适合逐句跳字特效）
  python -m src.srt_generator --entry-id 01_001 --split
  ```

### Q6: 如何单独生成或批量生成多平台营销文案与标签？
- **直接调用文案模块**：
  ```powershell
  # 单条生成（调用 muse-spark）
  python -m src.copywriter --entry-id 01_001

  # 离线模拟批量生成（秒级就绪，适合大批量离线准备）
  python -m src.copywriter --all --mock
  ```
- 生成后可直接在 `04_review_dashboard.py` 看板中一键复制，或直接打开 `output/final_videos/{clean_name}_copywriting.txt`。

### Q7: 为什么不同社交平台导出视频体积不同？如何选择平台码率预设？
- **原因**：根据 [ADR-012](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-012-Social-Platform-Bitrate-Presets.md)，各平台服务器转码策略不同（例如小红书容易二次压缩降低清晰度，微信视频号更注重在弱网环境下秒开）。
- **参数选择指南**：
  - 上传小红书：`python 03_video_assembler.py --entry-id 01_001 --preset xhs`（CRF=19, VBV=4500k，抗二压保清）；
  - 上传抖音：`python 03_video_assembler.py --entry-id 01_001 --preset douyin`（CRF=20, VBV=6000k，高动态保真）；
  - 上传微信视频号：`python 03_video_assembler.py --entry-id 01_001 --preset wechat`（CRF=22, VBV=3500k，体积约 10MB，朋友圈秒开加载）；
  - 通用默认：`python 03_video_assembler.py --entry-id 01_001 --preset default`。
- 所有预设均已强制注入 `-movflags +faststart`，保障手机端点开即播。

### Q8: 调用主线路 Muse-Spark 或 Muse-Image 提示 `Request timed out` 或远端报 `MEMORY.md` 错误？
- **原因**：根据 [ADR-016](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-016-Muse2API-Reverse-Proxy-Timeout-and-Agent-Memory-Isolation.md)：
  1. 客户端超时设定过短（原 45s）：复杂 6 幕 JSON 分镜（40~120s）和 1024×1792 超清原画渲染（35~85s）超过 45s 时被客户端主动中断连接；
  2. 远端 muse.ai 底层为 Agent 架构：若批量生成时复用旧会话，上下文积累会导致远端 Agent 擅自调用后台命令修改 `/home/hatch/MEMORY.md`，出现红色 `エラー` 并阻塞正文输出。
- **解决对策**：
  1. 确保 `.env` 中 `API_TIMEOUT_SECONDS=180.0`；
  2. 服务端已应用会话强制隔离补丁，每次对话均自动导航至干净独立的 `/thread/new`，切断一切历史记忆干扰；
  3. 提示词尾部保持强约束（`prompt_builder.py` 已内置“禁止调用工具、严禁编辑任何 MEMORY.md”铁律）。

### Q9: muse 管理后台账号出现「任务异常: 参考图上传未确认，已停止生成」或「提示词发送未确认」？
- **原因**：根据 [ADR-017](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-017-Native-CDP-File-Upload-and-Multi-Language-DOM-Robustness.md)：
  1. **现代 Chromium 安全策略拦截**：旧版反代代码使用网页前端 JS `DataTransfer` 模拟向 `<input type="file">` 赋值，被 Chromium C++ 底层静默拦截，导致实际文件数量为 0，等待 15 秒后触发超时报错；
  2. **DOM 结构与多语言选择器漂移**：远端 composer 去除了外层 `<form>` 标签；且部分账号界面为日文（发送按钮为 `送信`、移除附件为 `添付ファイルを削除`），旧版硬编码中英文字符串（`发送`/`send`/`移除附件`）无法命中；
  3. **账号池连锁多米诺反应**：单个任务失败后服务端切号重试，池内所有账号相继失败并持久化错误 Note，同时霸占全局锁 (`GEN_LOCK`) 导致后续客户端请求连锁超时。
- **解决对策**：
  1. **换用原生 CDP 文件注入**：弃用 JS 模拟，改用 `DOM.setFileInputFiles(files=[tmp_file], objectId=...)`，以浏览器底层调试器最高权限将临时物理文件挂载至输入框，100% 触发 React 上传；
  2. **多语言 DOM 全方位适配**：在 `_send`、`_clear_attachments`、`_attach_image`、`_download_fallback` 中全面兼容中/英/日（`送信`、`添付ファイルを削除`、`ダウンロード`、`ストップ` 等），并解除对 `<form>` 的依赖；
  3. **空入参防御与自愈机制**：在 API 网关处严格清洗空字符串参考图，自动保活守护进程定期巡检唤醒 VM 并自动重置历史错误 Note。

### Q10: 远端出现「这张按原描述没能生成出来，生成替代版：...点下面就行」及敏感词拦截？
- **原因**：
  1. **触发 Meta Hatch 内容安全策略 (AI Safety Guardrails)**：例如提示词中包含 `cigarette`, `smoking`, `ashtray filled with ashes`, `blood`, `wound` 等烟草/吸烟、医疗创伤敏感元素时，底层生图模型拒绝生成；
  2. **智能 Agent 交互式替代机制**：Meta Hatch 未死板报错，而是自主将画面改写为合规方案（如“倒扣的空烟灰缸 + 胸片 + 窗光”），并在前端渲染了交互按钮 `<button>生成替代版：...</button>` 等待人工点击。在无人点击时，自动化程序会因超时或纯文本拒答而失败。
- **解决对策（已落地双重防护）**：
  1. **反代服务端自动嗅探并点击（Self-Healing Auto-Click）**：`muse2api` 的 `_wait_attachment` 轮询已内置交互建议检测器，0.5 秒内自动匹配并点击“生成替代版”交互按钮，自动延长超时并给予宽限期，无需人工介入即可顺利出图；
  2. **上游分镜生成源头安全隐喻化**：[`src/prompt_builder.py`](file:///c:/develop/HowToLiveBetter-Motion/src/prompt_builder.py) 已内置安全隐喻转换铁律（严禁直接出现烟草/吸烟/开放性创伤词汇，统一自动改写为“倒扣的洁净空烟灰缸”、“无烟健康日历”、“温和医生问诊报告”等积极意象），从源头 100% 避免触发审查，提升生成速度。

### Q11: 如何扩充白板模式的 SVG 图库？能否直接放入自定义 SVG 或将 SD 像素图转为矢量？
- **机制说明**：成片中绘制的图形（如汽车、安全带等）**直接来源于高精度的 SVG 矢量数学曲线**，因此在 1080×1920 高清竖屏下放大毫无马赛克毛边，触控笔能严格顺着矢量控制点逐帧描画。
- **扩展方式 A：直接加入自定义 SVG 矢量文件**：
  1. 将任意标准 `.svg` 矢量文件（如从 [SVGRepo](https://www.svgrepo.com/)、Iconfont 下载的线条图，或 Illustrator/Figma 绘制的矢量图）保存到 `assets/whiteboard/svg/{icon_name}.svg`；
  2. 打开 [`src/whiteboard/svg_library.py`](file:///c:/develop/HowToLiveBetter-Motion/src/whiteboard/svg_library.py)，在 `SEMANTIC_KEYWORD_MAP` 中添加该图素的中文/英文关联词（如 `"airplane": ["飞机", "航线", "出行", "出差"]`）；
  3. 重新运行白板生成命令，系统即会自动匹配并在分镜中由金属触控笔逐帧写画。
- **扩展方式 B：将本地 SD 生成的像素图转为 SVG 矢量**：
  1. 本地 Stable Diffusion / ComfyUI 生成高反差黑白线稿图（PNG/JPG）；
  2. 使用命令行矢量化工具转换为 SVG：
     ```powershell
     # 使用开源 vtracer 快速将黑白位图矢量化
     pip install vtracer
     vtracer --input my_sketch.png --output assets/whiteboard/svg/my_icon.svg --colormode binary
     ```
  3. 系统底层解析器自动兼容三次贝塞尔曲线及折线，无缝转化为触控笔轨迹。





