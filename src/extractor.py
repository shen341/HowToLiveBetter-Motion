"""Markdown parser and extractor for HowToLiveBetter book entries."""

import os
import re
from typing import Any, Dict, List, Optional, Tuple


def parse_chapter_filename(filename: str) -> Tuple[int, str]:
    """
    Parse filename like '01-不要早死.md' into (1, '不要早死').
    """
    base = os.path.basename(filename)
    if base.endswith(".md"):
        base = base[:-3]

    match = re.match(r"^(\d+)[-_](.*)$", base)
    if match:
        chapter_idx = int(match.group(1))
        chapter_title = match.group(2).strip()
        return chapter_idx, chapter_title

    return 0, base


def parse_cost_tags(text: str) -> Dict[str, str]:
    """
    Parse `<!-- 成本标签: 钱=0 时间=少 毅力=否 收益=大 口径=死亡率 -->`.
    """
    tags: Dict[str, str] = {
        "cost_money": None,
        "cost_time": None,
        "cost_willpower": None,
        "benefit_level": None,
        "benefit_metric": None,
    }

    match = re.search(r"<!--\s*成本标签:\s*(.*?)\s*-->", text)
    if not match:
        return tags

    content = match.group(1).strip()
    pairs = content.split()
    mapping = {
        "钱": "cost_money",
        "时间": "cost_time",
        "毅力": "cost_willpower",
        "收益": "benefit_level",
        "口径": "benefit_metric",
    }

    for pair in pairs:
        if "=" in pair:
            k, v = pair.split("=", 1)
            k = k.strip()
            v = v.strip()
            if k in mapping:
                tags[mapping[k]] = v

    return tags


def parse_bullets(text: str) -> Dict[str, str]:
    """
    Parse bullet points like `- 成本：...`, `- 说人话：...`, preserving multiline values.
    """
    bullets: Dict[str, str] = {
        "成本": "",
        "说人话": "",
        "收益": "",
        "证据等级": "",
        "来源": "",
        "备注": "",
    }

    # Split text into lines
    lines = text.split("\n")
    current_key: Optional[str] = None
    buffer: List[str] = []

    # Regex to identify a new bullet header: e.g. "- 成本：..." or "* 成本: ..."
    bullet_header_re = re.compile(r"^\s*[-\*]\s*([^：:\n]+)[：:]\s*(.*)$")

    for line in lines:
        # Ignore cost tag line
        if "成本标签:" in line and "<!--" in line:
            continue

        m = bullet_header_re.match(line)
        if m:
            key_raw = m.group(1).strip()
            val_first_line = m.group(2).strip()

            if current_key and current_key in bullets:
                bullets[current_key] = "\n".join(buffer).strip()

            current_key = key_raw
            buffer = [val_first_line] if val_first_line else []
        elif current_key is not None:
            # Continuation line
            buffer.append(line.strip())

    if current_key and current_key in bullets:
        bullets[current_key] = "\n".join(buffer).strip()

    return bullets


def extract_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse a single markdown file into a list of entry dicts.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Markdown file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    source_file = os.path.basename(file_path)
    chapter_index, chapter_title = parse_chapter_filename(source_file)

    # Regex matches each item section: ### {item_num}. {title}
    section_pattern = re.compile(
        r"^###\s+(\d+)\.\s+(.*?)\n(.*?)(?=(?:\n###\s+\d+\.)|\Z)",
        re.DOTALL | re.MULTILINE
    )

    matches = section_pattern.findall(content)
    entries: List[Dict[str, Any]] = []

    for item_num_str, title_raw, body_raw in matches:
        item_index = int(item_num_str)
        title = title_raw.strip()
        body = body_raw.strip()

        # Generate unique ID: e.g. 01_001
        entry_id = f"{chapter_index:02d}_{item_index:03d}"

        cost_tags = parse_cost_tags(body)
        bullets = parse_bullets(body)

        evidence_grade = bullets.get("证据等级", "").strip()
        # Clean evidence grade (take first letter if it's A/B/C)
        if evidence_grade and evidence_grade[0].upper() in ("A", "B", "C"):
            evidence_grade = evidence_grade[0].upper()

        entry = {
            "id": entry_id,
            "source_file": source_file,
            "chapter_index": chapter_index,
            "chapter_title": chapter_title,
            "item_index": item_index,
            "title": title,
            "cost_money": cost_tags["cost_money"],
            "cost_time": cost_tags["cost_time"],
            "cost_willpower": cost_tags["cost_willpower"],
            "benefit_level": cost_tags["benefit_level"],
            "benefit_metric": cost_tags["benefit_metric"],
            "cost_desc": bullets.get("成本", ""),
            "plain_text": bullets.get("说人话", ""),
            "benefit_desc": bullets.get("收益", ""),
            "evidence_grade": evidence_grade,
            "source_citations": bullets.get("来源", ""),
            "notes": bullets.get("备注", ""),
            "raw_content": f"### {item_index}. {title}\n{body}",
        }
        entries.append(entry)

    return entries


def extract_all(book_dir: str) -> List[Dict[str, Any]]:
    """
    Extract all entries from all markdown files in book directory.
    """
    if not os.path.exists(book_dir):
        raise FileNotFoundError(f"Book directory not found: {book_dir}")

    files = [f for f in os.listdir(book_dir) if f.endswith(".md") and not f.startswith(".")]

    def sort_key(name: str) -> int:
        idx, _ = parse_chapter_filename(name)
        return idx

    files.sort(key=sort_key)

    all_entries: List[Dict[str, Any]] = []
    for f in files:
        file_path = os.path.join(book_dir, f)
        entries = extract_file(file_path)
        all_entries.extend(entries)

    return all_entries
