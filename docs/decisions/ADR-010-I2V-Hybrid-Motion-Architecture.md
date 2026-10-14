# ADR-010: 图生视频 (Image-to-Video, I2V) 混合动态微动架构与演进路线

## 状态 (Status)
**Accepted (已实施 · 2026-10-12)**

## 日期 (Date)
2026-10-12

## 背景与上下文 (Context)
在当前流水线中，视频装配阶段（[ADR-003](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-003-MoviePy-and-Pillow-Video-Assembly-Architecture.md) 与 [ADR-008](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-008-Golden-6-Scenes-Narrative-Pulse-Rhythm.md)）采用 `muse-image` 生成 1024×1792 高清艺术原画，配合 MoviePy 的 Ken Burns 运镜（`zoom_in`、`zoom_out`、`pan_left`、`pan_right`）与 0.5s 交叉溶解实现动态效果。

这一方案在成本控制、画风稳定性与「以声定景」（[ADR-004](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-004-Edge-TTS-Integration-and-Audio-Driven-Timing.md)）动态时间轴对齐上达到了极高的工程平衡点。然而在实际视觉表现力上存在天然局限：
1. **伪动效与静态感**：Ken Burns 仅能对整幅二维图像做仿射变换，画面主体缺乏内部物理微动（如安全带卡扣的按压锁止、水汽升腾、血压计数字跳动、门把手旋动）；
2. **纯文生视频 (T2V) 的不可行性**：直接调用大模型文本生视频（Text-to-Video）存在三大硬伤：
   - **画风崩溃与 AI Slop 风险**：小众艺术风格（水墨、剪报、波普、吉卜力手绘）在视频帧间极易闪烁、形变与画风漂移；
   - **时间轴刚性脱节**：视频模型通常输出固定长度（如 3s 或 4s），无法匹配 TTS 动态浮点秒数（如 4.7s），强行变速会导致动作畸变；
   - **成本与耗时失控**：全书 677 条目 × 6 幕 = 4062 个镜头，直接生成视频会产生巨大的 API 账单与漫长排队等待，破坏自动化量产可行性。

为了在“物理级微动真实感”与“画风稳定、精准对齐、可控成本”之间取得统一，本决策确立了基于 **“图生视频 (Image-to-Video, I2V)” 的混合动态微动架构**。

---

## 架构决策 (Decision)

### 1. “首帧高精原画锚定 + I2V 物理微动” 双阶段生成闭环
不再使用端到端纯文生视频（T2V），而是将视觉生成解耦为两级管道：
```
[muse-spark 分镜与双轨 Prompt]
           │
           ▼
[阶段 1: muse-image 生成首帧原画 (scene_{i}.png)] ──► 100% 锁定风格卡、色调与高质量构图
           │
           ▼
[阶段 2: muse-video 首帧驱动 I2V 运算] ──────────► 以原画为首帧，输入 video_motion_prompt 生成 2.5~3.5s 物理微动
           │
           ▼
[阶段 3: 自适应定格/缓动扩展 (Freeze-and-Drift)] ──► 动态补齐 TTS 音频所需剩余秒数 (以声定景毫秒级对齐)
           │
           ▼
[阶段 4: MoviePy/FFmpeg 复合装配与字幕混音] ──────► 叠加 Pillow 黄金分割字幕与 BGM 导出成片
```

### 2. 双轨提示词工程协同 (`image_prompt` + `video_motion_prompt`)
充分激活 `system_design.md` 中预留的数据协议契约：
- **`image_prompt`**：专注于静态艺术主体、环境空间、艺术风格卡关键词（如 `Studio Ghibli aesthetic, gouache wash texture`）与 9:16 竖屏构图；
- **`video_motion_prompt`**：专注于动量控制与物理细节，采用标准化动词语法：
  `Camera: {camera_movement_type}, Subject: {physical_micro_movement}, photorealistic motion physics, clean frame transition`。

### 3. 分镜分级混合策略 (Tiered Motion Strategy)
避免对 6 幕无差别启用视频生成，实施精细化成本与注意力投资策略：
- **Tier-1 核心焦点幕 (必须微动)**：
  - **第 1 幕 (0-4.5s 抓眼钩子)**：前 3 秒留存率是短视频生命线，必须调用 I2V 生成强烈的物理微动作（如扣卡扣、滴水、撕纸）；
  - **第 5 幕 (极低成本示范)**：涉及手部微操作或工具使用的场景，调用 I2V 呈现具体操作过程。
- **Tier-2 叙事与论证幕 (维持 Ken Burns)**：
  - **第 2、3、4、6 幕**（误区全貌、机理、权威标签、金句定格）：以信息图表、场景全景与文字阅读为主，继续沿用高质感 Ken Burns 运镜，保证文字背景稳定不干扰阅读。
- **收益**：视频生成 API 调用量从 6 次/条骤降至 1~2 次/条，成本与等待时间降低 **70%** 以上。

### 4. “自适应微动尾帧定格 (Freeze-and-Drift)” 时间轴对齐算法
解决视频切片定长（如 3.0s）与 TTS 音频动态时长（如 4.8s）的失步矛盾：
- 当 $T_{video} < T_{scene}$ 时：
  - 前 $T_{video}$ 秒播放 I2V 生成的真实物理微动视频；
  - 尾部剩余的 $\Delta T = T_{scene} - T_{video}$ 时间，提取视频末帧，施加极低速的微幅缓慢推拉（Subtle Drift，变化率 $< 2\%$），形成自然的电影定格呼吸感；
- 彻底维持 [ADR-004](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-004-Edge-TTS-Integration-and-Audio-Driven-Timing.md) 的动态时间公式与 [ADR-009](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-009-Standalone-SRT-Subtitle-Architecture.md) 的 SRT 毫秒级时间轴。

### 5. 自动熔断与向下兼容降级 (Fallback Resilience)
在 `src/muse_client.py` 与 `02_ai_generator.py` 中引入容灾分支：
- 若未配置 `MODEL_VIDEO`、API 限流（HTTP 429）、生成超时（>60s）或输出校验失败，流水线自动回退至纯 `muse-image` + Ken Burns 模式；
- 用户可通过命令行参数显式控制模式：
  - `--motion-mode static`（默认，纯原画 + Ken Burns，适合大规模全量跑）；
  - `--motion-mode i2v-tier1`（智能混合，仅第 1、5 幕 I2V）；
  - `--motion-mode i2v-all`（全量 6 幕 I2V，适合精品条目定制）。

---

## 备选方案评估 (Alternatives Considered)

### 备选方案 A：直接采用纯文生视频 (Text-to-Video, T2V)
- **缺点**：首帧无法锁定风格配方卡，非写实画风帧间严重频闪变形；时长无法配合 TTS；成本成倍暴涨。
- **结论**：**否决**。

### 备选方案 B：维持现状，完全不做主体微动
- **缺点**：虽然成本低且极其稳定，但长期来看，相比市场上具备局部微动的优质短视频，在平台完播率与视觉沉浸度上存在上限。
- **结论**：**保留为基底默认模式，通过 I2V 扩展作为高阶演进能力**。

---

## 实施后果与收益 (Consequences)

### 正面收益
1. **打破静态幻灯片感**：使短视频核心镜头拥有电影级的物理实体微动，前 3 秒吸睛度成倍提高；
2. **画风 100% 稳定可控**：以 `muse-image` 高清原画为首帧底图，消除风格突变与画风漂移；
3. **完美保留「以声定景」与外挂 SRT 机制**：结合 Freeze-and-Drift 算法，毫秒级音频对齐与软字幕不变形；
4. **极致成本效益**：通过 Tier-1 分级控制，以 25% 的视频生成开销换取 80% 的动态收益。

### 潜在代价与挑战
1. **网络与接口等待时间增加**：启用 I2V 的条目单条处理耗时将从 25s 增至约 50~90s；
2. **依赖视频生成 API 对首帧图（Image Input）的支持质量**：需要底层模型具备高保真 Image-to-Video 驱动能力。

---

## 实施与工程落地成果 (Implementation & Verification)

本架构决策于 2026-10-12 实施落地（**TASK-5.0**），关键组件如下：

1. **分级分镜路由器 (`src/muse_client.py` - `is_i2v_scene`)**：
   - 支持 `static`（纯原画运镜）、`i2v-tier1`（首幕钩子与第 5 幕行动示范）、`i2v-all`（全量 6 幕）；
   - 大小写容错与场景数弹性适配（4 幕 / 6 幕）。
2. **首帧驱动生成引擎 (`src/muse_client.py` - `generate_video`)**：
   - 优先以 `image_path` 为首帧驱动 `muse-video` 物理微动生成，兼容网关异常与速率重试；
   - 具备高效的模拟合成器（`_mock_video_generation`），以首帧为底图合成 24fps H.264 真实测试视频切片。
3. **自适应尾帧缓动定格引擎 (`src/assembler.py` - `create_freeze_and_drift_clip`)**：
   - 当 $T_{video} < T_{scene}$ 时，捕获视频末帧施加 1.2% 微幅呼吸推拉，通过 `concatenate_videoclips` 无缝延展补齐 TTS 动态时长；
   - 当 $T_{video} \ge T_{scene}$ 时，精确截取子切片；
   - 异常时自动平滑回退至静态原画 Ken Burns 运镜。
4. **流水线调度集成**：
   - `02_ai_generator.py`：新增 `--motion-mode [static|i2v-tier1|i2v-all]` 命令行参数，生成 `motion_{idx:02d}.mp4` 并记录至 `storyboard.json`；
   - `03_video_assembler.py`：自动识别 I2V 分镜并执行 Freeze-and-Drift 混流；
   - 环境变量与默认配置：`src/config.py` 与 `.env.example` 新增 `DEFAULT_MOTION_MODE`。
5. **自动化测试守门 (`tests/test_i2v_motion.py`)**：
   - 9 个专项测试用例 100% 覆盖路由器分类、Mock 视频生成、Freeze-and-Drift 延展截取、异常回退与图层合成。
