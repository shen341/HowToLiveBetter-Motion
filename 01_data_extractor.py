"""01_data_extractor.py - Data extraction and state initialization pipeline for HowToLiveBetter-Motion.

Usage:
    python 01_data_extractor.py
    python 01_data_extractor.py --chapter 1
    python 01_data_extractor.py --force
"""

import argparse
import os
import subprocess
import sys
import io

# Ensure UTF-8 output encoding on Windows consoles
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from src.db import (
    DEFAULT_DB_PATH,
    DEFAULT_PROGRESS_PATH,
    export_progress_json,
    get_connection,
    get_statistics,
    init_db,
    upsert_entry,
)
from src.extractor import extract_all, extract_file, parse_chapter_filename

DEFAULT_REPO_URL = "https://github.com/eternity4719/HowToLiveBetter.git"
DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "HowToLiveBetter")


def ensure_data_repo(repo_url: str, data_dir: str, do_pull: bool = False) -> str:
    """Ensure that HowToLiveBetter repository is present locally."""
    book_dir = os.path.join(data_dir, "book")

    if not os.path.exists(data_dir):
        print(f"📦 Local repository not found. Cloning from {repo_url}...")
        os.makedirs(os.path.dirname(data_dir), exist_ok=True)
        cmd = ["git", "clone", repo_url, data_dir, "--depth", "1"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"❌ Failed to clone repository: {res.stderr}")
            sys.exit(1)
        print("✅ Clone completed successfully.")
    elif do_pull:
        print(f"🔄 Pulling latest updates in {data_dir}...")
        subprocess.run(["git", "-C", data_dir, "pull"], capture_output=True, text=True)

    if not os.path.exists(book_dir):
        print(f"❌ Error: 'book' directory does not exist in {data_dir}!")
        sys.exit(1)

    return book_dir


def main():
    parser = argparse.ArgumentParser(description="Extract HowToLiveBetter entries and initialize pipeline state.")
    parser.add_argument("--repo-url", default=DEFAULT_REPO_URL, help="Git repository URL")
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR, help="Local directory for HowToLiveBetter")
    parser.add_argument("--pull", action="store_true", help="Run git pull before extracting")
    parser.add_argument("--chapter", type=int, default=None, help="Extract only specific chapter index (e.g. 1)")
    parser.add_argument("--force", action="store_true", help="Force reset existing workflow status to 'Pending'")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Path to SQLite database")
    parser.add_argument("--progress-path", default=DEFAULT_PROGRESS_PATH, help="Path to progress.json")
    args = parser.parse_args()

    print("=" * 65)
    print("🚀 HowToLiveBetter-Motion: 数据抓取与状态管理初始化")
    print("=" * 65)

    # 1. 检查或拉取数据源
    book_dir = ensure_data_repo(args.repo_url, args.data_dir, args.pull)
    print(f"📂 数据源目录: {book_dir}")

    # 2. 初始化数据库
    conn = get_connection(args.db_path)
    init_db(conn)
    print(f"🗄️ SQLite 数据库初始化就绪: {args.db_path}")

    # 3. 抽取与解析 Markdown 条目
    if args.chapter is not None:
        target_file = None
        for fn in os.listdir(book_dir):
            if fn.endswith(".md"):
                idx, _ = parse_chapter_filename(fn)
                if idx == args.chapter:
                    target_file = os.path.join(book_dir, fn)
                    break
        if not target_file:
            print(f"❌ 未找到第 {args.chapter} 章对应的 .md 文件！")
            sys.exit(1)
        print(f"🔍 正在解析指定章节: {os.path.basename(target_file)}")
        entries = extract_file(target_file)
    else:
        print("🔍 正在解析全书章节 (book/*.md)...")
        entries = extract_all(book_dir)

    print(f"📊 本次抽取到条目数: {len(entries)} 条")

    # 4. 持久化至 SQLite 数据库
    inserted_cnt = 0
    updated_cnt = 0
    for item in entries:
        action = upsert_entry(conn, item, force_reset_status=args.force)
        if action == "inserted":
            inserted_cnt += 1
        else:
            updated_cnt += 1

    print(f"💾 持久化同步完成: 新增入库 {inserted_cnt} 条 | 更新刷新 {updated_cnt} 条")

    # 5. 导出 progress.json 镜像快照
    snapshot = export_progress_json(conn, args.progress_path)
    print(f"📑 进度快照同步导出: {args.progress_path}")

    # 6. 输出统计信息
    stats = get_statistics(conn)
    print("-" * 65)
    print(f"📈 状态统计总览 (Total: {stats['total_entries']} 条):")
    for st, count in stats["status_summary"].items():
        print(f"   • {st:<18}: {count:>5} 条")
    print("-" * 65)

    # 抽取 2 条展示样本验证
    sample_entries = entries[:2]
    print("✨ 条目解析样本预览:")
    for s in sample_entries:
        print(f"   [{s['id']}] 《{s['chapter_title']}》 - {s['title']}")
        print(f"       成本: {s['cost_desc'][:40]}...")
        print(f"       说人话: {s['plain_text'][:40]}...")
        print(f"       收益标签: {s['benefit_level']} | 证据等级: {s['evidence_grade']}")
        print()

    print("=" * 65)
    print("🎉 数据抽取与状态管理初始化顺利完成！")
    print("=" * 65)


if __name__ == "__main__":
    main()
