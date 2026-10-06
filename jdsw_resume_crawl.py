#!/usr/bin/env python3
import csv, json, os, time, random, hashlib
from pathlib import Path
import requests
from bs4 import BeautifulSoup

BASE='http://www.kaom.net'
UA='WangLi-timeplanes-source-audit/1.0 (academic research; low-rate public-data crawl)'
BATCH_SIZE=int(os.environ.get('BATCH_SIZE','150'))
PRIOR=Path('prior_artifacts')
OUT=Path('jdsw_resume_output'); RAW=OUT/'raw_html'; RAW.mkdir(parents=True,exist_ok=True)

# Rebuild exact 60,784-entry universe from Kaom.
s=requests.Session(); s.headers.update({'User-Agent':UA})
r=s.post(BASE+'/zgy_jdsw_box.php',data={'wenzi':'目錄'},timeout=60)
r.raise_for_status()
soup=BeautifulSoup(r.text,'html.parser')
universe=[]; seen=set()
for a in soup.find_all('a',href=True):
    href=a['href']; marker='zgy_jdsw8.php?id='
    if marker not in href: continue
    try: eid=int(href.split(marker,1)[1].split('&',1)[0])
    except: continue
    if eid not in seen:
        seen.add(eid); universe.append((eid,a.get_text(' ',strip=True)))
universe.sort()
if len(universe)!=60784: raise SystemExit(f'universe mismatch {len(universe)}')

# An ID is authoritative-success only if manifest says success, sha matches a nonempty raw HTML,
# and parsed_rows contains at least one row for that entry.
successful=set()
for manifest in PRIOR.rglob('entry_manifest.csv'):
    root=manifest.parent
    parsed=root/'parsed_rows.csv'
    parsed_ids=set()
    if parsed.exists():
        with parsed.open(encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f):
                try: parsed_ids.add(int(row['entry_id']))
                except: pass
    with manifest.open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            try: eid=int(row['entry_id'])
            except: continue
            if str(row.get('success','')).lower() not in ('true','1'): continue
            if eid not in parsed_ids: continue
            rel=row.get('raw_html',f'raw_html/{eid}.html')
            raw=root/rel
            if not raw.exists(): continue
            b=raw.read_bytes()
            if not b: continue
            sha=hashlib.sha256(b).hexdigest()
            if row.get('sha256','').strip().lower()!=sha: continue
            successful.add(eid)

remaining=[(eid,hw) for eid,hw in universe if eid not in successful]
queue=remaining[:BATCH_SIZE]
(OUT/'resume_queue.txt').write_text('\n'.join(str(x[0]) for x in queue),encoding='utf-8')
(OUT/'remaining_before_batch.txt').write_text('\n'.join(str(x[0]) for x in remaining),encoding='utf-8')

manifest=[]; rows=[]; failures=[]; consecutive_empty=0; stopped_reason=''
for pos,(eid,headword) in enumerate(queue):
    if pos: time.sleep(random.uniform(4.5,6.0))
    url=f'{BASE}/zgy_jdsw8.php?id={eid}'
    try:
        resp=s.get(url,timeout=35,allow_redirects=True)
        b=resp.content or b''
        text=b.decode('utf-8','ignore')
        rate=('點擊過頻' in text or '点击过频' in text)
        empty=(resp.status_code==200 and len(b)==0)
        ok_http=(resp.status_code==200 and len(b)>0 and not rate)
        err=''
    except Exception as e:
        resp=None; b=b''; text=''; rate=False; empty=True; ok_http=False; err=repr(e)
    if empty: consecutive_empty+=1
    else: consecutive_empty=0
    parsed_for_entry=[]
    if ok_http:
        ps=BeautifulSoup(text,'html.parser')
        for ti,table in enumerate(ps.find_all('table')):
            trs=table.find_all('tr')
            if not trs: continue
            headers=[x.get_text(' ',strip=True) for x in trs[0].find_all(['th','td'])]
            for ri,tr in enumerate(trs[1:],1):
                cells=[x.get_text(' ',strip=True) for x in tr.find_all(['th','td'])]
                if cells:
                    parsed_for_entry.append({'entry_id':eid,'headword_index':headword,'table_index':ti,'row_index':ri,
                      'headers_json':json.dumps(headers,ensure_ascii=False),'cells_json':json.dumps(cells,ensure_ascii=False),
                      'links':';'.join(a.get('href','') for a in tr.find_all('a',href=True)),'raw_html':f'raw_html/{eid}.html'})
    success=ok_http and bool(parsed_for_entry)
    if b: (RAW/f'{eid}.html').write_bytes(b)
    sha=hashlib.sha256(b).hexdigest() if b else ''
    manifest.append({'entry_id':eid,'headword_index':headword,'batch_pos':pos,'http_status':getattr(resp,'status_code',''),
      'bytes':len(b),'sha256':sha,'rate_limited':rate,'success':success,'error':err,'raw_html':f'raw_html/{eid}.html'})
    if success: rows.extend(parsed_for_entry)
    else: failures.append(eid)
    if rate:
        stopped_reason='soft_rate_limit'; break
    if consecutive_empty>=3:
        stopped_reason='three_consecutive_empty_bodies'; break

fields=['entry_id','headword_index','batch_pos','http_status','bytes','sha256','rate_limited','success','error','raw_html']
with (OUT/'entry_manifest.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(manifest)
pfields=['entry_id','headword_index','table_index','row_index','headers_json','cells_json','links','raw_html']
with (OUT/'parsed_rows.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=pfields); w.writeheader(); w.writerows(rows)
(OUT/'failed_ids.txt').write_text('\n'.join(map(str,failures)),encoding='utf-8')
summary={'expected_universe':60784,'validated_success_before_batch':len(successful),'remaining_before_batch':len(remaining),
 'queued':len(queue),'attempted':len(manifest),'successful_this_batch':sum(str(x['success']).lower()=='true' for x in manifest),
 'failed_this_batch':len(failures),'parsed_rows':len(rows),'stopped_reason':stopped_reason}
(OUT/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
