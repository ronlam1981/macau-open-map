"""Fetch only official published open data; never store Authorization codes in output."""
import json,urllib.request,concurrent.futures,pathlib,datetime,time,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];CACHE=ROOT/'data/raw';CACHE.mkdir(exist_ok=True)
def request(url,method='GET',code=None):
 h={'User-Agent':'MacauOpenMap/1.0 (open data integration)','lang':'TC'}
 if code:h['Authorization']='APPCODE '+code
 if method=='POST':h['Content-Type']='application/json'
 req=urllib.request.Request(url,data=b'{}' if method=='POST' else None,headers=h,method=method)
 with urllib.request.urlopen(req,timeout=50) as r:return r.read()
def get(s):
 f=CACHE/(s['id']+'.json')
 if f.exists() and '--refresh' not in sys.argv:return
 try:
  d=json.loads(request('https://api.data.gov.mo/datadir/detail/'+s['id']))['data']
  a=json.loads(request('https://api.data.gov.mo/api/'+str(s['apiId'])))['data']
  if not d.get('appCode'):raise ValueError('No public authorization available')
  raw=request(a['apiPath'],a.get('httpMethod','GET'),d['appCode']).decode('utf-8-sig')
  out={'source':s,'retrievedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'type':a['resultType'],'body':raw}
  f.write_text(json.dumps(out,ensure_ascii=False));print(s['name'],len(raw),'OK',flush=True)
 except Exception as e:print(s['name'],type(e).__name__,str(e),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:list(ex.map(get,json.loads((ROOT/'data/sources.json').read_text())))
