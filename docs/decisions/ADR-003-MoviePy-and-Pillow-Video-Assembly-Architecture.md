# ADR-003: 视频组装引擎与黄金分割排版架构 (Pillow + MoviePy)

## 状态 (Status)
**Accepted (已采纳实施)**

## 日期 (Date)
2026-10-11

## 背景与上下文 (Context)
在音视频后期合成（`03_video_assembler.py`）模块中，需要将多段 9:16（1024×1792）图片资产、TTS 解说语音轨、BGM 音频轨、运镜动效以及中文字幕合成导出为 1080×1920 高清短视频。
在技术选型与实现中面临三大痛点：
1. **Windows 平台 ImageMagick 依赖灾难**：
   - MoviePy 原生 `TextClip` 强制要求在操作系统中安装 `ImageMagick`，并正确配置注册表和 `MAGICK_HOME` 环境变量。在 Windows 环境下极易产生 `ImageMagick is not installed`、找不到中文字体或中文渲染乱码崩溃等问题。
2. **手机端短视频 UI 遮挡问题**：
   - 抖音、小红书、视频号的竖屏界面在底部（0~400px）有密集的点赞、评论、转发、输入框和作者头像；在顶部（0~300px）有状态栏和返回键。如果字幕居中偏下放置（如常规 1500~1700px），会被平台 UI 完全遮挡。
3. **幻灯片死板无动效感**：
   - 静态图片如果直接拼接，画面极度死板，缺乏短视频平台的视觉动态流动感。

## 架构决策 (Decision)

### 1. 废除 ImageMagick 依赖，采用 Pillow (PIL) 原生高质量中文字幕渲染
- 在 `src/assembler.py` 中自主实现纯 Python 的 PIL 排版绘制引擎。
- 自动探测 Windows 本地自带的中文字体（优先 `msyhbd.ttc` 微软雅黑粗体、`simhei.ttf` 黑体，或本地 `assets/fonts/` 字体），零外部环境配置。
- 支持绘制多行自动换行、阴影（Drop Shadow）、微半透明磨砂背景胶囊框（Rounded Rectangle with Alpha），生成 RGBA 内存图层转换为 MoviePy 的 `ImageClip`。

### 2. 竖屏黄金分割视觉层次排版
针对 1080×1920 竖屏画布（高度 $H = 1920$）：
- **上部黄金分割点（$Y \approx 733\text{px}$）**：
  - 放置 **核心浮现字徽章 (Kinetic Typography Badge)**。
  - 选用高辨识度琥珀暖金配色（`#D97706` 边框，`#FFFBEB` 高亮大字），在各分镜第 0.2s 快速缩放弹出，停留 2.5s，抓取观众眼球重音。
- **下部黄金分割点（$Y \approx 1186\text{px}$）**：
  - 放置 **旁白解说字幕胶囊 (Frosted Dark Glass Subtitle Capsule)**。
  - 选用深黑微透明胶囊框（`rgba(15, 23, 42, 0.72)`，圆角 22px），搭配清晰居中白色文字（`#F8FAFC`）。
  - 该高度恰好位于短视频黄金视觉焦点，同时距离底部 734px，**完美避开小红书与抖音底部全部交互按钮**！

### 3. Ken Burns 电影感运镜与 0.5s 交叉溶解转场
- 对每镜静态图片应用细微动态相机运动（`zoom_in` 1.0 $\to$ 1.08、`zoom_out` 1.08 $\to$ 1.0、`pan_left`、`pan_right`）。
- 相邻分镜间应用 $0.5\text{s}$ 交叉溶解（`crossfadein(0.5)`），营造连贯流畅的呼吸感。

## 备选方案评估 (Alternatives Considered)

### 备选方案 A：继续使用 MoviePy TextClip + ImageMagick
- **缺点**：测试过程中反复因 Windows 注册表和字体路径失败，不具备跨机器一致性与开箱即用性。
- **结论**：**否决**。

### 备选方案 B：直接拼接生成原生 FFmpeg 命令行滤镜字符串
- **缺点**：复杂多轨交叉溶解与运镜的 FFmpeg filter-complex 字符串长度超过数千字符，调试极其痛苦，出错时错误提示极不友好。
- **结论**：**否决（保留 MoviePy 作为主编排引擎，由底层 `imageio_ffmpeg` 负责最终 H.264 编码）**。

## 实施后果与收益 (Consequences)
- 彻底摆脱 ImageMagick 外部软件依赖，`pip install -r requirements.txt` 即可直接跑通。
- 生成的 MP4 在抖音、小红书和视频号真机播放时，上下黄金分割点文字均一览无余，视觉层次极其高级。
