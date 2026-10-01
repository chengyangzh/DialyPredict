#!/usr/bin/env python3
import csv, json, os, subprocess, time, hashlib
from pathlib import Path

OUT=Path('kaom_probe_output'); OUT.mkdir(exist_ok=True)
UA='WangLi-timeplanes-source-audit/1.0 (academic research; low-rate public-form probe)'
JOBS=[
 ('jdsw_empty','https://www.kaom.net/zgy_jdsw8.php',[('word',''),('mode','word'),('bianti','no'),('wenzi','查 詢')]),
 ('buddhist_empty','https://www.kaom.net/book_vot8.php',[('word',''),('mode','word'),('bianti','yes')]),
 ('jinshuyinyi_empty','https://www.kaom.net/word8.php',[('word',''),('mode','word'),('bianti','yes'),('book[]','jinshuyinyi')]),
 ('qieyun_empty','https://www.kaom.net/word8.php',[('word',''),('mode','word'),('bianti','yes'),('book[]','qieyun')]),
 ('zhongyuanyinyun_empty','https://www.kaom.net/word8.php',[('word',''),('mode','word'),('bianti','yes'),('book[]','zhongyuanyinyun')]),
 ('zhongzhouyinyun_empty','https://www.kaom.net/word8.php',[('word',''),('mode','word'),('bianti','yes'),('book[]','zhongzhouyinyun')]),
 ('jiajie_empty','https://www.kaom.net/book_jiajie8.php',[('word',''),('mode','word'),('page','no'),('bianti','yes')]),
]
rows=[]
for i,(name,url,data) in enumerate(JOBS):
    if i: time.sleep(4.2)
    path=OUT/f'{name}.html'
    cmd=['curl','-L','--fail','--silent','--show-error','--max-time','90','-A',UA,'-o',str(path),'-w','%{http_code} %{url_effective}',url]
    for k,v in data: cmd += ['--data-urlencode',f'{k}={v}']
    p=subprocess.run(cmd,capture_output=True,text=True)
    status=p.stdout.strip(); err=p.stderr.strip()
    b=path.read_bytes() if path.exists() else b''
    text=b.decode('utf-8','ignore')
    rows.append({'name':name,'status':status,'returncode':p.returncode,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest() if b else '', 'table_count':text.lower().count('<table'), 'tr_count':text.lower().count('<tr'), 'rate_limit':'點擊過頻' in text, 'error':err})
with open(OUT/'probe_summary.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
print(json.dumps(rows,ensure_ascii=False,indent=2))
