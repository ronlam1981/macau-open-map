import json,re,html,pathlib,datetime,xml.etree.ElementTree as ET,zipfile,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
def clean(v):
 if not isinstance(v,(str,int,float)):return ''
 return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>',' ',str(v)))).strip()
def first(r,keys):
 lower={k.lower():v for k,v in r.items()}
 for k in keys:
  v=lower.get(k.lower())
  if v is not None and clean(v):return clean(v)
 return ''
def category(n):
 for terms,c in [('廁所|育嬰|母乳|飲水','生活設施'),('停車場','交通出行'),('回收|垃圾|收集|狗糞','環保回收'),('公園|花園|休憩|植物|生態|古樹|燒烤','公園自然'),('遛狗|狗房|熊貓|動物','動物友善'),('文化|漫步|雕塑|綠化教育','文化探索'),('街市|酒店','商業旅遊'),('WiFi','免費上網')]:
  if re.search(terms,n):return c
 return '公共服務'
def coords(r):
 lat=first(r,['latitude','lat','緯度']);lng=first(r,['longitude','lng','lon','經度'])
 if not lat or not lng:
  v=first(r,['location','locations.location','coordinates','coordinate','GPS'])
  nums=re.findall(r'-?\d+(?:\.\d+)?',v)
  if len(nums)==2:lat,lng=nums
 if not lat or not lng:lat,lng=first(r,['X_coords']),first(r,['Y_coords'])
 try:
  a,b=float(lat),float(lng)
  if 113.4<a<113.7 and 22<b<22.3:a,b=b,a
  if 22.08<=a<=22.25 and 113.48<=b<=113.65:return a,b
 except (ValueError,TypeError):pass
 return None

def walk(v):
 if isinstance(v,dict):
  yield v
  for k,x in v.items():
   if isinstance(x,(list,dict)):yield from walk(x)
 elif isinstance(v,list):
  for x in v:yield from walk(x)

def wifi_rows():
 f=ROOT/'data/wifi.xlsx'
 if not f.exists():return []
 ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
 with zipfile.ZipFile(f) as z:
  ss=[]
  if 'xl/sharedStrings.xml' in z.namelist():
   ss=[''.join(t.itertext()) for t in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',ns)]
  rows=[]
  for row in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('.//m:row',ns):
   out={}
   for c in row.findall('m:c',ns):
    col=re.sub(r'\d','',c.get('r',''));v=c.find('m:v',ns);txt=v.text if v is not None else ''.join(c.find('m:is',ns).itertext()) if c.find('m:is',ns) is not None else ''
    if c.get('t')=='s':txt=ss[int(txt)]
    out[col]=txt
   rows.append(out)
  if not rows:return []
  # The publisher's first row holds machine-readable column names.
  header=rows[0]
  return [{header.get(k,k):v for k,v in row.items()} for row in rows[1:]]

catalog=json.loads((ROOT/'data/catalog.json').read_text());sources=json.loads((ROOT/'data/sources.json').read_text());allpoints=[];layers=[]
for s in sources:
 f=ROOT/'data/raw'/(s['id']+'.json');layer=dict(s,category=category(s['name']),count=0,status='unavailable',note='尚未成功取得資料',retrievedAt=None)
 if not f.exists():layers.append(layer);continue
 d=json.loads(f.read_text());layer['retrievedAt']=d['retrievedAt']
 try:
  if d['type'].upper()=='XML':rows=[dict(e.attrib,**{ch.tag:(ch.text or '') for ch in e}) for e in ET.fromstring(d['body']).iter()]
  else:rows=list(walk(json.loads(d['body'])))
 except Exception as e:layer['note']='資料格式待核對';layers.append(layer);continue
 seen=set();skipped=0
 for r in rows:
  pos=coords(r)
  if not pos:continue
  name=first(r,['nameZh','name_tc','nameTC','NameC','name_zh','name','Name','treeNameTc','nameCN','nameChi','title','titleZh','locationNameTc','treeTypeNameTc'])
  if not name:name=s['name']
  if r.get('oldTreeNo'):name+=' · '+str(r['oldTreeNo'])
  key=(name,round(pos[0],6),round(pos[1],6))
  if key in seen:continue
  seen.add(key)
  p={'id':hashlib.sha1((s['id']+str(key)).encode()).hexdigest()[:14],'layer':s['id'],'name':name,'lat':pos[0],'lng':pos[1],'category':layer['category'],'address':first(r,['addressZh','address_tc','addressTC','LocationC','address_zn','address_zh','locationZh']),'hours':first(r,['openHourZh','serviceHourTC','hour_cn','openingHours']),'tel':first(r,['telZh','ContactNo','tel','telephone']),'description':first(r,['Description_html','descriptionTc','introductionTc','description','remarkZh','remarksZh']),'closed':str(r.get('tempClose','')).lower()=='true','accessible':str(r.get('hasDwc','')).lower()=='true','family':str(r.get('hasFwc','')).lower()=='true'}
  if s['apiId']==6:p['parkingId']=first(r,['CP_ID']);p['price']=first(r,['Lcar_price_C']);p['height']=first(r,['height'])
  if '臨時垃圾' in s['name']:p['notice']='僅在災害應急時設置，並非日常收集點。'
  allpoints.append(p)
 layer['count']=len(seen);layer['status']='ready' if seen else 'needs_review';layer['note']='' if seen else '已取得資料，位置格式待整理';layers.append(layer)
# File-based Wi-Fi source.
w=next(x for x in catalog if 'FreeWiFi.MO' in x['name']);wl={k:w[k] for k in ['id','name','methods','url','dept','frequency']};wl.update(category='免費上網',status='needs_review',count=0,note='檔案位置格式待整理',retrievedAt=datetime.datetime.fromtimestamp((ROOT/'data/wifi.xlsx').stat().st_mtime,datetime.timezone.utc).isoformat())
for r in wifi_rows():
 pos=coords(r)
 if not pos:continue
 name=first(r,['nameTC','nameZh','name','繁中名稱'])
 allpoints.append({'id':'wifi-'+hashlib.sha1((name+str(pos)).encode()).hexdigest()[:12],'layer':w['id'],'name':name or 'FreeWiFi.MO','lat':pos[0],'lng':pos[1],'category':'免費上網','address':first(r,['addressTC','繁中地址']),'hours':first(r,['serviceHourTC','繁中服務時間']),'tel':'','description':'Wi-Fi 名稱：'+first(r,['SSID']),'closed':False,'accessible':False,'family':False})
 wl['count']+=1
if wl['count']:wl['status']='ready';wl['note']=''
layers.append(wl)
# Merge duplicate toilet overlays: preserve every source on the point.
merged={};result=[]
for p in allpoints:
 key=(p['name'].strip(),round(p['lat'],5),round(p['lng'],5))
 if key in merged:
  old=merged[key];old['layers'].append(p['layer']);old['accessible']|=p['accessible'];old['family']|=p['family'];continue
 p['layers']=[p['layer']];merged[key]=p;result.append(p)
output={'generatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'layers':layers,'points':result,'catalog':catalog,'sourceLabel':'澳門特別行政區政府數據開放平台'}
(ROOT/'data/site-data.json').write_text(json.dumps(output,ensure_ascii=False,separators=(',',':')))
print('POINTS',len(result),'LAYERS',len(layers),'READY',sum(x['status']=='ready' for x in layers));print([(x['name'],x['count'],x['status']) for x in layers])
