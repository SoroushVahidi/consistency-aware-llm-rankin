#!/usr/bin/env python3
"""Validate the public v1.0.0 ranking package without private benchmark inputs."""
import collections
import csv
import gzip
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b''): h.update(chunk)
    return h.hexdigest()

files={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()}
ledger={}
for line in (ROOT/'CHECKSUMS.sha256').read_text().splitlines():
    if line.strip():
        digest, rel=line.split('  ',1)
        assert rel not in ledger
        ledger[rel]=digest
assert files == set(ledger)|{'CHECKSUMS.sha256'}, (sorted(files-set(ledger)),sorted(set(ledger)-files))
assert all(sha(ROOT/rel)==digest for rel,digest in ledger.items())

with gzip.open(ROOT/'data/novel_ndcg.csv.gz','rt',newline='',encoding='utf-8') as f:
    reader=csv.DictReader(f); fields=reader.fieldnames; rows=list(reader)
assert fields==['record_id','benchmark','unit_id','regime','pool_policy_id','pool_size','metric_cutoff','config_id','method_key','metric_name','ndcg_value','run_id','protocol_id','replicate_id','seed','comparator_method_key']
assert len(rows)==93504
by_benchmark=collections.defaultdict(set)
methods=collections.defaultdict(set)
values=collections.defaultdict(list)
ids=set()
for r in rows:
    assert set(r)==set(fields)
    assert r['benchmark'] in {'scidocs','fiqa','hotpotqa','bright'}
    assert len(r['unit_id'])==64 and all(c in '0123456789abcdef' for c in r['unit_id'])
    assert len(r['record_id'])==64 and all(c in '0123456789abcdef' for c in r['record_id'])
    assert r['metric_name']=='ndcg' and r['protocol_id']=='minmax_raw_matched' and r['pool_policy_id']=='rrf_union_topk'
    assert not r['replicate_id'] and not r['seed']
    assert int(r['pool_size'])>=int(r['metric_cutoff'])
    assert r['config_id']==f"pool{r['pool_size']}_ndcg{r['metric_cutoff']}"
    assert r['run_id']==f"greedy-20260714/{r['benchmark']}/{r['regime']}/{r['config_id']}"
    key=(r['benchmark'],r['regime'],r['config_id'],int(r['pool_size']),int(r['metric_cutoff']),r['unit_id'],r['method_key'])
    assert key not in ids
    ids.add(key)
    assert r['record_id']==hashlib.sha256(json.dumps(key,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    value=float(r['ndcg_value']);assert math.isfinite(value) and 0<=value<=1
    by_benchmark[r['benchmark']].add(r['unit_id'])
    methods[key[:-1]].add(r['method_key'])
    values[(r['benchmark'],r['regime'],r['config_id'],r['method_key'])].append(value)
assert {k:len(v) for k,v in by_benchmark.items()}=={'scidocs':120,'fiqa':120,'hotpotqa':52,'bright':50}
assert len(methods)==5844 and all(len(v)==16 for v in methods.values())
assert len(values)==1056
with (ROOT/'data/configurations.csv').open(newline='') as f: configs=list(csv.DictReader(f))
assert len(configs)==66 and len({r['run_id'] for r in configs})==66
with (ROOT/'validation/summary_reproduction.csv').open(newline='') as f: summaries=list(csv.DictReader(f))
assert len(summaries)==1056
for s in summaries:
    v=values[(s['benchmark'],s['regime'],s['config_id'],s['method_key'])]
    assert len(v)==int(s['n_queries'])
    assert abs(statistics.fmean(v)-float(s['mean_ndcg']))<=1e-14
    assert abs(min(v)-float(s['min_ndcg']))<=1e-14
    assert abs(max(v)-float(s['max_ndcg']))<=1e-14
with gzip.open(ROOT/'comparison/public_vs_new.csv.gz','rt',newline='') as f: comparison=list(csv.DictReader(f))
assert len(comparison)==93504 and {r['record_id'] for r in comparison}=={r['record_id'] for r in rows}
assert all(r['exact_public_identity_matches']=='0' for r in comparison)
print(json.dumps({'status':'PASS','files':len(files),'checksummed_files':len(ledger),'records':len(rows),'queries':sum(map(len,by_benchmark.values())),'configurations':len(configs),'summary_rows':len(summaries),'comparison_rows':len(comparison)},sort_keys=True))
