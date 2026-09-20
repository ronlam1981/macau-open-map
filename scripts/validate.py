import json,pathlib,re,collections
r=pathlib.Path(__file__).resolve().parents[1]
d=json.loads((r/'data/site-data.json').read_text());ls={l['id']:l for l in d['layers']};ids=set()
assert len(d['catalog'])==len({x['id'] for x in d['catalog']})==1376
assert all(c['methods'] and c['url'].startswith('https://data.gov.mo/') for c in d['catalog'])
for p in d['points']:
 assert p['id'] not in ids;ids.add(p['id'])
 assert 22.08<=p['lat']<=22.25 and 113.48<=p['lng']<=113.65
 assert p['name'] and p['layers'] and all(x in ls for x in p['layers'])
for l in d['layers']:
 if l['status']=='ready':assert l['count']>0 and l['retrievedAt']
s=(r/'public/index.html').read_text()
assert not re.search(r'APPCODE |"appCode"|Authorization',s)
assert not any(t in s for t in ['/*APP_JS*/','/*DATA*/','/*APP_CSS*/'])
assert json.loads(re.search(r'<script id="dataset" type="application/json">(.*?)</script>',s,re.S).group(1))==d
print(json.dumps({'datasets':len(d['catalog']),'readyLayers':sum(x['status']=='ready' for x in d['layers']),'points':len(d['points']),'status':'PASS'},ensure_ascii=False))
