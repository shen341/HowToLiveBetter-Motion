"""Prompt builder combining HowToLiveBetter entries with huashu-art-motion aesthetic philosophies."""

from typing import Any, Dict


STYLE_RECIPES = {
    "25_ghibli": {
        "name": "吉卜力暖调手绘风",
        "description": "水彩洗染、自然漫射暖阳、质朴生活细节、温润治愈手绘感",
        "suitable_for": "健康习惯、日常生活、家庭温情、身心治愈、生命保护类条目",
        "keywords": "Studio Ghibli aesthetic, hand-drawn anime background, warm natural sunlight, gouache wash texture, meticulous everyday details, peaceful and clean composition",
        "negative": "blurry, low quality, neon purple futuristic cyber, abstract glowing icons, 3d glossy render, watermark, text"
    },
    "y1_kurzgesagt": {
        "name": "Kurzgesagt 扁平科普风",
        "description": "高饱和纯净色块、几何轮廓分明、极简无描边或清晰轮廓、童趣明晰科普感",
        "suitable_for": "生理机制、医学常识、科学数据、精力时间管理、认知心理学拆解类条目",
        "keywords": "Kurzgesagt art style, clean flat vector illustration, rich vibrant solid colors, whimsical scientific infographic, sharp geometric silhouettes, immaculate lighting",
        "negative": "photorealistic, noisy gradients, 3d render, dark neon cyber, blurry, deformed, watermark"
    },
    "y2_vox": {
        "name": "Vox 调查剪报拼贴风",
        "description": "真实复古纸纹、剪报拼贴、红线引导、档案卷宗感、高对比黑白配高饱和警示色",
        "suitable_for": "法律红线、金融防骗、合同维权、安全隐患调查、反直觉反诈调查类条目",
        "keywords": "Vox-style investigative collage, torn aged paper textures, archival document aesthetic, high contrast red accents, halftone printing dots, sharp journalistic details",
        "negative": "cartoonish, cute anime, pastel tones, 3d glossy, abstract sci-fi, blurry, watermark"
    },
    "13_pop": {
        "name": "利希滕斯坦波普艺术风",
        "description": "本戴点网格纹理、粗重黑色描边、经典美漫原色冲击、复古摩登张力",
        "suitable_for": "强烈反常识痛点、消费陷阱、人际冲突、情绪破防、高警醒度警示类条目",
        "keywords": "Roy Lichtenstein pop art, Ben-Day dots texture, bold black outlines, vintage comic book aesthetic, vibrant primary colors, graphic punchy composition",
        "negative": "soft watercolor, photorealistic, gloomy dark, 3d cgi, blurry, watermark"
    },
    "24_hopper": {
        "name": "霍珀美国现实主义风",
        "description": "强烈斜射几何光块与阴影、深思熟虑的构图、市井生活写实、克制孤独沉思感",
        "suitable_for": "都市打工人、独处与内心压力、人际交往、夜间作息、沉思人生类条目",
        "keywords": "Edward Hopper American realism style, dramatic geometric sunlight shadows, architectural clean planes, contemplative atmosphere, cinematic framing",
        "negative": "anime, cute cartoon, cyberpunk neon, hyper-saturated fantasy, chaotic details, watermark"
    },
    "17_ink": {
        "name": "新中式东方水墨风",
        "description": "东方水墨晕染留白、淡雅矿物设色、宁静从容、东方哲学意境",
        "suitable_for": "处世哲学、断舍离、心态调适、中式养生、静心修身类条目",
        "keywords": "modern Chinese ink wash painting, ethereal poetic composition, delicate sumi-e brush strokes, mineral color accents, elegant negative space, tranquil atmosphere",
        "negative": "loud neon, western comic, sharp geometric, cluttered, noisy 3d, watermark"
    },
    "14_pixel": {
        "name": "8-Bit 像素复古游戏风",
        "description": "精致复古像素点阵、街机闯关界面感、成就奖励图标、轻松趣味打怪升级感",
        "suitable_for": "习惯打卡、微小行动积累、目标达成、游戏化生活类条目",
        "keywords": "detailed 16-bit pixel art style, nostalgic retro game aesthetic, vibrant palette, clean isometric or side-view composition, charming playful details",
        "negative": "blurry, smooth photorealistic, soft watercolor, dark gloomy, watermark"
    }
}


def get_style_recipe(style_id: str) -> Dict[str, Any]:
    """Retrieve style recipe by ID with fallback to 25_ghibli."""
    return STYLE_RECIPES.get(style_id, STYLE_RECIPES["25_ghibli"])


def format_style_palette_menu() -> str:
    """Format the style recipe palette for LLM autonomous selection."""
    lines = []
    for sid, info in STYLE_RECIPES.items():
        lines.append(f"- 【{sid}】 {info['name']}: {info['description']}（适合：{info['suitable_for']}）")
    return "\n".join(lines)


def recommend_style_for_entry(chapter_index: int) -> str:
    """Recommend a style card based on chapter domain (default fallback)."""
    # 01(不要早死), 02(不要慢慢死), 13(紧急情况), 24(看病) -> Ghibli (温润生活守护)
    if chapter_index in (1, 2, 13, 24, 27, 34):
        return "25_ghibli"
    # 05(不要浪费钱), 08(别把自己搭进去), 09(法律红线), 11(技术红线), 12(创业), 15(买房租房) -> Vox (硬核调查与规则)
    elif chapter_index in (5, 8, 9, 11, 12, 15, 19):
        return "y2_vox"
    # 03(精力), 04(时间), 06(反面清单), 23(学技能) -> Kurzgesagt (清晰机制拆解)
    elif chapter_index in (3, 4, 6, 23, 26):
        return "y1_kurzgesagt"
    # 07(没钱), 10(恋爱结婚), 17(老人), 18(养孩子), 22(放松), 29(重大打击) -> Hopper (真实人情生活)
    elif chapter_index in (7, 10, 17, 18, 22, 29):
        return "24_hopper"
    else:
        return "25_ghibli"


def build_system_prompt(scene_count: int = 6) -> str:
    """System prompt embedding huashu-art-motion principles for muse-spark with Golden 6-scene rhythm."""
    return f"""你是一位顶级短视频总导演兼视觉分镜大师，精通开源动画项目 `huashu-art-motion` 的美学和解说语法。
你的任务是将提供的高性价比人生指南条目，转化为一份极具观赏性、节奏紧凑、绝无低质 AI 感的 28~32 秒大众科普短视频分镜脚本。

【绝对禁令与防 Agent 跑偏原则（最高优先级）】
1. **纯文本直接输出**：必须在当前会话中直接以纯文本 JSON 格式返回最终的分镜脚本结果，严禁输出任何思考过程、自我总结或无关前缀。
2. **严禁调用系统工具**：严禁调用任何后台系统工具、文件修改命令（edit file）、终端命令或沙盒脚本。
3. **严禁写入或更新记忆文件**：严禁创建、读取、编辑或追加任何 MEMORY.md、SOUL.md、USER.md 等文件；严禁更新规则库（包括 Chinese brief fidelity rule 等），严禁记录任何历史任务日志或规则演进记录。

【核心设计铁律】
1. **时长控制**：全片时长严格控制在 28 ~ 32 秒以内，非常适合抖音、小红书和视频号短视频。
2. **视频标题**：必须遵循格式 `"[章节名]之[小条目标题]"`。
3. **拒斥 AI Slop (防劣质 AI 原则)**：
   - 严禁任何蓝紫霓虹、深紫星空、炫光光球、数据流雨、无脸白模人偶、抽象悬浮几何体！
   - 全片必须锁定单一、统一的高级艺术画风和调和色板。
4. **镜头里必须有“具体的物与动作”**：
   - 拒绝空洞的符号。必须落在生活场景中具体的实体物件和物理动作上（如系扣安全带、旋紧燃气阀门、电子血压计数字跳动、纸质药盒、窗框限位锁）。
5. **黄金 {scene_count} 幕脉冲式叙事节奏 (Golden Multi-Scene Pulse Rhythm)**：
   - 全片必须严格规划 **{scene_count} 个紧凑分镜**（单镜时长约为 4.0~5.2 秒，拒绝长镜头静止死板，强化连续流动感）：
     * 第 1 镜 (0-4秒 痛点抓眼钩子)：生活场景具体物动作 + 抛出反直觉痛点。口播约 12~18 字。
     * 第 2 镜 (4-9秒 认知颠覆展开)：生活全貌展开，指出常见认知误区与真相。口播约 15~20 字。
     * 第 3 镜 (9-14秒 科学机理与隐形危害)：底层机理拆解，关键指标震撼对比。口播约 15~20 字。
     * 第 4 镜 (14-19秒 权威证据背书)：国家规章 / WHO / 权威文献数据标签展示。口播约 15~20 字。
     * 第 5 镜 (19-24秒 极低执行成本与示范)：具体的手部微动作或零成本实施步骤。口播约 15~20 字。
     * 第 6 镜 (24-29秒 金句定格落定)：明亮开阔的未来生活场景，核心行动金句收尾。口播约 10~15 字。
6. **核心浮现字 (Kinetic Typography)**：
   - 每一镜提炼 1 个简短有力的屏幕浮现词（2-8字），用于短视频大字冲击，例如“风险降50%”、“后排不系 60%致命”、“成本=0秒”。
7. **多模态视觉 Prompts 规范**：
   - `image_prompt`: 英文，面向生图模型。必须包含具体的物理实体、动作、构图（9:16 vertical ratio）、景别、光影质感，以及所选艺术画风的基石关键词！
   - `video_motion_prompt`: 英文，面向视频运镜控制。写明镜头运动（如 `Camera quick punch-in zoom`, `Smooth lateral tracking pan`, `Static grounded hold`）与微动细节。
8. **AI 生图内容安全与隐喻转换规范 (Safety Guardrails & Metaphorical Design)**：
   - 严禁在 `image_prompt` 中直接包含任何可能触发主流生图模型（Meta/Midjourney/SD）内容安全审查（Content Policy Violation）的敏感违规词：
     * **严禁烟草/吸烟物象**：严禁出现 `cigarette`, `smoking`, `tobacco`, `ashtray filled with ashes`, `stubbing out a cigarette` 等字眼。涉及戒烟、肺癌或健康防护时，必须转换为安全积极的隐喻意象（如：`an inverted empty clean ceramic ashtray on a rustic desk`, `clean smoke-free wooden table`, `fresh houseplant beside a glass of clear water`, `a medical lung health booklet with morning daylight`）。
     * **严禁创伤/血液/注射**：严禁出现具象血迹（`blood`）、开放性创口（`wound`）或针头穿刺人体皮肤（`needle piercing skin`）。必须转换为“温和医生健康问诊（warm doctor consultation）”、“医学显微细胞科普示意图（microscopic cellular diagram）”或“常规纸质体检报告单（health checkup report paper sheet）”。
     * **严禁危险管制物**：严禁枪械、管制刀具与非法违禁物，统一使用日常安全防护用具或生活实物作为具象载体。

【输出格式】
你必须直接输出严格的 JSON 对象（不要包裹 Markdown 代码块外的废话），其结构如下：
{{
  "entry_id": "01_001",
  "video_title": "不要早死之系安全带，前排后排都系",
  "target_duration_sec": 29,
  "art_style_id": "25_ghibli",
  "art_style_name": "吉卜力暖调手绘风",
  "art_style_reason": "条目涉及家庭乘车出行与生命安全，吉卜力暖调手绘能传递珍惜生活、温润治愈的守护感，避免生硬说教",
  "color_palette": ["#...", "#...", "#..."],
  "narration_text_full": "完整旁白文本...",
  "scenes": [
    {{
      "scene_index": 1,
      "time_range": "0.0-4.5",
      "duration_sec": 4.5,
      "narration_segment": "分镜口播文本（15字左右精炼短句）",
      "primary_subject": "具象主体（名词）",
      "visual_action": "主体在做什么动作及镜头事件（动词）",
      "kinetic_typography": {{
        "text": "浮现核心字",
        "style": "slam_in",
        "position": "center_high"
      }},
      "image_prompt": "Detailed English prompt for image generation, 9:16 vertical aspect ratio, including style keywords...",
      "video_motion_prompt": "Camera motion prompt in English..."
    }}
  ]
}}
"""


def build_user_prompt(entry: Dict[str, Any], style_mode: str = "auto", scene_count: int = 6) -> str:
    """Build user prompt with entry data, dynamic style selection and scene count."""
    chapter_index = entry.get("chapter_index", 1)
    chapter_title = entry.get("chapter_title", "")
    item_title = entry.get("title", "")
    entry_id = entry.get("id", "")
    cost_desc = entry.get("cost_desc", "不花钱")
    plain_text = entry.get("plain_text", "")
    benefit_desc = entry.get("benefit_desc", "")
    evidence_grade = entry.get("evidence_grade", "A")
    notes = entry.get("notes", "")

    chapter_recommended_id = recommend_style_for_entry(chapter_index)
    chapter_style_info = get_style_recipe(chapter_recommended_id)

    if style_mode == "auto":
        style_instruction = f"""【艺术风格决策指示（AI 总导演自主裁决）】:
你有权作为短视频总导演，根据条目的「核心要点」、「情绪基调」和「受众心理冲击」，从以下开源 `huashu-art-motion` 风格库中自主决策最契合的视觉画风：

{format_style_palette_menu()}

*(参考章节基准推荐: 【{chapter_recommended_id}】{chapter_style_info['name']}，你可沿用亦可自主选择更契合的画风)*

请在输出 JSON 中填入：
- `art_style_id`: 所选画风的代号 (必须是上述列表中的合法 ID)
- `art_style_name`: 画风中文名称
- `art_style_reason`: 1 句话选风理由（说明为什么此画风最能强化本条目的视觉传达）
并在每个分镜 scene 的 `image_prompt` 尾部，务必注入所选风格的关键词基石！"""

    elif style_mode == "chapter":
        style_instruction = f"""【艺术风格指定（遵循章节统一规范）】:
全片必须严格采用章节统一画风：
- 风格 ID: {chapter_recommended_id}
- 风格名称: {chapter_style_info['name']}
- 美学特征: {chapter_style_info['description']}
- 提示词基石: {chapter_style_info['keywords']}
在输出 JSON 中填入 art_style_id: "{chapter_recommended_id}", art_style_name: "{chapter_style_info['name']}", 并将提示词基石融入所有分镜的 image_prompt。"""

    else:
        chosen_style = get_style_recipe(style_mode)
        style_instruction = f"""【艺术风格强制指定】:
本条目强制指定画风为：
- 风格 ID: {style_mode}
- 风格名称: {chosen_style['name']}
- 美学特征: {chosen_style['description']}
- 提示词基石: {chosen_style['keywords']}
在输出 JSON 中填入 art_style_id: "{style_mode}", art_style_name: "{chosen_style['name']}", 并将提示词基石融入所有分镜的 image_prompt。"""

    return f"""请将以下条目转化为 28~32 秒高性价比人生指南短视频分镜脚本：

【条目编号】: {entry_id}
【章节】: {chapter_title}
【小条目标题】: {item_title}
【成本情况】: {cost_desc}
【说人话（核心要点）】: {plain_text}
【权威收益与数据】: {benefit_desc}
【证据等级】: {evidence_grade} 级
【补充备注】: {notes}

{style_instruction}

【分镜幕数要求】:
必须严格规划 **{scene_count} 幕分镜**（黄金六幕叙事曲线：痛点钩子 -> 认知颠覆 -> 机理危害 -> 权威证据 -> 极低成本 -> 行动金句），每镜口播控制在 15~20 字以内短句，节奏紧凑连续流动，拒绝长镜头静止！

【强制输出与抑制工具约束】:
请直接以纯文本 JSON 格式输出短视频分镜脚本，禁止调用任何系统工具、不要更新规则记忆文件（严禁编辑任何 MEMORY.md），直接回复最终内容。
标题统一命名为："{chapter_title}之{item_title}"。"""


