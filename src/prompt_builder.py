"""Prompt builder combining HowToLiveBetter entries with huashu-art-motion aesthetic philosophies."""

from typing import Any, Dict


STYLE_RECIPES = {
    "25_ghibli": {
        "name": "吉卜力暖调手绘风",
        "description": "水彩洗染、自然漫射暖阳、质朴生活细节、温润治愈手绘感",
        "keywords": "Studio Ghibli aesthetic, hand-drawn anime background, warm natural sunlight, gouache wash texture, meticulous everyday details, peaceful and clean composition",
        "negative": "blurry, low quality, neon purple futuristic cyber, abstract glowing icons, 3d glossy render, watermark, text"
    },
    "y1_kurzgesagt": {
        "name": "Kurzgesagt 扁平科普风",
        "description": "高饱和纯净色块、几何轮廓分明、极简无描边或清晰轮廓、童趣明晰科普感",
        "keywords": "Kurzgesagt art style, clean flat vector illustration, rich vibrant solid colors, whimsical scientific infographic, sharp geometric silhouettes, immaculate lighting",
        "negative": "photorealistic, noisy gradients, 3d render, dark neon cyber, blurry, deformed, watermark"
    },
    "y2_vox": {
        "name": "Vox 调查剪报拼贴风",
        "description": "真实复古纸纹、剪报拼贴、红线引导、档案感、高对比黑白配高饱和重点色",
        "keywords": "Vox-style investigative collage, torn aged paper textures, archival document aesthetic, high contrast red accents, halftone printing dots, sharp journalistic details",
        "negative": "cartoonish, cute anime, pastel tones, 3d glossy, abstract sci-fi, blurry, watermark"
    },
    "13_pop": {
        "name": "利希滕斯坦波普艺术风",
        "description": "本戴点网格纹理、粗重黑色描边、经典美漫原色冲击、复古摩登",
        "keywords": "Roy Lichtenstein pop art, Ben-Day dots texture, bold black outlines, vintage comic book aesthetic, vibrant primary colors, graphic punchy composition",
        "negative": "soft watercolor, photorealistic, gloomy dark, 3d cgi, blurry, watermark"
    },
    "24_hopper": {
        "name": "霍珀美国现实主义风",
        "description": "强烈斜射几何光块、深思熟虑的构图、市井生活写实、克制孤独感",
        "keywords": "Edward Hopper American realism style, dramatic geometric sunlight shadows, architectural clean planes, contemplative atmosphere, cinematic framing",
        "negative": "anime, cute cartoon, cyberpunk neon, hyper-saturated fantasy, chaotic details, watermark"
    }
}


def recommend_style_for_entry(chapter_index: int) -> str:
    """Recommend a style card based on chapter domain."""
    # 01(不要早死), 02(不要慢慢死), 13(紧急情况), 24(看病) -> Ghibli (温润生活守护)
    if chapter_index in (1, 2, 13, 24, 27, 34):
        return "25_ghibli"
    # 05(不要浪费钱), 08(别把自己搭进去), 09(法律红线), 11(技术红线), 12(创业), 15(买房租房) -> Vox / Pop (硬核证据与规则)
    elif chapter_index in (5, 8, 9, 11, 12, 15, 19):
        return "y2_vox"
    # 03(精力), 04(时间), 06(反面清单), 23(学技能) -> Kurzgesagt (清晰机制拆解)
    elif chapter_index in (3, 4, 6, 23, 26):
        return "y1_kurzgesagt"
    # 07(没钱), 10(恋爱结婚), 17(老人), 18(养孩子), 22(放松), 29(重大打击) -> Hopper (真实人情生活)
    else:
        return "24_hopper"


def build_system_prompt() -> str:
    """System prompt embedding huashu-art-motion principles for muse-spark."""
    return """你是一位顶级短视频总导演兼视觉分镜大师，精通开源动画项目 `huashu-art-motion` 的美学和解说语法。
你的任务是将提供的高性价比人生指南条目，转化为一份极具观赏性、节奏紧凑、绝无低质 AI 感的 30 秒大众科普短视频分镜脚本。

【核心设计铁律】
1. **时长控制**：全片时长严格控制在 25 ~ 30 秒以内，适合抖音、小红书和视频号短视频。
2. **视频标题**：必须遵循格式 `"{章节名}之{小条目标题}"`。
3. **拒斥 AI Slop (防劣质 AI 原则)**：
   - 严禁任何蓝紫霓虹、深紫星空、炫光光球、数据流雨、无脸白模人偶、抽象悬浮几何体！
   - 全片必须锁定单一、统一的高级艺术画风和调和色板。
4. **镜头里必须有“具体的物与动作”**：
   - 拒绝空洞的符号。必须落在生活场景中具体的实体物件和物理动作上（如系扣安全带、旋紧燃气阀门、电子血压计数字跳动、纸质药盒、窗框限位锁）。
5. **脉冲式节奏与镜头事件 (Pulse Rhythm)**：
   - 全片划分 3 到 4 个分镜：
     * 第 1 镜 (0-4秒 抓眼钩子)：生活场景具体物动作 + 抛出痛点或反直觉事实。
     * 第 2 镜 (4-12秒 核心论据与颠覆)：核心数据震撼对比、说人话解释。
     * 第 3 镜 (12-22秒 行动与成本收益)：极低成本 vs 极高收益，权威背书（WHO/国家规章）。
     * 第 4 镜 (22-28秒 金句定格落定)：具体的行动指令与金句结语。
6. **核心浮现字 (Kinetic Typography)**：
   - 每一镜提炼 1 个简短有力的屏幕浮现词（2-8字），用于短视频大字冲击，例如“风险降50%”、“后排不系 60%致命”、“成本=0秒”。
7. **多模态视觉 Prompts 规范**：
   - `image_prompt`: 英文，面向生图模型。必须包含具体的物理实体、动作、构图（9:16 vertical ratio）、景别、光影质感，以及所选风格的关键词。
   - `video_motion_prompt`: 英文，面向视频运镜控制。写明镜头运动（如 `Camera quick punch-in zoom`, `Smooth lateral tracking pan`, `Static grounded hold`）与微动细节。

【输出格式】
你必须直接输出严格的 JSON 对象（不要包裹 Markdown 代码块外的废话），其结构如下：
{
  "entry_id": "01_001",
  "video_title": "不要早死之系安全带，前排后排都系",
  "target_duration_sec": 28,
  "art_style_id": "25_ghibli",
  "art_style_name": "吉卜力暖调手绘风",
  "color_palette": ["#...", "#...", "#..."],
  "narration_text_full": "完整旁白文本...",
  "scenes": [
    {
      "scene_index": 1,
      "time_range": "0.0-4.0",
      "duration_sec": 4.0,
      "narration_segment": "分镜口播文本",
      "primary_subject": "具象主体（名词）",
      "visual_action": "主体在做什么动作及镜头事件（动词）",
      "kinetic_typography": {
        "text": "浮现核心字",
        "style": "slam_in",
        "position": "center_high"
      },
      "image_prompt": "Detailed English prompt for image generation, 9:16 vertical aspect ratio...",
      "video_motion_prompt": "Camera motion prompt in English..."
    }
  ]
}
"""


def build_user_prompt(entry: Dict[str, Any]) -> str:
    """Build user prompt with entry data and recommended style card."""
    style_id = recommend_style_for_entry(entry.get("chapter_index", 1))
    style_info = STYLE_RECIPES.get(style_id, STYLE_RECIPES["25_ghibli"])

    chapter_title = entry.get("chapter_title", "")
    item_title = entry.get("title", "")
    entry_id = entry.get("id", "")
    cost_desc = entry.get("cost_desc", "不花钱")
    plain_text = entry.get("plain_text", "")
    benefit_desc = entry.get("benefit_desc", "")
    evidence_grade = entry.get("evidence_grade", "A")
    notes = entry.get("notes", "")

    return f"""请将以下条目转化为 30 秒高性价比人生指南短视频分镜脚本：

【条目编号】: {entry_id}
【章节】: {chapter_title}
【小条目标题】: {item_title}
【成本情况】: {cost_desc}
【说人话（核心要点）】: {plain_text}
【权威收益与数据】: {benefit_desc}
【证据等级】: {evidence_grade} 级
【补充备注】: {notes}

【推荐视觉风格】:
- 风格 ID: {style_id}
- 风格名称: {style_info['name']}
- 风格美学特征: {style_info['description']}
- 提示词基石: {style_info['keywords']}

请严格输出指定 JSON 格式，标题统一命名为："{chapter_title}之{item_title}"。"""
