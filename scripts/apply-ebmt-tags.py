#!/usr/bin/env python3
"""
把「每題對應 EBMT Handbook 章節」的分類寫進 question_tags,讓「相似題目」
(worker/routes/questions.ts 的 tag-overlap 那一路)與年度頁的 tag 篩選有東西可用。

輸入:
  docs/hsct-ebmt-chapter-map.json   每題 {id, primary, secondary[]}(章號 1..94;
                                    2026-10-08 由 7 個 subagent 逐年分類,手動校正過)
  scripts/ebmt-chapter-tags.json    章號 → 短 tag("GVHD 預防"、"急性 GVHD"、"CAR-T"…;使用者要的是一眼看得懂的短字)

用法:
  python3 scripts/apply-ebmt-tags.py --local
  python3 scripts/apply-ebmt-tags.py --remote
  python3 scripts/apply-ebmt-tags.py --dry-run     # 只印 SQL 統計

冪等:INSERT OR IGNORE(PK 是 (question_id, tag)),重跑不會重複;先 DELETE 掉舊的
自己(created_by)寫過的 tag 再寫,所以改分類重跑會收斂到新的那一份。其他 tag(共同/複選/AI暫定)
一個都不碰。
"""
import argparse
import json
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
with (ROOT / "config.toml").open("rb") as f:
    CFG = tomllib.load(f)
D1_DB = CFG["project"]["d1_db"]
AUTHOR = f"ebmt-tagger@{CFG['project']['slug']}"


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--local", action="store_true")
    g.add_argument("--remote", action="store_true")
    g.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    chapters = {c["n"]: c["tag"] for c in json.loads((ROOT / "scripts" / "ebmt-chapter-tags.json").read_text("utf-8"))}
    rows = json.loads((ROOT / "docs" / "hsct-ebmt-chapter-map.json").read_text("utf-8"))["questions"]

    now = int(time.time() * 1000)
    # 只清自己寫過的那批(created_by),不靠 tag 字樣 —— 短名改過一次,字樣靠不住。
    stmts = [f"DELETE FROM question_tags WHERE created_by = '{AUTHOR}';"]
    n_tags = 0
    for r in rows:
        for ch in [r["primary"], *r.get("secondary", [])]:
            tag = chapters[ch]
            stmts.append(
                "INSERT OR IGNORE INTO question_tags (question_id, tag, created_by, created_at) "
                f"VALUES ('{r['id']}', '{tag.replace(chr(39), chr(39) * 2)}', '{AUTHOR}', {now});"
            )
            n_tags += 1
    print(f"{len(rows)} questions → {n_tags} chapter tags", file=sys.stderr)
    if args.dry_run:
        print("\n".join(stmts[:4]))
        return

    flag = "--local" if args.local else "--remote"
    with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False, encoding="utf-8") as tmp:
        tmp.write("\n".join(stmts) + "\n")
        path = tmp.name
    subprocess.run(["wrangler", "d1", "execute", D1_DB, flag, "--file", path], check=True, stdout=subprocess.DEVNULL)
    print(f"✅ applied ({flag})", file=sys.stderr)


if __name__ == "__main__":
    main()
