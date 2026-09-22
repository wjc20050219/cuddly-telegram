#!/usr/bin/env python3
import csv
from pathlib import Path
p=Path('/mnt/d/dsh/RiceVar-ID/data/metadata/candidates/candidate_samples.tsv')
tmp=p.with_suffix('.tsv.tmp')
with p.open(encoding='utf-8',newline='') as f:
    r=csv.DictReader(f,delimiter='\t')
    fields=r.fieldnames
    rows=[row for row in r if (row.get('sample_id') or '').strip() and row.get('sample_id') != 'sample_id']
with tmp.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields,delimiter='\t',lineterminator='\n')
    w.writeheader(); w.writerows(rows)
tmp.replace(p)
print(f'保留 {len(rows)} 条，已删除空 sample_id 记录')
