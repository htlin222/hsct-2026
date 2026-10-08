"""把 out/<year>-<b>.json 合成 years/<year>/batches/batch-01.json(114 年前面加 AI 暫定警語)。"""
import json, sys, glob, re, os
S='/private/tmp/claude-501/-Users-htlin-hema-2026/92d4e88b-0a03-45b7-8aa9-dd5a6db33ef1/scratchpad/expl/out'
ROOT='/Users/htlin/hsct-2026'
year=sys.argv[1]
ai={}
if year=='114':
    ai={a['number']:a for a in json.load(open(f'{ROOT}/docs/hsct-114-ai-provisional-answers.json',encoding='utf-8'))['answers']}
CONF={'high':'高','medium':'中','low':'低'}
items={}
for f in sorted(glob.glob(f'{S}/{year}-*.json')):
    for q in json.load(open(f,encoding='utf-8')): items[int(q['number'])]=q['explanation_md']
missing=[n for n in range(1,51) if n not in items]
assert not missing, f'missing {missing}'
out=[]
for n in range(1,51):
    md=items[n].strip()
    heads=re.findall(r'^## (\d)\.', md, flags=re.M)
    assert heads==['1','2','3','4','5','6'], (year, n, heads)
    h1=re.findall(r'^# ', md, flags=re.M); assert len(h1)==1, (year, n, 'h1', len(h1))
    h3=len(re.findall(r'^### ', md, flags=re.M)); bullets=len(re.findall(r'^\s*- ', md, flags=re.M))
    assert h3>=8, (year, n, 'h3', h3)
    assert not re.search(r'^>', md, flags=re.M), (year, n, 'blockquote in agent output')
    if year=='114':
        a=ai[n]
        md=(f"> ⚠️ **AI 暫定答案:{a['answer']}**(信心:{CONF[a['confidence']]})。官方 114 年試題 PDF 沒有答案欄,本題答案由 AI 依 *The EBMT Handbook*(2nd ed., 2024)推定,**尚未經人工核對** —— 有疑義請用「挑戰答案」或在討論串提出。\n\n"+md)
        if n==47:
            md=md.replace('## 1. Topic review', '## 原卷流程圖\n\n![113-41 / 114-47 流程圖](https://img-hosting.hsieh-ting-lin.workers.dev/i/orwLp0O.png)\n\n## 1. Topic review',1)
    out.append({'number':n,'explanation_md':md})
os.makedirs(f'{ROOT}/years/{year}/batches', exist_ok=True)
json.dump(out, open(f'{ROOT}/years/{year}/batches/batch-01.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
tables=sum(1 for q in out if '| --- |' in q['explanation_md'])
print(year, 'ok 50 questions, with tables:', tables, 'avg chars:', sum(len(q['explanation_md']) for q in out)//50)
