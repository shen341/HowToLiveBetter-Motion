"""Local SVG Icon Registry and Semantic Matcher for Whiteboard Explainer Animation."""

import os
import re
from typing import Dict, List, Optional, Tuple

from src.whiteboard.svg_parser import parse_svg_content, scale_and_center_strokes

# Built-in clean minimalist line-art SVGs (optimized for drawing pen reveals)
BUILTIN_SVGS: Dict[str, str] = {
    # 1. Automobile / Car: Elegant side-profile sedan with windshield, roof arc, wheels, and lights
    "automobile": """<svg viewBox="0 0 100 60" xmlns="http://www.w3.org/2000/svg">
        <!-- Main Car Body & Cabin Outline -->
        <path d="M 5,42 L 18,42 C 18,36 28,36 28,42 L 72,42 C 72,36 82,36 82,42 L 95,42 C 97,42 98,39 96,36 L 88,27 C 85,25 81,25 78,25 L 68,13 C 66,10 61,10 56,10 L 32,10 C 26,10 22,14 19,20 L 10,26 C 6,28 4,32 5,36 Z" />
        <!-- Front & Rear Windows Separator -->
        <path d="M 33,13 L 23,24 L 50,24 L 50,13 Z" />
        <path d="M 53,13 L 53,24 L 75,24 L 66,13 Z" />
        <!-- Front Wheel (Outer & Rim) -->
        <circle cx="23" cy="42" r="6" />
        <circle cx="23" cy="42" r="2.5" />
        <!-- Rear Wheel (Outer & Rim) -->
        <circle cx="77" cy="42" r="6" />
        <circle cx="77" cy="42" r="2.5" />
        <!-- Headlight & Tail light accents -->
        <line x1="93" y1="35" x2="97" y2="35" />
        <line x1="4" y1="34" x2="7" y2="34" />
        <!-- Door handle & waistline -->
        <line x1="45" y1="28" x2="52" y2="28" />
    </svg>""",

    # 2. Seatbelt: Cross diagonal strap with secure latch and click buckle
    "seatbelt": """<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
        <!-- Diagonal Shoulder Strap -->
        <path d="M 10,12 L 68,70 L 62,76 L 4,18 Z" />
        <!-- Buckle Outer Shell -->
        <path d="M 32,32 L 48,16 C 51,13 56,13 59,16 L 64,21 C 67,24 67,29 64,32 L 48,48 C 45,51 40,51 37,48 Z" />
        <!-- Metal Tongue Insertion -->
        <path d="M 28,36 L 36,44 L 32,48 L 24,40 Z" />
        <!-- Red Release Button -->
        <rect x="44" y="24" width="10" height="6" />
        <!-- Safety Click Sparks -->
        <line x1="22" y1="26" x2="16" y2="22" />
        <line x1="26" y1="22" x2="24" y2="15" />
        <line x1="38" y1="18" x2="38" y2="11" />
    </svg>""",

    # 3. Crash Warning Triangle
    "crash_warning": """<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
        <!-- Outer Warning Triangle -->
        <path d="M 40,8 L 74,68 C 76,71 74,75 70,75 L 10,75 C 6,75 4,71 6,68 Z" />
        <!-- Inner Border Triangle -->
        <path d="M 40,18 L 66,65 L 14,65 Z" />
        <!-- Exclamation Mark Bar -->
        <line x1="40" y1="32" x2="40" y2="48" />
        <!-- Exclamation Mark Dot -->
        <circle cx="40" cy="56" r="2.5" />
    </svg>""",

    # 4. Shield Badge (Authority & Grade Certification)
    "shield_badge": """<svg viewBox="0 0 80 90" xmlns="http://www.w3.org/2000/svg">
        <!-- Outer Shield -->
        <path d="M 40,6 C 58,6 72,12 72,12 C 72,50 56,76 40,84 C 24,76 8,50 8,12 C 8,12 22,6 40,6 Z" />
        <!-- Inner Shield Ribbon -->
        <path d="M 40,14 C 54,14 64,18 64,18 C 64,48 50,70 40,76 C 30,70 16,48 16,18 C 16,18 26,14 40,14 Z" />
        <!-- Star / Grade Symbol in Center -->
        <path d="M 40,28 L 43,38 L 53,38 L 45,44 L 48,54 L 40,48 L 32,54 L 35,44 L 27,38 L 37,38 Z" />
    </svg>""",

    # 5. Balance Scale (Cost vs Benefit)
    "balance_scale": """<svg viewBox="0 0 90 70" xmlns="http://www.w3.org/2000/svg">
        <!-- Base Stand -->
        <line x1="45" y1="12" x2="45" y2="58" />
        <path d="M 32,64 L 45,58 L 58,64 Z" />
        <!-- Top Beam (Slightly tilted up to right) -->
        <line x1="12" y1="22" x2="78" y2="14" />
        <!-- Left Pan Strings & Plate (Cost) -->
        <line x1="12" y1="22" x2="6" y2="42" />
        <line x1="12" y1="22" x2="20" y2="42" />
        <path d="M 4,42 C 4,48 22,48 22,42 Z" />
        <!-- Right Pan Strings & Plate (Benefit, heavier/bigger) -->
        <line x1="78" y1="14" x2="70" y2="38" />
        <line x1="78" y1="14" x2="86" y2="38" />
        <path d="M 66,38 C 66,48 90,48 90,38 Z" />
    </svg>""",

    # 6. Checkmark Circle (Decisive Action)
    "checkmark_circle": """<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
        <!-- Outer Circle -->
        <circle cx="40" cy="40" r="32" />
        <!-- Inner Bold Checkmark -->
        <path d="M 24,40 L 35,52 L 56,26" />
    </svg>""",

    # 7. Clock / Stopwatch (Minimal Time & Seconds)
    "clock_time": """<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
        <!-- Outer Clock Dial -->
        <circle cx="40" cy="42" r="30" />
        <!-- Top Button -->
        <line x1="40" y1="6" x2="40" y2="12" />
        <line x1="34" y1="6" x2="46" y2="6" />
        <!-- Hour Hand & Minute Hand pointing to ~2s / quick time -->
        <line x1="40" y1="42" x2="40" y2="24" />
        <line x1="40" y1="42" x2="56" y2="34" />
        <!-- Small center pin -->
        <circle cx="40" cy="42" r="2" />
    </svg>""",

    # 8. Heart Life Pulse (Health & Safety)
    "heart_pulse": """<svg viewBox="0 0 80 70" xmlns="http://www.w3.org/2000/svg">
        <!-- Heart Outline -->
        <path d="M 40,62 C 34,56 12,40 12,24 C 12,14 20,8 30,8 C 36,8 40,12 40,12 C 40,12 44,8 50,8 C 60,8 68,14 68,24 C 68,40 46,56 40,62 Z" />
        <!-- Pulse EKG Line through Center -->
        <polyline points="18,34 28,34 33,20 38,48 43,26 48,34 62,34" />
    </svg>""",
}

# Semantic dictionary mapping domain keywords to appropriate icon IDs
SEMANTIC_KEYWORD_MAP: Dict[str, List[str]] = {
    "automobile": [
        "汽车", "车", "车祸", "轿车", "卡车", "撞车", "驾驶", "车辆", "行车", "死在车里", "安全带", "乘车", "副驾驶",
        "car", "automobile", "drive", "vehicle", "crash", "truck"
    ],
    "seatbelt": [
        "安全带", "卡扣", "系带", "插销", "扣紧", "前排", "后排",
        "seatbelt", "buckle"
    ],
    "crash_warning": [
        "误区", "盲区", "陷阱", "警示", "危险", "事故", "风险", "漏洞", "注意",
        "warning", "caution", "alert", "danger", "pitfall"
    ],
    "shield_badge": [
        "证据", "权威", "等级", "认证", "标准", "who", "nhtsa", "规范", "徽章", "硬核",
        "shield", "badge", "grade", "evidence", "certified"
    ],
    "balance_scale": [
        "天平", "对比", "性价比", "投入", "产出", "收益", "代价",
        "scale", "balance", "cost", "benefit"
    ],
    "clock_time": [
        "成本", "时间", "秒", "时钟", "快速", "2秒", "两秒", "花费", "平时",
        "clock", "time", "second", "fast"
    ],
    "checkmark_circle": [
        "行动", "唯一解", "对勾", "完成", "立即", "开始", "执行", "落实",
        "check", "action", "done", "start"
    ],
    "heart_pulse": [
        "生命", "健康", "心跳", "存活", "救命", "保命", "猝死",
        "heart", "life", "health", "pulse"
    ],
    # 9. Abdominal Feeling (生病、肚子疼、不舒服)
    "abdominal_feeling": [
        "生病", "肚子疼", "不舒服", "胃痛", "腹痛", "疼痛", "难受", "身体不适", "呕吐", "腹泻", "肠胃"
    ],
    # 10. Bank Card (银行卡、信用卡、卡片)
    "bank-card": [
        "银行卡", "信用卡", "卡片", "借记卡", "刷卡", "转账", "消费", "开销", "资金", "买单"
    ],
    # 11. Crying Feeling (哭泣、哭、悲伤)
    "crying_feeling": [
        "哭泣", "哭", "悲伤", "难过", "流泪", "痛苦", "沮丧", "伤心", "崩溃", "抑郁"
    ],
    # 12. Gambling (赌博、打牌、骰子)
    "gambling": [
        "赌博", "打牌", "骰子", "下注", "博弈", "押注", "轮盘", "抽奖", "筹码", "牌局"
    ],
    # 13. Happy Feeling (开心、胜利、优秀)
    "happy_feeling": [
        "开心", "胜利", "优秀", "快乐", "喜悦", "成功", "庆祝", "积极", "点赞", "好心情"
    ],
    # 14. Hospital (医院、卫生机构)
    "hospital": [
        "医院", "卫生机构", "看病", "诊所", "就医", "急救", "门诊", "医生", "医护", "医疗机构"
    ],
    # 15. AIDS (艾滋病)
    "aids": [
        "艾滋病", "艾滋", "hiv", "获得性免疫缺陷", "阻断药", "血液传染", "免疫缺陷"
    ],
    # 16. Drug (药物、疫苗、药品)
    "drug": [
        "药物", "疫苗", "药品", "吃药", "抗生素", "止痛药", "处方药", "胶囊", "西药", "药丸", "服药"
    ],
    # 17. Help (救助、帮助)
    "help": [
        "救助", "帮助", "援助", "扶持", "求助", "协助", "援手", "关照", "支持", "互助"
    ],
    # 18. Medical Examination (医疗检查、病情)
    "medical-examination": [
        "医疗检查", "体检", "病情", "检查", "问诊", "诊断", "化验", "查体", "筛查", "病历"
    ],
    # 19. Motor (摩托车、电动车)
    "motor": [
        "摩托车", "电动车", "机车", "电瓶车", "骑车", "二轮车", "两轮", "骑行", "头盔"
    ],
    # 20. Metal Bar (金属)
    "metal-bar": [
        "金属", "铁", "钢", "铅", "重金属", "合金", "金属栏杆", "金属棒"
    ],
    # 21. Radiation Alt (放射源)
    "radiation-alt": [
        "放射源", "辐射", "核辐射", "放射线", "射线", "电离辐射", "放射性", "防辐射"
    ],
    # 22. Female (女性、女人)
    "female": [
        "女性", "女人", "女士", "妇女", "女孩", "母婴", "产妇", "女"
    ],
    # 23. Male (男性、男人)
    "male": [
        "男性", "男人", "男士", "男子", "男孩", "男"
    ],
    # 24. Children (儿童、小孩、少儿、幼儿)
    "children": [
        "儿童", "小孩", "少儿", "幼儿", "孩子", "婴儿", "青少年", "童年", "学龄前"
    ],
    # 25. Dead (死亡、死亡率)
    "dead": [
        "死亡", "死亡率", "丧命", "致命", "去世", "遇难", "致死", "身亡", "致死率", "死因"
    ],
    # 26. Fall Down (摔倒、骨折)
    "fall-down": [
        "摔倒", "骨折", "跌倒", "滑倒", "骨裂", "扭伤", "摔伤", "跌伤", "外伤"
    ],
}


class SVGIconLibrary:
    """Manager for retrieving, persisting, and scaling whiteboard vector graphics."""

    def __init__(self, asset_dir: Optional[str] = None):
        self.asset_dir = asset_dir or os.path.join("assets", "whiteboard", "svg")
        os.makedirs(self.asset_dir, exist_ok=True)
        self._ensure_builtin_svg_files()

    def _ensure_builtin_svg_files(self):
        """Materialize built-in SVGs as physical files in assets/whiteboard/svg/ for user editing."""
        for name, content in BUILTIN_SVGS.items():
            file_path = os.path.join(self.asset_dir, f"{name}.svg")
            if not os.path.exists(file_path):
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content.strip())
                except Exception:
                    pass

    def get_svg_content(self, icon_name: str) -> Optional[str]:
        """Fetch SVG XML content from disk or built-in registry with flexible naming."""
        clean_name = icon_name.lower().strip()
        candidates = [
            clean_name,
            clean_name.replace("_", "-"),
            clean_name.replace("-", "_")
        ]
        for name in candidates:
            file_path = os.path.join(self.asset_dir, f"{name}.svg")
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception:
                    pass
            if name in BUILTIN_SVGS:
                return BUILTIN_SVGS[name]
        return None

    def match_icon(self, text: str, preferred_priority: Optional[List[str]] = None) -> Optional[str]:
        """
        Analyze Chinese/English text semantically to match the most suitable vector icon.
        
        Args:
            text: Context string (scene subject, narration, keywords).
            preferred_priority: Optional list of icon names to prioritize.
        """
        if not text:
            return None

        clean_text = text.lower()

        # Check priorities first
        if preferred_priority:
            for icon_id in preferred_priority:
                keywords = SEMANTIC_KEYWORD_MAP.get(icon_id, [])
                if any(kw.lower() in clean_text for kw in keywords):
                    return icon_id

        # General matching with specificity scoring
        best_icon: Optional[str] = None
        best_score = 0

        for icon_id, keywords in SEMANTIC_KEYWORD_MAP.items():
            score = 0
            for kw in keywords:
                if kw.lower() in clean_text:
                    # Longer keyword matches get higher specificity weight
                    score += len(kw)
            if score > best_score:
                best_score = score
                best_icon = icon_id

        return best_icon

    def get_icon_strokes(
        self,
        icon_name_or_keyword: str,
        center_x: float = 540.0,
        center_y: float = 850.0,
        target_width: float = 380.0,
        target_height: Optional[float] = None,
    ) -> Optional[List[List[Tuple[float, float]]]]:
        """
        Retrieve and scale vector stroke polyline paths for an icon by name or keyword.
        """
        icon_name = icon_name_or_keyword.lower().strip()

        # 1. Direct file or built-in lookup first
        svg_content = self.get_svg_content(icon_name)
        if not svg_content:
            # 2. Try semantic matching if not an explicit filename/icon_id
            matched = self.match_icon(icon_name_or_keyword)
            if matched:
                icon_name = matched
                svg_content = self.get_svg_content(icon_name)
            else:
                return None

        if not svg_content:
            return None

        raw_strokes = parse_svg_content(svg_content)
        if not raw_strokes:
            return None

        return scale_and_center_strokes(
            strokes=raw_strokes,
            center_x=center_x,
            center_y=center_y,
            target_width=target_width,
            target_height=target_height,
        )
