# ADR-004: Edge-TTS 语音解说接入与「以声定景」动态音画同步

## 状态 (Status)
**Accepted (已采纳实施)**

## 日期 (Date)
2026-10-11

## 背景与上下文 (Context)
在流水线早期原型中，视频只有背景音乐和浮现文字，没有语音讲解。短视频平台受众更偏好有声口播解说，人声能极大幅度提升内容吸收效率。
引入 TTS 讲解后，面临的核心技术挑战是：
1. **音质与音色说服力**：需要严肃、专业、可信且不机械的中文科普男声。
2. **音画时间轴失步**：如果分镜画面时长在脚本中被大模型预估为死板的固定秒数（例如每镜写死 6 秒），而实际 TTS 朗读耗时为 8.5 秒或 3.2 秒，就会导致“话没念完画面就切走了”或“念完了画面卡死僵住”。

## 架构决策 (Decision)

### 1. 接入 Cloudflare Worker 部署的 Edge-TTS 专有服务
- **端点**：`https://tts-voice-magic.shimizuhiro874-28e.workers.dev/v1/audio/speech`
- **音色选型**：`"zh-CN-YunzeNeural"`（云泽·男声解说）。该音色沉稳诚恳、字正腔圆，在专业解说、知识科普领域具有极强的公信力。
- **参数规格**：`speed: 1.0`，`pitch: "0"`，`style: "general"`。
- **客户端模块**：在 `src/tts_client.py` 中封装 `TTSClient`，支持 HTTP POST 请求并自动解析二进制音频流，落盘为 `output/raw_assets/{entry_id}/voice_01~04.mp3`。

### 2. “以声定景 (Audio-Driven Duration)” 动态音画同步公式
通过 `moviepy.AudioFileClip` 或 `ffprobe` 精准探测生成的 MP3 音频实际时长 $T_{audio}$，以音频时长为基准反向决定该分镜的画面展示时长 $T_{scene}$：

$$T_{scene}^{(i)} = \max\left(T_{audio}^{(i)} + \Delta t_{cushion},\; 3.0\right)$$

- 其中 $\Delta t_{cushion} = 0.5\text{s}$：作为句末呼吸留白，给予观众心理消化时间。
- 保底时长为 $3.0\text{s}$：防止极短口播导致的画面闪退。
- 回写 `storyboard.json` 中的 `duration_sec` 与 `audio_duration_sec`，在 `03_video_assembler.py` 中直接以此为准同步构建复合视频轨。

## 备选方案评估 (Alternatives Considered)

### 备选方案 A：本地离线 pyttsx3
- **缺点**：Windows SAPI 原生机械音严重，声音生硬干瘪，完全不适合短视频平台发布。
- **结论**：**否决**。

### 备选方案 B：固定分镜时长，通过 ffmpeg atempo 强行拉伸/压缩音频
- **缺点**：改变语速会导致音调失真、语速忽快忽慢，听感极其怪异。
- **结论**：**否决（语速必须恒定自然，由画面时长配合语音）**。

## 实施后果与收益 (Consequences)
- 讲解音质饱满自然，极具专业纪录片/科普短视频质感。
- 下部黄金分割点胶囊文字与云泽讲解完全同步呈现，分镜切换与说话节奏天衣无缝。
