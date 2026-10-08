---
name: hsct-bank
version: 1.0.0
description: 移專衝衝衝(hsct-2026)加題目與標 tag 的固定流程:官方筆試 PDF → CSV → D1,再用兩層受控清單(EBMT 章節 + 關鍵字詞彙)標 tag 讓「相似題目」有東西可吃。當使用者說「加 115 年」「匯入新題目」「幫這些題標 tag」「/hsct-bank」或拿著血液及骨髓移植專科筆試 PDF 來時使用。
---

# hsct-bank — 加題目、標 tag

這支 skill 是「怎麼做」的清單,不是工具包:所有腳本都在 repo 裡,清單也在 repo 裡。
**tag 只能從清單挑,不自創** —— hema-2026 的 `question_tags` 就是自由產生到幾百種
同義寫法才需要另做白名單,這裡從第一天就是受控的。

## 檔案地圖

| 用途 | 檔案 | 備註 |
| --- | --- | --- |
| 解析官方 PDF | `scripts/parse-hsct-exam.py` | PyMuPDF;答案位置每年不同,見下 |
| 題庫 CSV | `years/hsct/hsct-<年>.csv` | gitignored;格式同 `scripts/import-questions.ts` 檔頭 |
| 詳解種子 | `years/<年>/batches/batch-*.json` → `scripts/seed-explanations.py` | `{number, explanation_md}` |
| **第一層 tag(章節,94 個)** | `scripts/ebmt-chapter-tags.json` | 章號 → 短名(「GVHD 預防」「急性 GVHD」「HLA」…) |
| 第一層分類結果 | `docs/hsct-ebmt-chapter-map.json` | 每題 `primary` + 0–2 `secondary` 章號 |
| **第二層 tag(關鍵字,143 個)** | `docs/hsct-keyword-tags.json` 的 `vocab` | `{tag, aliases, group}`,每題 3–6 個 |
| 第二層分類結果 | `docs/hsct-keyword-tags.json` 的 `questions` | `{id, tags:[…]}` |
| 套用兩層 tag | `scripts/apply-ebmt-tags.py --local/--remote` | 冪等;分兩個 `created_by`,不碰其他 tag |
| 解析報告(踩過的坑) | `docs/hsct-pdf-parse-report.md` | 每年答案藏法、缺答案的題 |

## A. 加一個年份的題目

1. **PDF 放進隔離目錄**(不要跟腳本同目錄),先看結構:

       pdftotext -layout <pdf> - | grep -nE '單選|複選|題號|答案' | head

   每年 50 題:單選 1–35、K-type 複選 36–50(複選題若從 1 重編,解析器會接到 36 起)。

2. **解析**(用 bank-ingest skill 的 venv,它有 PyMuPDF):

       /Users/htlin/hsct-2026/.claude/skills/bank-ingest/.venv/bin/python -I \
         scripts/parse-hsct-exam.py <pdf> --year 115 --out years/hsct

   讀 `hsct-115.check.json`:50 題、編號連續、answer 全部非空。**答案藏法每年不同**
   (108/110 紅色 `(X)` span、109 題號後粗體字母、111–113 右欄 x≈537、114 根本沒有),
   新年份要先用 PyMuPDF 看 span 的顏色與座標,再決定要不要改解析器,不要直接信輸出。

3. **缺答案的題不要猜**。114 年是這樣處理的:50 題用 5 個 subagent 各解 10 題、以 EBMT
   Handbook 全文為依據,答案進 `questions.answer`、理由種成詳解、tag `AI暫定`、`source`
   欄註明信心;日後拿到官方答案走站上「挑戰答案」更正(留 `answer_history`),**不要
   重跑 import 蓋掉**。理由與頁碼存在 `docs/hsct-114-ai-provisional-answers.json`。

4. **匯入**:先 local 再 remote。

       node --experimental-strip-types scripts/import-questions.ts years/hsct/hsct-115.csv --local
       node --experimental-strip-types scripts/import-questions.ts years/hsct/hsct-115.csv          # remote

   pre-flight 一筆錯整批拒。`config.toml [groups].list` 是 `內科:50`,`number` 要在 1–50。
   既有年份**不要**重新 import(upsert 會把社群改過的答案蓋回去)。

5. **題幹有圖**的題:用 `img-hosting` skill 把圖 host 成 URL,寫在題幹末尾
   (`流程圖:https://…`),`StemText` 會把 http(s) 網址渲染成連結。詳解可用
   `![](url)` 嵌圖。

## B. 標 tag(兩層都要)

### B1. 第一層:EBMT 章節(粗)

每題 1 個 primary + 0–2 個 secondary **章號**(1–94)。判準是「這題的知識點在手冊
哪一章會被教到」,不是題幹出現了哪個字。分批交給 subagent(每人一年 50 題),提示詞
給它三樣東西:

- 題目 JSON(id / stem / options)
- 章節清單:`python3 -c "import json;[print(c['n'],c['chapter']) for c in json.load(open('scripts/ebmt-chapters.json'))['chapters']]"`
- 手冊全文(可 grep):`pdftotext -layout <ebmt-handbook.pdf> ebmt.txt`,每頁用 `\f` 分隔

輸出 `{"id","primary","secondary":[…],"note"}`,**合併進** `docs/hsct-ebmt-chapter-map.json`
的 `questions`(不要另開檔)。常見的歸章判斷(agent 回報過的):CML 第二版沒有獨立章
→ Ch77 MPN;SOS/VOD → Ch49 肝(不是 Ch42);EBV viremia + pre-emptive rituximab → Ch45
PTLD;感染預防總覽題 → Ch37;移植後 G-CSF 手冊沒專章 → Ch16。

### B2. 第二層:關鍵字(細)

每題 3–6 個,**只能用 `docs/hsct-keyword-tags.json` 的 `vocab` 裡一字不差的 tag**。
判準是這題「考到」這個概念(題幹或正解相關的選項在考它),順便提到的不算。
subagent 的提示詞要附完整 vocab(含 aliases),並要求它**讀檔比對**驗證每個 tag 存在。

要加新詞的規則:**至少 2 題需要**才加(孤兒 tag 對相似題與篩選都沒用),名稱 ≤ 16
字元、藥名用英文原名、概念用中文或通用縮寫;先加進 `vocab` 再用,
`apply-ebmt-tags.py` 遇到不在 vocab 的 tag 會直接拒絕整批。

### B3. 套用與驗證

    python3 scripts/apply-ebmt-tags.py --dry-run     # 看統計
    python3 scripts/apply-ebmt-tags.py --local
    python3 scripts/apply-ebmt-tags.py --remote
    pnpm vectors:backfill                             # Vectorize metadata 帶 tags,改完 tag 要重跑

核對(remote):

    wrangler d1 execute hsct-2026-db --remote --command "
      SELECT created_by, COUNT(*) n, COUNT(DISTINCT question_id) q, COUNT(DISTINCT tag) t
      FROM question_tags GROUP BY created_by;
      SELECT id FROM questions WHERE id NOT IN (SELECT question_id FROM question_tags WHERE created_by LIKE 'keyword-tagger@%');"

第二句要回空:每題都該有關鍵字 tag。`questions_fts` 靠 trigger 跟 `question_tags` 同步,
不要手動 INSERT 進 FTS 表。

## 不要做的事

- 不自創 tag、不在 tag 名裡放章號(使用者要的是一眼看得懂的短字)。
- 不用 `LIKE 'EBMT%'` 之類的字樣去刪 tag;要刪就用 `created_by`。
- 不把 AI 推定的答案當官方答案:一定要 `AI暫定` tag + `source` 註明 + 詳解開頭警語。
