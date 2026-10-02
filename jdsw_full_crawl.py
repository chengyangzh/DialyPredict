#!/usr/bin/env python3
import csv, json, os, subprocess, time, hashlib
from pathlib import Path
from bs4 import BeautifulSoup

BASE='http://www.kaom.net'
UA='WangLi-timeplanes-source-audit/1.0 (academic research; low-rate public-data crawl)'
CHUNK_INDEX=int(os.environ['CHUNK_INDEX'])
CHUNK_COUNT=int(os.environ.get('CHUNK_COUNT','24'))
OUT=Path(f'jdsw_full_output/chunk_{CHUNK_INDEX:02d}')
RAW=OUT/'raw_html'; RAW.mkdir(parents=True, exist_ok=True)

# Fetch the official Kaom contents page and extract the exact detail-entry universe.
idx_path=OUT/'jdsw_contents.html'
cmd=['curl','-L','--fail','--silent','--show-error','--connect-timeout','8','--max-time','60','-A',UA,
     '-o',str(idx_path),'-w','%{http_code}',BASE+'/zgy_jdsw_box.php','--data-urlencode','wenzi=目錄']
p=subprocess.run(cmd,capture_output=True,text=True,timeout=70)
if p.returncode!=0 or p.stdout.strip()!='200':
    raise SystemExit(f'failed to fetch contents page: rc={p.returncode} http={p.stdout} err={p.stderr}')
html=idx_path.read_text(encoding='utf-8',errors='ignore')
soup=BeautifulSoup(html,'html.parser')
entries=[]
seen=set()
for a in soup.find_all('a',href=True):
    href=a['href']
    marker='zgy_jdsw8.php?id='
    if marker not in href: continue
    try: eid=int(href.split(marker,1)[1].split('&',1)[0])
    except Exception: continue
    if eid in seen: continue
    seen.add(eid)
    entries.append((eid,a.get_text(' ',strip=True)))
if len(entries)!=60784:
    raise SystemExit(f'index universe mismatch: expected 60784, got {len(entries)}')
entries.sort(key=lambda x:x[0])

# contiguous, exhaustive partition over exactly 60,784 entries
n=len(entries); q,r=divmod(n,CHUNK_COUNT)
start=CHUNK_INDEX*q+min(CHUNK_INDEX,r)
end=start+q+(1 if CHUNK_INDEX<r else 0)
chunk=entries[start:end]

manifest=[]; rows=[]; failures=[]
for pos,(eid,headword) in enumerate(chunk):
    if pos: time.sleep(4.2)
    url=f'{BASE}/zgy_jdsw8.php?id={eid}'
    path=RAW/f'{eid}.html'
    cmd=['curl','-L','--fail','--silent','--show-error','--connect-timeout','8','--max-time','30','-A',UA,
         '-o',str(path),'-w','%{http_code} %{url_effective} %{remote_ip}',url]
    pr=subprocess.run(cmd,capture_output=True,text=True,timeout=40)
    b=path.read_bytes() if path.exists() else b''
    text=b.decode('utf-8','ignore')
    rate=('點擊過頻' in text or '点击过频' in text)
    http=pr.stdout.strip()
    ok=(pr.returncode==0 and http.startswith('200 ') and len(b)>0 and not rate)
    manifest.append({'entry_id':eid,'headword_index':headword,'chunk':CHUNK_INDEX,'chunk_pos':pos,
                     'http':http,'returncode':pr.returncode,'bytes':len(b),
                     'sha256':hashlib.sha256(b).hexdigest() if b else '',
                     'rate_limited':rate,'success':ok,'error':pr.stderr.strip(),
                     'raw_html':f'raw_html/{eid}.html'})
    if not ok:
        failures.append(eid); continue
    s=BeautifulSoup(text,'html.parser')
    for ti,table in enumerate(s.find_all('table')):
        trs=table.find_all('tr')
        if not trs: continue
        headers=[x.get_text(' ',strip=True) for x in trs[0].find_all(['th','td'])]
        for ri,tr in enumerate(trs[1:],start=1):
            cells=[x.get_text(' ',strip=True) for x in tr.find_all(['th','td'])]
            if not cells: continue
            links=';'.join(a.get('href','') for a in tr.find_all('a',href=True))
            rows.append({'entry_id':eid,'headword_index':headword,'table_index':ti,'row_index':ri,
                         'headers_json':json.dumps(headers,ensure_ascii=False),
                         'cells_json':json.dumps(cells,ensure_ascii=False),
                         'links':links,'raw_html':f'raw_html/{eid}.html'})

with open(OUT/'entry_manifest.csv','w',encoding='utf-8-sig',newline='') as f:
    fields=['entry_id','headword_index','chunk','chunk_pos','http','returncode','bytes','sha256','rate_limited','success','error','raw_html']
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(manifest)
with open(OUT/'parsed_rows.csv','w',encoding='utf-8-sig',newline='') as f:
    fields=['entry_id','headword_index','table_index','row_index','headers_json','cells_json','links','raw_html']
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
(OUT/'failed_ids.txt').write_text('\n'.join(map(str,failures)),encoding='utf-8')
summary={'expected_universe':60784,'chunk_index':CHUNK_INDEX,'chunk_count':CHUNK_COUNT,
         'chunk_start_offset':start,'chunk_end_offset_exclusive':end,'chunk_entries':len(chunk),
         'successful_entries':sum(1 for x in manifest if x['success']),'failed_entries':len(failures),
         'parsed_rows':len(rows),'first_entry_id':chunk[0][0] if chunk else None,'last_entry_id':chunk[-1][0] if chunk else None}
(OUT/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
