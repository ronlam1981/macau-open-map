"""Import DSAT's public shapefile/XLS bundle; pip install pyshp pyproj pandas xlrd."""
import argparse,datetime,hashlib,json,pathlib,tempfile,urllib.request,zipfile
import pandas as pd
import shapefile
from pyproj import CRS,Transformer
ROOT=pathlib.Path(__file__).resolve().parents[1]
SOURCE='e7b2e84d-3333-42f0-b676-64ce95306f0d'
a=argparse.ArgumentParser();a.add_argument('--archive');args=a.parse_args()
meta=json.load(urllib.request.urlopen('https://api.data.gov.mo/datadir/detail/'+SOURCE,timeout=30))['data']
file=meta['file'][0]
url='https://api.data.gov.mo/datadir/downloadSingleFile?fileId='+str(file['fileId'])+'&dataDirId='+SOURCE
blob=pathlib.Path(args.archive).read_bytes() if args.archive else urllib.request.urlopen(url,timeout=60).read()
with tempfile.TemporaryDirectory() as tmp:
 z=zipfile.ZipFile(__import__('io').BytesIO(blob));z.extractall(tmp);folder=next(pathlib.Path(tmp).rglob('BUS_POLE.shp')).parent
 crs=CRS.from_wkt((folder/'BUS_POLE.prj').read_text())
 # Publisher's WKT uses legacy names without EPSG identifiers. Verify the
 # projection and ellipsoid before resolving it to Macao 1920 / Macao Grid.
 expected=CRS.from_epsg(8433)
 assert crs.ellipsoid.semi_major_metre==expected.ellipsoid.semi_major_metre
 assert all(abs(x.value-y.value)<1e-6 for x,y in zip(crs.coordinate_operation.params,expected.coordinate_operation.params))
 transform=Transformer.from_crs(8433,4326,always_xy=True,allow_ballpark=False)
 def pos(x,y):
  lon,lat=transform.transform(x,y);assert 22.08<=lat<=22.25 and 113.48<=lon<=113.65
  return [round(lat,6),round(lon,6)]
 d=json.loads((ROOT/'data/site-data.json').read_text())
 d['points']=[p for p in d['points'] if SOURCE not in p['layers']];d['layers']=[l for l in d['layers'] if l['id']!=SOURCE]
 poles={};reader=shapefile.Reader(str(folder/'BUS_POLE'),encoding='utf-8')
 for sr in reader.iterShapeRecords():
  r=sr.record.as_dict();lat,lon=pos(*sr.shape.points[0]);pid='bus-'+str(r['POLE_ID']);routes=[x.strip() for x in r['ROUTE_NOS'].split(',') if x.strip()]
  p={'id':pid,'name':r['P_NAME'],'lat':lat,'lng':lon,'category':'交通出行','layers':[SOURCE],'layer':SOURCE,'address':'站號：'+r['P_ALIAS'],'hours':'','tel':'','description':'途經路線：'+', '.join(routes),'closed':False,'accessible':False,'family':False,'busStopCode':r['P_ALIAS'],'busStationCode':r['ALIAS'],'busPoleId':r['POLE_ID'],'busRoutes':routes,'namePor':r['P_NAME_POR']}
  poles[r['POLE_ID']]=p;d['points'].append(p)
 networks={};reader=shapefile.Reader(str(folder/'ROUTE_NETWORK'),encoding='utf-8')
 for sr in reader.iterShapeRecords():
  r=sr.record.as_dict();bounds=list(sr.shape.parts)+[len(sr.shape.points)]
  networks[str(r['NETWORK_ID'])]=[[pos(*xy) for xy in sr.shape.points[start:end]] for start,end in zip(bounds,bounds[1:])]
 table=pd.read_excel(folder/'BUS_ROUTE_SEQ.xls');routes=[]
 for (number,rid,direction),g in table.groupby(['ROUTE_NO','ROUTE_ID','DIRECTION'],sort=False):
  g=g.sort_values('SEQ');stops=[poles[int(v)]['id'] for v in g.POLE_ID.dropna()];segments=[str(int(v)) for v in g.NETWORK_ID.dropna()]
  assert all(s in networks for s in segments)
  r=g.iloc[0];routes.append({'id':str(rid),'number':str(number),'direction':str(direction),'name':str(r.NAME),'company':str(r.COMPANY_NAME),'remarks':'' if pd.isna(r.REMARKS) else str(r.REMARKS),'stops':stops,'segments':segments})
 now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 d['bus']={'routes':routes,'networks':networks,'retrievedAt':now,'sourceUpdatedAt':meta['info']['updateTime'],'archiveName':z.namelist()[0].split('/')[0],'archiveSha256':hashlib.sha256(blob).hexdigest(),'sourceCrs':'EPSG:8433','targetCrs':'EPSG:4326','transformAccuracyMetres':transform.accuracy}
 c=next(c for c in d['catalog'] if c['id']==SOURCE);c.update(updated=meta['info']['updateTime'],note='已接入巴士站位置、途經路線、方向及站序；路線走向來自官方地理線段。')
 d['layers'].append({'id':SOURCE,'name':'巴士站及巴士路線','category':'交通出行','methods':'檔案','url':c['url'],'dept':'交通事務局','frequency':'按需要','count':len(poles),'status':'ready','note':'','retrievedAt':now,'sourceUpdatedAt':meta['info']['updateTime']})
 (ROOT/'data/site-data.json').write_text(json.dumps(d,ensure_ascii=False,separators=(',',':')))
 print(json.dumps({'stops':len(poles),'routeNumbers':len(set(r['number'] for r in routes)),'directions':len(routes),'segments':len(networks),'updated':meta['info']['updateTime'],'accuracyMetres':transform.accuracy},ensure_ascii=False))
