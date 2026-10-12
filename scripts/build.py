import pathlib,json,re
r=pathlib.Path(__file__).resolve().parents[1]
s=(r/'template.html').read_text()
data_path=r/'data/site-data.json'
data=data_path.read_text() if data_path.exists() else re.search(r'<script id="dataset" type="application/json">(.*?)</script>',(r/'index.html').read_text(),re.S).group(1)
for token,value in {'/*VENDOR_CSS*/':(r/'vendor/leaflet.css').read_text()+'\n'+(r/'vendor/cluster.css').read_text(),'/*APP_CSS*/':(r/'app.css').read_text(),'/*DATA*/':data.replace('<','\\u003c'),'/*VENDOR_JS*/':(r/'vendor/leaflet.js').read_text()+'\n'+(r/'vendor/cluster.js').read_text(),'/*APP_JS*/':(r/'app.js').read_text()}.items():s=s.replace(token,value)
(r/'index.html').write_text(s)
print('Built',len(s.encode()),'bytes')
