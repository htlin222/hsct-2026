#!/usr/bin/env python3
"""
血液及骨髓移植專科醫師筆試試題 PDF(108–114)→ 題庫 CSV。

用法:  python3 -I parse_hsct.py <pdf> --year 108 --out <dir>

版面重點(都是看座標/顏色推出來的,不靠「行尾剛好是一個大寫字母」):
- 108 / 110:答案是**紅色粗體** `(X)` span,位置可在題號同一列,也可在下一列的左欄。
- 109:答案是題號後的單一粗體字母,但多半跟題幹黏在同一個 span → 用文字規則。
- 111–113:答案在最右欄(x≈537)的單字母 span,依同頁 y 座標對回題號列。
- 114:文字層**沒有任何答案**(沒有白字、沒有右欄字母)→ 全部留空待人工。
- K-type(複選):對照表三種寫法 —— 108 卷首共用表 + 個別 `Answers: (A) 1+2 …`,
  109/111/112 `A. (1)(2)(3)… are correct`,110 `(A) 123 (B) 13 …`,
  113/114 `(1)(2)(3) Are Correct, Please Choose (A)`。
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field

import fitz

RED = 0xFF0000
DEFAULT_K_MAP = {"A": "(1)(2)(3)", "B": "(1)(3)", "C": "(2)(4)", "D": "(4)", "E": "(1)(2)(3)(4)"}

RE_QSTART = re.compile(r"^(\d{1,3})(?!\d)\s*[.．]?\s*(.*)$")
RE_GONG = re.compile(r"^(?:\(\s*共\s*\)|共同)\s*")
RE_ANS_PAREN = re.compile(r"^\(\s*([A-E])\s*\)$")
RE_ANS_BARE_109 = re.compile(r"^([A-E])\s+(\S.*)$")
RE_OPTION = re.compile(r"^\(\s*([A-E])\s*\)\s*(.*)$")
RE_OPTION_DOT = re.compile(r"^([A-E])\s*[.．]\s+(.*)$")
RE_STMT = re.compile(r"^\(\s*(\d)\s*\)\s*(.*)$")
RE_ANSWER_HDR = re.compile(r"^Answers?\s*[:：]\s*(.*)$", re.I)
RE_MAP_DOT = re.compile(r"^([A-E])\s*[.．]\s*(.*)$")
RE_MAP_CHOOSE = re.compile(r"^(.*?)\s*,?\s*(?:(?:Are|Is)\s+Correct\s*,?\s*)?Please\s+Choose\s*\(\s*([A-E])\s*\)\s*$", re.I)
RE_MAP_INLINE = re.compile(r"\(\s*([A-E])\s*\)\s*([\d+ ,]+?)(?=\s*\(|$)")
RE_REF = re.compile(r"^(?:\(?\s*(?:Ref|Reference|Source)\s*[:：]|來源出處|\(?\s*Thomas'|ESH-EBMT Handbook)", re.I)
RE_SECTION = re.compile(r"(單選題|複選題)")
RE_TITLE = re.compile(r"年血液及骨髓移植專科醫師筆試試題")
NOISE_CHARS = set("題號目答案")


# Symbol 字型的 PUA 字元 → 希臘字母等(112 Q2「αβ TCR」、108 Q47「interferon-α」、110 Q36「α- and β-chain」)
_SYMBOL = {c: g for c, g in zip("abgdezhqiklmnxoprstufcyw", "αβγδεζηθικλμνξοπρστυφχψω")}
_SYMBOL.update({c.upper(): g.upper() for c, g in _SYMBOL.items()})
_SYMBOL.update({"\xa3": "≤", "\xb3": "≥", "\xb1": "±", "\xb0": "°", "\xd7": "×", "\xae": "→", "\xb4": "×", "\xa5": "∞"})


def symbol_decode(text: str, font: str) -> str:
    if "Symbol" not in font:
        return text
    out = []
    for ch in text:
        o = ord(ch)
        if 0xF000 <= o <= 0xF0FF:
            out.append(_SYMBOL.get(chr(o - 0xF000), ch))
        else:
            out.append(ch)
    return "".join(out)


@dataclass
class Span:
    text: str
    x0: float
    x1: float
    y0: float
    color: int
    font: str


@dataclass
class Row:
    page: int
    y0: float
    x0: float
    spans: list[Span]
    text: str = ""

    def build(self, drop: set[int]) -> None:
        parts = [s.text for s in self.spans if id(s) not in drop]
        t = "".join(parts).replace("\xa0", " ").replace("​", "")
        self.text = re.sub(r"[ \t]+", " ", t).strip()


def is_cjk(ch: str) -> bool:
    return "一" <= ch <= "鿿" or "　" <= ch <= "〿" or "＀" <= ch <= "￯"


def join_text(a: str, b: str) -> str:
    if not a:
        return b
    if not b:
        return a
    if is_cjk(a[-1]) and is_cjk(b[0]):
        return a + b
    if a[-1] in "-‐‑":
        return a + b
    return a + " " + b


def load_rows(path: str) -> tuple[list[Row], int]:
    doc = fitz.open(path)
    lines: list[tuple[int, float, float, list[Span]]] = []
    for pno, page in enumerate(doc):
        # 不帶 TEXT_MEDIABOX_CLIP:113 有幾行超出 mediabox 右緣,預設旗標會把尾巴的字整個丟掉
        flags = fitz.TEXT_PRESERVE_LIGATURES | fitz.TEXT_PRESERVE_WHITESPACE
        for block in page.get_text("dict", flags=flags)["blocks"]:
            for ln in block.get("lines", []):
                # 只有空白的 span 也要留:字與字之間的空格常常就是一個獨立的「' '」span,
                # 丟掉它會把「adaptive immune」黏成「adaptiveimmune」。
                spans = [
                    Span(symbol_decode(s["text"], s.get("font", "")), s["bbox"][0], s["bbox"][2], s["bbox"][1],
                         s.get("color", 0), s.get("font", ""))
                    for s in ln["spans"] if s["text"]
                ]
                solid = [s for s in spans if s.text.strip()]
                if solid:
                    lines.append((pno, ln["bbox"][1], min(s.x0 for s in solid), spans))
    npages = len(doc)
    doc.close()
    lines.sort(key=lambda t: (t[0], t[1], t[2]))
    # 同頁、y 相差 ≤5pt 的 line 合成一列(左欄答案 / 右欄答案跟題幹在同一視覺列,但是不同 block)
    groups: list[tuple[int, float, float, list[list[Span]]]] = []
    for pno, y0, x0, spans in lines:
        if groups and groups[-1][0] == pno and abs(y0 - groups[-1][1]) <= 5:
            groups[-1][3].append(spans)
            groups[-1] = (pno, groups[-1][1], min(groups[-1][2], x0), groups[-1][3])
        else:
            groups.append((pno, y0, x0, [spans]))
    rows: list[Row] = []
    for pno, y0, x0, gs in groups:
        gs.sort(key=lambda g: min(s.x0 for s in g if s.text.strip()))
        rows.append(Row(pno, y0, x0, [s for g in gs for s in g]))
    return rows, npages


def answer_letter(text: str) -> str | None:
    m = re.fullmatch(r"[（(]?\s*([A-E])\s*[）)]?", unicodedata.normalize("NFKC", text).strip())
    return m.group(1) if m else None


@dataclass
class Q:
    num: int
    multi: bool
    gong: bool = False
    answer: str = ""
    answer_src: str = ""
    stem_parts: list[str] = field(default_factory=list)
    options: dict[str, str] = field(default_factory=dict)
    opt_order: list[str] = field(default_factory=list)
    stmts: list[tuple[str, str]] = field(default_factory=list)
    kmap: dict[str, str] = field(default_factory=dict)
    ref: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    raw: list[str] = field(default_factory=list)


def normalize_combo(body: str) -> str:
    """'1+2+ 3' / '123' / '(1),(3)' / '(1)(2)(3)……..Are Correct' → '(1)(2)(3)'。認不得就原樣回傳。"""
    b = re.sub(r"(?:Are|Is|are|is)\s+[Cc]orrect.*$", "", body).strip()
    b = b.rstrip(" .…,;")
    if not b:
        return ""
    if re.fullmatch(r"[\s()\d+,.…]*", b):
        digits = re.findall(r"\d", b)
        if digits:
            return "".join(f"({d})" for d in digits)
    return b


def parse(path: str, year: int) -> list[Q]:
    rows, _ = load_rows(path)
    drop: set[int] = set()

    # ---- 111–113:右欄答案 span 先抽出來 ----
    col_answers: list[tuple[int, float, str]] = []
    if 111 <= year <= 114:
        cand = [(r, s) for r in rows for s in r.spans if s.x0 > 480 and answer_letter(s.text)]
        # 答案欄 x 不寫死:單選區與複選區的欄位 x 略有不同(111/112 差約 5pt),
        # 所以把右側單字母 span 依 x 分群,只收「成員 ≥5」的群,孤立的字母(題幹溢出的尾巴)不算。
        xs = sorted(s.x0 for _, s in cand)
        clusters: list[list[float]] = []
        for x in xs:
            if clusters and x - clusters[-1][-1] <= 3:
                clusters[-1].append(x)
            else:
                clusters.append([x])
        good = [c for c in clusters if len(c) >= 5]
        for r, s in cand:
            if any(c[0] - 0.5 <= s.x0 <= c[-1] + 0.5 for c in good):
                col_answers.append((r.page, s.y0, answer_letter(s.text)))  # type: ignore[arg-type]
                drop.add(id(s))
    # ---- 108/110:紅色 (X) span ----
    red_answers: dict[int, str] = {}  # id(row) -> letter
    if year in (108, 110):
        for r in rows:
            for s in r.spans:
                if s.color == RED and answer_letter(s.text):
                    red_answers[id(r)] = answer_letter(s.text)  # type: ignore[assignment]
                    drop.add(id(s))
    for r in rows:
        r.build(drop)
    # 只剩紅色答案的列(110 Q42 的「(A)」自成一列)文字會是空的,但不能丟
    rows = [r for r in rows if r.text or id(r) in red_answers]

    # ---- 題號欄位置 ----
    numx = [r.x0 for r in rows if re.match(r"^\d{1,3}\s*[.．]", r.text)]
    numx.sort()
    left_limit = (numx[len(numx) // 2] if numx else 0) + 12

    questions: list[Q] = []
    multi = False
    skip_hdr = False
    if_table = False
    cur: Q | None = None
    mapping = False
    refmode = False
    last_elem: list | None = None  # where continuation text goes: ['stem'] / ['opt', L] / ['stmt', i]
    expected = 1

    def flush_cont(text: str) -> None:
        nonlocal cur, last_elem
        assert cur is not None
        if last_elem is None or last_elem[0] == "stem":
            cur.stem_parts.append(text)
        elif last_elem[0] == "opt":
            cur.options[last_elem[1]] = join_text(cur.options[last_elem[1]], text)
        elif last_elem[0] == "stmt":
            n, t = cur.stmts[last_elem[1]]
            cur.stmts[last_elem[1]] = (n, join_text(t, text))

    for r in rows:
        t = r.text
        compact = t.replace(" ", "")
        # 108/110:答案在題號之後的某一列左欄(紅色 span 已從文字中剔除,這裡只認列)
        if id(r) in red_answers and cur is not None and not RE_QSTART.match(t):
            if cur.answer and cur.answer != red_answers[id(r)]:
                cur.notes.append(f"兩個紅色答案 {cur.answer}/{red_answers[id(r)]}")
            cur.answer, cur.answer_src = red_answers[id(r)], "red-left"
            if not t:
                continue
        if RE_TITLE.search(t):
            continue
        if compact and all(c in NOISE_CHARS for c in compact):
            continue
        if RE_SECTION.search(t) and len(compact) <= 16:
            multi = "複選題" in t
            skip_hdr = True
            if_table = False
            continue
        if skip_hdr:
            if re.match(r"^IF\s*[:：]", t):
                if_table = True
                continue
            if "請於" in t and "Answer" in t:
                continue
            if if_table and (re.search(r"Correct\s*,?\s*Please\s+Choose", t, re.I) or re.fullmatch(r"\(?[A-E]\)?", t)):
                continue
            skip_hdr = False

        # ---- 新題? ----
        m = RE_QSTART.match(t)
        if m and r.x0 <= left_limit:
            num = int(m.group(1))
            ok = num == expected or (multi and num == 1 and (not questions or not questions[-1].multi))
            if ok:
                cur = Q(num=num, multi=multi)
                questions.append(cur)
                expected = num + 1
                mapping = refmode = False
                last_elem = ["stem"]
                rest = m.group(2).strip()
                cur.raw.append(t)
                g = RE_GONG.match(rest)
                if g:
                    cur.gong = True
                    rest = rest[g.end():].strip()
                if id(r) in red_answers:
                    cur.answer, cur.answer_src = red_answers[id(r)], "red-inline"
                if year == 109:
                    b = RE_ANS_BARE_109.match(rest)
                    if b:
                        cur.answer, cur.answer_src = b.group(1), "bold-inline"
                        rest = b.group(2)
                if 111 <= year <= 113:
                    cands = [(abs(y - r.y0), L) for p, y, L in col_answers if p == r.page]
                    cands.sort()
                    if cands and cands[0][0] <= 8:
                        cur.answer, cur.answer_src = cands[0][1], f"col dy={cands[0][0]:.1f}"
                        col_answers.remove(next(c for c in col_answers if c[0] == r.page and abs(c[1] - r.y0) == cands[0][0]))
                if rest:
                    cur.stem_parts.append(rest)
                continue
        if cur is None:
            continue
        cur.raw.append(t)

        # ---- K-type 對照表 ----
        if cur.multi:
            h = RE_ANSWER_HDR.match(t)
            if h:
                mapping, refmode = True, False
                rest = h.group(1).strip()
                if rest:
                    found = RE_MAP_INLINE.findall(rest)
                    if found:
                        for L, body in found:
                            cur.kmap[L] = normalize_combo(body)
                    else:
                        cur.notes.append(f"Answer 行無法解析: {t}")
                continue
            if mapping and RE_REF.match(t):
                mapping = False  # 對照表之後接參考列(108 Q36)
            elif mapping or RE_MAP_DOT.match(t) or RE_MAP_CHOOSE.match(t):
                mapping = True
                mc = RE_MAP_CHOOSE.match(t)
                md = RE_MAP_DOT.match(t)
                if mc:
                    L, body = mc.group(2), mc.group(1)
                elif md:
                    L, body = md.group(1), md.group(2)
                else:
                    found = RE_MAP_INLINE.findall(t)
                    if not found:
                        cur.notes.append(f"對照表行無法解析: {t}")
                        continue
                    for L, body in found:
                        cur.kmap[L] = normalize_combo(body)
                    continue
                combo = normalize_combo(body)
                if not combo:
                    cur.notes.append(f"對照表行無法解析(選項 {L} 的組合是空的): {t}")
                cur.kmap[L] = combo
                continue

        # ---- 參考來源 ----
        if RE_REF.match(t):
            refmode = True
            cur.ref.append(t)
            continue
        if refmode:
            cur.ref.append(t)
            continue

        # ---- 選項 / 敘述 ----
        mo = RE_OPTION.match(t) or (None if cur.multi else RE_OPTION_DOT.match(t))
        if mo and not cur.multi:
            L = mo.group(1)
            if L in cur.options:
                cur.notes.append(f"選項 {L} 重複出現: {t}")
            cur.options[L] = mo.group(2).strip()
            cur.opt_order.append(L)
            last_elem = ["opt", L]
            continue
        ms = RE_STMT.match(t)
        if ms and cur.multi:
            cur.stmts.append((ms.group(1), ms.group(2).strip()))
            last_elem = ["stmt", len(cur.stmts) - 1]
            continue
        if mo and cur.multi:
            cur.notes.append(f"複選題出現 (X) 選項列: {t}")
        flush_cont(t)

    # ---- 收尾 ----
    for q in questions:
        if q.multi:
            if not q.kmap:
                q.kmap = dict(DEFAULT_K_MAP) if year == 108 else {}
                if year == 108:
                    q.notes.append("使用卷首共用對照表")
            q.options = {L: q.kmap.get(L, "") for L in "ABCDE"}
            q.opt_order = [L for L in "ABCDE" if q.kmap.get(L)]
            nums = [n for n, _ in q.stmts]
            if nums and nums[0] != "1" and nums == [str(int(nums[0]) + i) for i in range(len(nums))]:
                q.stmts = [(str(i + 1), t) for i, (_, t) in enumerate(q.stmts)]
                q.notes.append(f"敘述編號原為 ({nums[0]})–({nums[-1]}),已重編為 (1)–({len(nums)})")
    return questions


def source_text(ref: list[str]) -> str:
    """逐行剝前綴與外層括號:「(Reference: X)」+「Townsley DM…」→「X Townsley DM…」。"""
    out: list[str] = []
    open_paren = False
    for line in ref:
        t = line.strip()
        starts_paren = t.startswith("(") and not re.match(r"^\(\s*[A-E\d]\s*\)", t)
        t = re.sub(r"^\(?\s*(?:Ref|Reference|Source)\s*[:：]\s*", "", t, flags=re.I)
        t = re.sub(r"^\(?\s*來源出處\s*[:：]?\s*", "", t)
        if starts_paren and t.startswith("("):
            t = t[1:]
        if (starts_paren or open_paren) and t.endswith(")") and t.count(")") > t.count("("):
            t = t[:-1]
            open_paren = False
        elif starts_paren:
            open_paren = True
        elif t.endswith(")") and t.count(")") > t.count("("):
            t = t[:-1]  # 108 Q32「來源出處：…p349)」—— 原文就多一個右括號
        out.append(t.strip())
    return re.sub(r"\s+", " ", " ".join(out)).strip()


def stem_text(q: Q) -> str:
    stem = ""
    for p in q.stem_parts:
        stem = join_text(stem, p)
    if q.multi and q.stmts:
        stem += "\n" + "\n".join(f"({n}) {t}" for n, t in q.stmts)
    return stem.strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    qs = parse(a.pdf, a.year)

    n_single = sum(1 for q in qs if not q.multi)
    records = []
    problems = []
    seq = 0
    for q in qs:
        seq += 1
        number = seq
        stem = stem_text(q)
        opts = {L: q.options.get(L, "").strip() for L in "ABCDE"}
        n_opts = sum(1 for v in opts.values() if v)
        tags = []
        if q.gong:
            tags.append("共同")
        if q.multi:
            tags.append("複選")
        issues = []
        if not stem:
            issues.append("題幹為空")
        if n_opts < 4:
            issues.append(f"選項只有 {n_opts} 個")
        if q.multi and not q.stmts:
            issues.append("複選題文字層沒有 (1)–(4) 敘述(可能是圖片)")
        if not q.answer:
            issues.append("答案缺")
        elif not opts.get(q.answer):
            issues.append(f"答案 {q.answer} 對應的選項是空的")
        issues += [n for n in q.notes if "無法解析" in n or "重複" in n or "兩個" in n or "複選題出現" in n]
        answer = q.answer
        if issues:
            answer = ""
            problems.append({
                "number": number, "orig": q.num, "multi": q.multi, "issues": issues,
                "pdf_answer": q.answer, "snippet": " / ".join(q.raw[:3])[:220],
            })
        records.append({
            "year": a.year, "number": number, "group": "內科", "stem": stem,
            "option_a": opts["A"], "option_b": opts["B"], "option_c": opts["C"],
            "option_d": opts["D"], "option_e": opts["E"], "answer": answer,
            "tags": ";".join(tags), "difficulty": "", "source": source_text(q.ref),
        })

    os.makedirs(a.out, exist_ok=True)
    csv_path = os.path.join(a.out, f"hsct-{a.year}.csv")
    cols = ["year", "number", "group", "stem", "option_a", "option_b", "option_c", "option_d",
            "option_e", "answer", "tags", "difficulty", "source"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writeheader()
        for rec in records:
            for k, v in rec.items():
                if isinstance(v, str) and "\r" in v:
                    rec[k] = v.replace("\r", "")
            w.writerow(rec)

    # 自動驗證
    nums = [r["number"] for r in records]
    checks = {
        "total": len(records), "single": n_single, "multi": len(records) - n_single,
        "numbers_contiguous": nums == list(range(1, len(records) + 1)),
        "orig_numbers": [q.num for q in qs],
        "problems": problems,
        "notes": [{"number": i + 1, "orig": q.num, "notes": q.notes} for i, q in enumerate(qs) if q.notes],
        "answer_sources": {s: sum(1 for q in qs if q.answer_src == s.split()[0] or q.answer_src.startswith(s)) for s in ("red-inline", "red-left", "bold-inline", "col")},
        "noise_hits": [],
    }
    noise_re = re.compile(r"(?:^|\s)題號(?:\s|$)|(?:^|\s)答案(?:\s|$)|\(共\)|^共同\s|Ref:|Reference:|來源出處|Please Choose|……|^\s*IF:", re.M)
    for rec in records:
        for k in ("stem", "option_a", "option_b", "option_c", "option_d", "option_e"):
            if noise_re.search(rec[k]):
                checks["noise_hits"].append({"number": rec["number"], "field": k, "text": rec[k][:120]})
    with open(os.path.join(a.out, f"hsct-{a.year}.check.json"), "w", encoding="utf-8") as f:
        json.dump(checks, f, ensure_ascii=False, indent=1)
    print(f"[{a.year}] {len(records)} 題 (單選 {n_single} / 複選 {len(records) - n_single}), "
          f"待確認 {len(problems)}, 雜訊命中 {len(checks['noise_hits'])}, 連續={checks['numbers_contiguous']}")
    print(f"  -> {csv_path}")


if __name__ == "__main__":
    main()
