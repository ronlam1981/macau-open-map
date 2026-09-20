import pathlib,json
r=pathlib.Path(__file__).resolve().parents[1]
s=(r/'template.html').read_text()
for token,value in {'/*VENDOR_CSS*/':(r/'vendor/leaflet.css').read_text()+'\n'+(r/'vendor/cluster.css').read_text(),'/*APP_CSS*/':(r/'app.css').read_text(),'/*DATA*/':(r/'data/site-data.json').read_text().replace('<','\\u003c'),'/*VENDOR_JS*/':(r/'vendor/leaflet.js').read_text()+'\n'+(r/'vendor/cluster.js').read_text(),'/*APP_JS*/':(r/'app.js').read_text()}.items():s=s.replace(token,value)
(r/'public/index.html').write_text(s)
print('Built',len(s.encode()),'bytes')
