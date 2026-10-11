# HowToLiveBetter-Motion 全流程运用手册 (Operations Manual)

> 本手册为 `HowToLiveBetter-Motion`（高性价比人生指南 · 短视频自动化流水线）的标准运维与操作指南。涵盖环境配置、标准生产流程（SOP）、高级调度技巧、配乐与画风定制、数据库状态运维及平台发布质检清单。

---

## 1. 系统环境与前置准备 (Prerequisites)

### 1.1 运行环境要求
- **操作系统**：Windows 10 / 11（已内置微软雅黑字体与 UTF-8 终端适配）或 Linux / macOS
- **Python 版本**：Python 3.10 ~ 3.14
- **硬件要求**：
  - CPU：4 核以上
  - 内存：8GB RAM 以上（MoviePy 视频渲染峰值占用约 1~2GB）
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

整个短视频自动化生产流水线由 3 个独立且解耦的步骤组成，支持随时中断和断点续传：

```
[01_data_extractor.py] ──► [02_ai_generator.py] ──► [03_video_assembler.py] ──► 成片交付
      (数据抽取)                 (分镜+生图+TTS)                (运镜+文字+混音)
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

本步骤调用 `muse-spark` 生成紧凑四幕分镜，调用 `muse-image` 生成 9:16 原画，并调用 Edge-TTS 生成解说音频。

```powershell
# 2.1 单条生成（默认 AI 自主选风，最推荐）
python 02_ai_generator.py --entry-id 01_001

# 2.2 批量生成待处理的前 3 个条目
python 02_ai_generator.py --limit 3

# 2.3 强制覆盖重跑已生成条目
python 02_ai_generator.py --entry-id 01_001 --force

# 2.4 离线/模拟测试模式 (不消耗 API 额度，快速验证流程)
python 02_ai_generator.py --entry-id 01_001 --mock --force
```

- **输出产物**（存放于 `output/raw_assets/{entry_id}/`）：
  - `cover.png`：[新增] 1080×1920 竖屏高辨识度专属封面卡片（小红书/抖音首选发布首图）。
  - `storyboard.json`：分镜脚本、Prompt、所选画风与选风理由、精准语音与分镜时长。
  - `scene_01.png` ~ `scene_04.png`：1024×1792 竖屏原画素材。
  - `voice_01.mp3` ~ `voice_04.mp3`：各分镜解说音频。

> 💡 **独立重制封面卡片命令**：
> 如需单独针对某一条目重新排版渲染封面图，可直接调用独立生成器：
> ```powershell
> python -m src.cover_generator --entry-id 01_001
> ```

---

### 步骤 3：影视级视频组装与双轨混音 (`03_video_assembler.py`)

本步骤将图片、运镜动效、转场溶解、黄金分割点文字卡片及 BGM 进行渲染，输出最终 MP4，并自动将发布首图同步复制至交付目录。

```powershell
# 3.1 合成指定条目的最终成片
python 03_video_assembler.py --entry-id 01_001

# 3.2 批量合成已完成素材生成的全部视频
python 03_video_assembler.py --limit 5

# 3.3 强制重新渲染合成
python 03_video_assembler.py --entry-id 01_001 --force
```

- **输出产物**（存放于 `output/final_videos/`）：
  - `{entry_id}_{章节名}之{小条目标题}.mp4`：1080×1920 竖屏成片（约 25~35 秒，8~15MB）。
  - `{entry_id}_{章节名}之{小条目标题}_cover.png`：配套的高清专属发布首图。


---

## 4. 艺术画风定制与调度技巧 (Art Styles)

系统内置 7 款基于开源 `huashu-art-motion` 研发的艺术画风，通过 `--style` 参数灵活调度：

| 风格代号 (`style_id`) | 风格名称 | 核心美学特征 | 适用内容场景推荐 |
|---|---|---|---|
| **`25_ghibli`** | 吉卜力暖调手绘风 | 水彩洗染、自然阳光漫射、质朴器物细节 | 生活好习惯、家庭温情、日常防护、治愈健康 |
| **`y2_vox`** | Vox 调查剪报拼贴风 | 真实纸纹、档案卷宗、红线连接、黑白配警示红 | 法律红线、金融避坑、借贷合同、防诈警示 |
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
# 强制采用 Vox 剪报风做视觉效果对比
python 02_ai_generator.py --entry-id 01_001 --style y2_vox --force
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
- [ ] **5. 人声清晰度**：云泽的声音是否洪亮饱满？背景音乐是否处于柔和衬底状态？
- [ ] **6. 画面质感**：画面是否统一遵循指定艺术风格？是否有手部异形或明显畸变？

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
- **预览**：在 Windows 文件资源管理器中直接双击 `.mp4` 文件即可通过系统播放器播放。
