#!/usr/bin/env python3
import csv, json, subprocess, time, hashlib, socket
from pathlib import Path
OUT=Path('kaom_probe_output'); OUT.mkdir(exist_ok=True)
UA='WangLi-timeplanes-source-audit/1.0 (academic research; low-rate public-form probe)'
JOBS=[
 ('jdsw_dong','POST','http://www.kaom.net/zgy_jdsw8.php',[('word','東'),('mode','word'),('bianti','no'),('wenzi','查 詢')]),
 ('buddhist_dong','POST','http://www.kaom.net/book_vot8.php',[('word','東'),('mode','word'),('bianti','yes')]),
 ('wordbooks_dong','POST','http://www.kaom.net/word8.php',[('word','東'),('mode','word'),('bianti','yes'),('book[]','jinshuyinyi'),('book[]','qieyun'),('book[]','zhongyuanyinyun'),('book[]','zhongzhouyinyun')]),
 ('jiajie_dong','POST','http://www.kaom.net/book_jiajie8.php',[('word','東'),('mode','word'),('page','no'),('bianti','yes')]),
]
rows=[]
try:
    dns=socket.getaddrinfo('www.kaom.net',80)
    (OUT/'dns.txt').write_text('\n'.join(str(x) for x in dns),encoding='utf-8')
except Exception as e:
    (OUT/'dns.txt').write_text('DNS_ERROR '+repr(e),encoding='utf-8')
for i,(name,method,url,data) in enumerate(JOBS):
    if i: time.sleep(4.2)
    path=OUT/f'{name}.html'
    cmd=['curl','-L','--fail','--silent','--show-error','--connect-timeout','6','--max-time','15','-A',UA,'-o',str(path),'-w','%{http_code} %{url_effective} %{remote_ip}',url]
    for k,v in data: cmd += ['--data-urlencode',f'{k}={v}']
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=20)
    status=p.stdout.strip(); err=p.stderr.strip()
    b=path.read_bytes() if path.exists() else b''
    text=b.decode('utf-8','ignore')
    rows.append({'name':name,'status':status,'returncode':p.returncode,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest() if b else '', 'table_count':text.lower().count('<table'), 'tr_count':text.lower().count('<tr'), 'rate_limit':'點擊過頻' in text, 'error':err})
with open(OUT/'probe_summary.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
print(json.dumps(rows,ensure_ascii=False,indent=2))
