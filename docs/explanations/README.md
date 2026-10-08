# 結構化詳解生成(v2:標題階層為主)

- `FORMAT.md`:規格(# 主題 / ## 六段 / ### 子題,清單只在標題不夠用時;表格用在比較)
- `PROMPT.txt`:給 subagent 的提示詞範本,`BATCH` 換成 `<年>-<批>`(每批 10 題,35 批)
- `in/<年>-<批>.json`:每批輸入(題目、答案、章節頁碼、關鍵字 tag)
- `out/<年>-<批>.json`:已完成的輸出 `{number, explanation_md}`
- `assemble.py <年>`:把 out/ 合成 `years/<年>/batches/batch-01.json`(114 年前面加 AI 暫定警語、47 題嵌流程圖),
  再 `python3 scripts/seed-explanations.py --remote --year <年>`。路徑寫死在 scratchpad,換機器要改 `S`。
- EBMT 手冊全文(agent 用來 grep 頁碼)不在 repo:`pdftotext -layout ebmt-handbook.pdf` 後每頁以 `===== PDF PAGE N =====` 分隔。

進度(2026-10-08):108–111 全年 v2 已上線;112–114 進行中(subagent 改用 sonnet);out/ 裡有哪些批就是做到哪。缺的批照 PROMPT.txt 補跑即可。
