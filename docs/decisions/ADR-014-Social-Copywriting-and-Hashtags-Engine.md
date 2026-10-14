# ADR-014: 多平台爆款营销文案与高权重标签生成引擎架构 (Social Copywriting & Hashtags Engine Architecture)

## 状态 (Status)
**Accepted (已采纳实施 · 2026-10-12)**

## 日期 (Date)
2026-10-12

## 背景与上下文 (Context)
在项目完成短视频装配（1080×1920 MP4）、专属封面（Cover Card）、独立字幕（SRT）与本地审核看板后，流水线已能批量产出高质量音视频实体。

然而，在自媒体工业化发布环节中，创作者依然面临巨大的运营人工瓶颈：
1. **多平台流量机制差异显著**：
   - **小红书 (Xiaohongshu)**：依赖“前两行标题吸引力”、“生活痛点/情绪共鸣导语”、“Emoji 结构化排版”与“精准细分话题标签（Tags）”，缺少 Emoji 或大段生硬文字会导致笔记 CTR 极低；
   - **抖音 (Douyin)**：依赖“黄金 3 秒停留率（Hook）”、“极简短标题（<20字）”与“泛娱乐大流量热搜话题”；
   - **微信视频号 (WeChat Channels)**：依赖“高公信力、温和利他表达”与“适合转发至亲友群/朋友圈的推荐语”。
2. **海量条目运营负担沉重**：全书 677 篇短视频如果依靠人工逐一撰写发布文案，耗时耗力且难以维持统一的文案水准与硬核循证调性。

为此，需建立一套基于大模型提示词工程与领域模板的多平台营销文案自动生成引擎（TASK-5.2）。

---

## 架构决策 (Decision)

### 1. 结构化多平台文案数据协议 (`src/copywriter.py`)
建立面向社媒自动分发的统一 JSON 数据协议：
```json
{
  "entry_id": "01_001",
  "title": "系安全带，前排后排都系",
  "xhs": {
    "title_candidates": ["备选标题1", "备选标题2", "备选标题3"],
    "intro": "颠覆常识的日常痛点导语...",
    "body_points": ["📌 硬核真相...", "⚠️ 惊人事实...", "💰 执行代价..."],
    "call_to_action": "行动呼吁与利他转发金句...",
    "tags": ["#生活百科", "#硬核科普", "#高性价比生活"],
    "full_post": "排版完整的小红书正文（一键全选复制）"
  },
  "douyin": {
    "title": "精炼短标题（18字以内）",
    "hook": "黄金 3 秒完播钩子文案",
    "caption": "视频描述文本",
    "tags": ["#涨知识", "#硬核科普", "#生活指南"]
  },
  "wechat": {
    "title": "沉稳公信力标题",
    "share_text": "朋友圈/相亲相爱一家人转发推荐语",
    "tags": ["#生活智慧", "#健康守护", "#家庭生活"]
  }
}
```

### 2. 双轨产物交付与持久化规范
为兼顾自动化调用与创作者直观操作，引擎生成两套物理交付物：
1. **机器可读格式**：`output/raw_assets/{id}/copywriting.json`（供后续 API 自动分发或创作者工具集成）；
2. **人类排版格式**：`output/final_videos/{clean_name}_copywriting.txt`（以清晰的分隔线排版，包含小红书一键全选复制块、抖音信息流描述与微信视频号转发语，自媒体运营者打开即可直接复制）。

### 3. 本地审核看板无缝集成 (`04_review_dashboard.py`)
在本地 Streamlit 审核工作台中开辟专门的「📢 多平台爆款营销文案与标签」面板：
- 针对当前条目呈现 `📕 小红书专属`、`🎵 抖音短视频`、`🟢 微信视频号` 三大子选项卡；
- 小红书候选标题以高亮块呈现；正文文本框支持直接一键全选复制；标签矩阵以可读徽章展示；
- 提供一键 `✨ 立即生成多平台文案` 按钮，支持按需动态重抽。

### 4. 离线/模拟生成与重试容灾
在 `Copywriter` 类中内建：
- 优先调用 `muse-spark` 执行生动创作，接入 [ADR-011](file:///c:/develop/HowToLiveBetter-Motion/docs/decisions/ADR-011-Rate-Limiting-and-Exponential-Backoff.md) 令牌桶速率控制与指数退避重试；
- 若离线或无 API Key 时，自动启用高质量规则模板（`_mock_copywriting_generation`），提取条目中的数据、代价与收益，智能拼装 Emoji 与真实标签，保证离线研发与断网测试 100% 可用。

---

## 备选方案评估 (Alternatives Considered)

### 备选方案 A：发布前由人工手工逐条撰写
- **缺点**：677 篇短视频预计耗费运营人员数百工时，且文案质量参差不齐，容易遗漏关键硬核证据。
- **结论**：**否决**。

### 备选方案 B：仅生成通用的简短描述，多平台共用同一套文案
- **缺点**：不符合不同平台的算法推荐偏好（小红书用户反感无 Emoji 的生硬口吻；抖音用户不会阅读长篇大论；视频号用户对过于夸张的标题党产生抗拒）。
- **结论**：**否决**。

---

## 实施后果与收益 (Consequences)

### 正面收益
1. **发布周期压缩至秒级**：运营人员从创作文案的繁重劳动中解放出来，仅需复制粘贴；
2. **多平台定制化流量提升**：精准匹配小红书种草、抖音完播与微信视频号裂变的算法特性；
3. **交付物四件套完备闭环**：至此交付体系升级为 **MP4 成片 + SRT 字幕 + Cover 封面卡 + Copywriting 发布文案** 标准化四件套。

---

## 实施与工程落地成果 (Implementation & Verification)

1. **核心引擎模块**：
   - [`src/copywriter.py`](file:///c:/develop/HowToLiveBetter-Motion/src/copywriter.py)：支持 CLI 单条/批量生成、双轨 Prompt 编译、格式化文本输出与 JSON 持久化。
2. **看板交互集成**：
   - [`04_review_dashboard.py`](file:///c:/develop/HowToLiveBetter-Motion/04_review_dashboard.py)：新增三平台文案排版卡片与即时生成重载按钮。
3. **自动化测试守门**：
   - [`tests/test_copywriter.py`](file:///c:/develop/HowToLiveBetter-Motion/tests/test_copywriter.py)：4 项针对 Prompt 编译、三平台结构完整性、产物文件生成与 JSON 清洗容错的测试 100% 绿灯。
