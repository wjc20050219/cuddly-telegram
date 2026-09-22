#!/usr/bin/env python3
import csv
from pathlib import Path
p=Path('/mnt/d/dsh/RiceVar-ID/data/metadata/candidates/candidate_samples.tsv')
with p.open(encoding='utf-8',errors='replace',newline='') as f:
    raw=f.readlines()
print('raw lines',len(raw),'last repr',repr(raw[-3:]))
with p.open(encoding='utf-8',errors='replace',newline='') as f:
    rows=list(csv.reader(f,delimiter='\t'))
print('csv rows',len(rows),'blank rows',sum(1 for r in rows[1:] if not r or all(not x for x in r)))
h=rows[0]; pi=h.index('publication');
print('nonempty publication',sum(1 for r in rows[1:] if r and pi<len(r) and r[pi].strip()))
print('last data',rows[-2] if len(rows)>1 else None)
