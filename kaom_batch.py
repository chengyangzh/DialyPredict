#!/usr/bin/env python3
import csv, json, subprocess, time, hashlib
from pathlib import Path
from bs4 import BeautifulSoup

OUT=Path('kaom_batch_output'); RAW=OUT/'raw_html'; RAW.mkdir(parents=True, exist_ok=True)
UA='WangLi-timeplanes-source-audit/1.0 (academic research; source-driven low-rate public-data crawl)'

SOURCE_JOBS={
 'jingdian_shiwen':{
   'chars':['㐲','㐼','㑹','㒉','㒼','㓨','㓷','㔻','㕞','㕣','㖩','㗉','㗛','㘲','㚄','㚟','㛮','㛰','㜸','㝔','㝠','㝱','㝷','㞵','㟪'],
   'url':'http://www.kaom.net/zgy_jdsw8.php',
   'make':lambda c:[('word',c),('mode','word'),('bianti','no'),('wenzi','查 詢')]
 },
 'buddhist_yinyi':{
   'chars':['㐭','㑌','㑗','㑥','㑦','㑷','㒋','㒤','㒵','㓗','㓨','㕘','㕟','㕺','㖑','㖟','㖶','㗖','㗧','㘝','㙪','㚊','㝡','㝯','㝹'],
   'url':'http://www.kaom.net/book_vot8.php',
   'make':lambda c:[('word',c),('mode','word'),('bianti','yes')]
 },
 'wang_rhyme_books':{
   'chars':['㐌','㐫','㑳','㑹','㒋','㒯','㓜','㓶','㓽','㔨','㕒','㖔','㗢','㗦','㘅','㙲','㚀','㚇','㚟','㜞','㜪','㜰','㜷','㝞','㝠'],
   'url':'http://www.kaom.net/word8.php',
   'make':lambda c:[('word',c),('mode','word'),('bianti','yes'),('book[]','jinshuyinyi'),('book[]','qieyun'),('book[]','zhongyuanyinyun'),('book[]','zhongzhouyinyun')]
 },
 'jiajie_tongjia':{
   'chars':['㐲','㐼','㑹','㒉','㒼','㓨','㓷','㔻','㕞','㕣','㖩','㗉','㗛','㘲','㚄','㚟','㛮','㛰','㜸','㝔','㝠','㝱','㝷','㞵','㟪'],
   'url':'http://www.kaom.net/book_jiajie8.php',
   'make':lambda c:[('word',c),('mode','word'),('page','no'),('bianti','yes')]
 },
}

def fetch(name,url,data):
    path=RAW/name
    cmd=['curl','-L','--fail','--silent','--show-error','--connect-timeout','6','--max-time','20','-A',UA,'-o',str(path),'-w','%{http_code} %{url_effective} %{remote_ip}',url]
    for k,v in data: cmd += ['--data-urlencode',f'{k}={v}']
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=25)
    b=path.read_bytes() if path.exists() else b''
    return p,b

def parse_tables(html, module, query_char, raw_path):
    soup=BeautifulSoup(html,'html.parser')
    out=[]
    for ti,table in enumerate(soup.find_all('table')):
        trs=table.find_all('tr')
        if not trs: continue
        headers=[x.get_text(' ',strip=True) for x in trs[0].find_all(['th','td'])]
        if not headers: continue
        for ri,tr in enumerate(trs[1:],start=1):
            cells=[x.get_text(' ',strip=True) for x in tr.find_all(['th','td'])]
            if not cells: continue
            links=';'.join(a.get('href','') for a in tr.find_all('a',href=True))
            out.append({'module':module,'query_char':query_char,'table_index':ti,'row_index':ri,'headers_json':json.dumps(headers,ensure_ascii=False),'cells_json':json.dumps(cells,ensure_ascii=False),'links':links,'raw_html':raw_path})
    return out

manifest=[]; rows=[]; first=True
for module,spec in SOURCE_JOBS.items():
    for ch in spec['chars']:
        if not first: time.sleep(4.2)
        first=False
        fn=f'{module}_{ord(ch):X}.html'
        p,b=fetch(fn,spec['url'],spec['make'](ch))
        text=b.decode('utf-8','ignore')
        manifest.append({'module':module,'query_char':ch,'http':p.stdout.strip(),'returncode':p.returncode,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest() if b else '', 'tables':text.lower().count('<table'),'trs':text.lower().count('<tr'),'rate_limit':'點擊過頻' in text,'error':p.stderr.strip(),'raw_html':f'raw_html/{fn}'})
        if b: rows.extend(parse_tables(text,module,ch,f'raw_html/{fn}'))
with open(OUT/'request_manifest.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=manifest[0].keys()); w.writeheader(); w.writerows(manifest)
with open(OUT/'parsed_rows.csv','w',encoding='utf-8-sig',newline='') as f:
    fields=['module','query_char','table_index','row_index','headers_json','cells_json','links','raw_html']
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
with open(OUT/'source_batch_summary.json','w',encoding='utf-8') as f:
    json.dump({'requests':len(manifest),'parsed_rows':len(rows),'errors':sum(1 for x in manifest if x['returncode']!=0),'rate_limited':sum(1 for x in manifest if x['rate_limit']),'requests_by_module':{m:sum(1 for x in manifest if x['module']==m) for m in SOURCE_JOBS}},f,ensure_ascii=False,indent=2)
print(json.dumps({'requests':len(manifest),'parsed_rows':len(rows),'errors':sum(1 for x in manifest if x['returncode']!=0),'rate_limited':sum(1 for x in manifest if x['rate_limit'])},ensure_ascii=False))
