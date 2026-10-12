const D=JSON.parse(document.getElementById('dataset').textContent),$=id=>document.getElementById(id),layers=new Map(D.layers.map(l=>[l.id,l]));
const colors={'生活設施':'#16877b','交通出行':'#4178b4','環保回收':'#729237','公園自然':'#287440','動物友善':'#a17846','文化探索':'#a65e53','商業旅遊':'#7c67a2','免費上網':'#3b99b3','公共服務':'#777e86'};
let category='',source='',query='',visible=[],limit=60,origin=null,page=0,selected=null,locationMarker=null,searchTimer=null,locating=false,routeId='';
function el(tag,txt,cls){const e=document.createElement(tag);if(txt!=null)e.textContent=txt;if(cls)e.className=cls;return e}
function date(x){return x?x.slice(0,10):'未提供'}
function link(text,url){const a=el('a',text);if(/^https:\/\//.test(url)){a.href=url;a.target='_blank';a.rel='noopener noreferrer'}return a}
function badge(t){return el('span',t,'badge')}
function normalize(value){return String(value||'').normalize('NFKC').toLowerCase().replace(/\s+/g,' ').trim()}
const BUS_ID='e7b2e84d-3333-42f0-b676-64ce95306f0d',busRoutes=new Map((D.bus?.routes||[]).map(r=>[r.id,r])),pointsById=new Map(D.points.map(p=>[p.id,p]));
const searchText=new Map(D.points.map(p=>[p.id,normalize([p.name,p.address,p.category,p.busStopCode,p.busStationCode,p.busRoutes?.join(' '),p.namePor,...p.layers.map(id=>layers.get(id)?.name)].join(' '))]));
const map=L.map('map',{zoomControl:true}).setView([22.164,113.559],12);let tiles;
if(location.protocol!=='file:'){tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);tiles.on('tileerror',()=>{$('mapnote').textContent='底圖暫未載入；地點搜尋仍可使用。'})}else $('mapnote').textContent='離線預覽：地點可搜尋；正式發佈後載入 OpenStreetMap 底圖。';
const group=L.markerClusterGroup({showCoverageOnHover:false,chunkedLoading:false,maxClusterRadius:48,iconCreateFunction:c=>L.divIcon({html:String(c.getChildCount()),className:'cluster',iconSize:[42,42]})}).addTo(map);
const markers=new Map(),routeLines=L.featureGroup().addTo(map);
for(const r of [...busRoutes.values()].sort((a,b)=>a.number.localeCompare(b.number,'en',{numeric:true})||a.direction.localeCompare(b.direction))){const o=el('option',r.number+' · 方向'+r.direction+' · '+pointsById.get(r.stops[0]).name+' → '+pointsById.get(r.stops.at(-1)).name);o.value=r.id;$('busRoute').append(o)}
$('busRoute').onchange=()=>{routeId=$('busRoute').value;closeDetail();applyFilters();const bounds=routeLines.getBounds?.();if(bounds?.isValid())map.fitBounds(bounds,{padding:[25,25]})};
$('busStops').onclick=showRouteStops;
function syncFilters(){
 for(const b of $('chips').children){const active=b.dataset.cat===category;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active))}
 $('layer').replaceChildren();const all=el('option',category?'此分類全部資料':'全部分類的資料');all.value='';$('layer').append(all);
 for(const l of D.layers.filter(l=>l.status==='ready'&&(!category||l.category===category))){const o=el('option',l.name+' · '+l.count);o.value=l.id;$('layer').append(o)}
 $('layer').value=source;$('search').value=query;
 $('busTools').hidden=source!==BUS_ID;const route=busRoutes.get(routeId);$('busRoute').value=routeId;$('busStops').hidden=!route;
 $('busRouteNote').textContent=route?route.stops.length+' 站 · '+route.company:'選擇路線可看走向及站序；非即時報站。';
 $('search').placeholder=source?'在「'+layers.get(source).name+'」搜尋…':category?'在「'+category+'」搜尋名稱或地址…':'搜尋全部地點名稱或地址…';
 const active=Boolean(category||source||query||routeId);$('clearFilters').disabled=!active;
 $('filterSummary').textContent=active?'目前範圍：'+[category||'全部分類',source?layers.get(source).name:'全部資料',route?route.number+'（方向'+route.direction+'）':'',query?'「'+query+'」':''].filter(Boolean).join(' › '):'分類、資料圖層及關鍵字可逐層收窄結果。';
}
function applyFilters(){clearTimeout(searchTimer);query=$('search').value.trim();syncFilters();render()}
function clearFilters(){closeDetail();category='';source='';query='';routeId='';clearTimeout(searchTimer);syncFilters();render()}
function setCategory(c){category=c;source='';routeId='';closeDetail();applyFilters()}
for(const c of ['',...Object.keys(colors)]){const b=el('button',c||'全部');b.dataset.cat=c;b.onclick=()=>setCategory(c);$('chips').append(b)}
function distance(p){if(!origin)return 0;const rad=Math.PI/180,a=(p.lat-origin.lat)*rad,b=(p.lng-origin.lng)*rad,h=Math.sin(a/2)**2+Math.cos(origin.lat*rad)*Math.cos(p.lat*rad)*Math.sin(b/2)**2;return 6371000*2*Math.asin(Math.sqrt(Math.min(1,Math.max(0,h))))}
function render(){
 const terms=normalize(query).split(' ').filter(Boolean),route=busRoutes.get(routeId),routeStops=route?new Set(route.stops):null;
 routeLines.clearLayers();
 if(route){const lines=route.segments.flatMap(id=>D.bus.networks[id]);L.polyline(lines,{color:'#d35420',weight:5,opacity:.85}).addTo(routeLines)}
 visible=D.points.filter(p=>(!category||p.layers.some(id=>layers.get(id)?.category===category))&&(!source||p.layers.includes(source))&&(!routeStops||routeStops.has(p.id))&&terms.every(term=>/^\d+[a-z]*$/i.test(term)&&p.busRoutes?p.busRoutes.some(r=>normalize(r)===term):/^[mtc]\d+(?:_\d+)?$/i.test(term)&&p.busStopCode?[p.busStopCode,p.busStationCode].some(c=>normalize(c)===term):searchText.get(p.id).includes(term)));
 if(origin)visible.sort((a,b)=>distance(a)-distance(b));
 group.clearLayers();const current=[];
 for(const p of visible){let m=markers.get(p.id);if(!m){m=L.marker([p.lat,p.lng],{icon:L.divIcon({html:'<span class="dot" style="background:'+colors[p.category]+'"></span>',className:'',iconSize:[15,15]}),title:p.name});m.on('click',()=>detail(p));markers.set(p.id,m)}current.push(m)}
 group.addLayers(current);
 if(selected&&!visible.some(p=>p.id===selected.id))closeDetail();
 $('count').textContent=visible.length.toLocaleString()+' 個地點';$('sortlabel').textContent=origin?'按直線距離排序':'按資料目錄排序';limit=60;renderList();
}
function renderList(){
 $('results').replaceChildren();
 for(const p of visible.slice(0,limit)){const b=el('button',null,'result');b.append(badge(p.category),badge([...new Set(p.layers.map(id=>layers.get(id)?.methods))].join(' / ')),el('strong',p.name),el('small',p.address||'查看位置與政府資料'));if(origin)b.append(el('small','距離約 '+(distance(p)/1000).toFixed(2)+' 公里（直線）'));b.onclick=()=>{map.setView([p.lat,p.lng],17);detail(p)};$('results').append(b)}
 if(!visible.length){const box=el('div',null,'empty');box.append(el('p','目前篩選範圍內沒有符合的地點。可刪減關鍵字，或清除篩選查看全部。'));const b=el('button','清除篩選');b.onclick=clearFilters;box.append(b);$('results').append(box)}
 if(visible.length>limit){const b=el('button','載入更多地點','result');b.onclick=()=>{limit+=60;renderList()};$('results').append(b)}
}
function detail(p){selected=p;$('detail').hidden=false;$('detailContent').replaceChildren();const root=$('detailContent');root.append(badge(p.category),el('h2',p.name));if(p.closed)root.append(el('p','資料標示：暫停開放','warning'));if(p.notice)root.append(el('p',p.notice,'warning'));const dl=el('dl');for(const [k,v] of [['地址',p.address],['開放時間',p.hours],['電話',p.tel],['設施',[p.accessible?'無障礙設施':'',p.family?'親子設施':''].filter(Boolean).join('、')],['說明',p.description],['輕型車收費',p.price]])if(v){dl.append(el('dt',k),el('dd',v))}root.append(dl);if(p.busRoutes){root.append(el('h3','途經路線'));const buttons=el('div',null,'busRouteButtons');for(const n of p.busRoutes){const b=el('button',n);b.onclick=()=>{const r=[...busRoutes.values()].find(r=>r.number===n&&r.stops.includes(p.id));if(r)showBusRoute(r.id)};buttons.append(b)}root.append(buttons);root.append(el('p','靜態資料，未提供即時到站時間；臨時改道以交通事務局公布為準。','source'))}const a=link('用 Google Maps 開啟導航','https://www.google.com/maps/dir/?api=1&destination='+p.lat+','+p.lng);a.className='primary';root.append(a);for(const id of p.layers){const l=layers.get(id),s=el('div',null,'source');if(l.sourceUpdatedAt)s.append(el('div','官方資料更新：'+date(l.sourceUpdatedAt)));s.append(badge(l.methods),link(l.name,l.url),el('div',l.dept),el('div','資料取得：'+date(l.retrievedAt)+' · 更新頻率：'+l.frequency));root.append(s)}root.append(el('p','來源：'+D.sourceLabel+'。設施狀況以主管部門公布為準。','source'))}
function showBusRoute(id){category='交通出行';source=BUS_ID;query='';routeId=id;clearTimeout(searchTimer);syncFilters();render();showRouteStops()}
function showRouteStops(){const r=busRoutes.get(routeId);if(!r)return;selected=null;$('detail').hidden=false;const root=$('detailContent');root.replaceChildren();root.append(badge('巴士路線'),el('h2',r.number+' · 方向'+r.direction),el('p',r.name),el('p',r.company),el('p',r.remarks),el('p','資料更新：'+date(D.bus.sourceUpdatedAt)+' · 非即時報站','source'));const list=el('ol',null,'busStopSequence');for(const id of r.stops){const p=pointsById.get(id),li=el('li'),b=el('button',p.busStopCode+' · '+p.name);b.onclick=()=>{map.setView([p.lat,p.lng],17);detail(p)};li.append(b);list.append(li)}root.append(list,link('官方巴士報站','https://bis.dsat.gov.mo/macauweb/index.html'));}
function closeDetail(){selected=null;$('detail').hidden=true}
$('close').onclick=closeDetail;document.addEventListener('keydown',e=>{if(e.key==='Escape')closeDetail()});
$('search').oninput=()=>{clearTimeout(searchTimer);searchTimer=setTimeout(applyFilters,160)};
$('search').addEventListener('search',applyFilters);
$('layer').onchange=e=>{source=e.target.value;routeId='';closeDetail();applyFilters()};$('clearFilters').onclick=clearFilters;
$('reset').onclick=()=>map.fitBounds([[22.108,113.523],[22.221,113.599]]);
$('locate').onclick=()=>{
 if(locating)return;
 if(origin){origin=null;if(locationMarker){map.removeLayer(locationMarker);locationMarker=null}$('locate').textContent='◎ 我的附近';$('locate').setAttribute('aria-pressed','false');render();$('mapnote').textContent='已取消附近排序，保留目前篩選。';return}
 if(!navigator.geolocation){$('mapnote').textContent='此瀏覽器不支援定位。';return}
 locating=true;$('locate').disabled=true;$('locate').textContent='定位中…';
 navigator.geolocation.getCurrentPosition(p=>{locating=false;$('locate').disabled=false;origin={lat:p.coords.latitude,lng:p.coords.longitude};locationMarker=L.circleMarker([origin.lat,origin.lng],{radius:7,color:'#246bcc',fillOpacity:1}).addTo(map);map.setView([origin.lat,origin.lng],15);$('locate').textContent='◎ 取消附近排序';$('locate').setAttribute('aria-pressed','true');render();$('mapnote').textContent='依目前篩選按直線距離排序；位置只在你的瀏覽器使用。'},()=>{locating=false;$('locate').disabled=false;$('locate').textContent='◎ 我的附近';$('mapnote').textContent='未能取得位置。請允許定位，或用名稱搜尋。'},{timeout:10000});
};
function view(v){$('workspace').hidden=v!=='map';$('catalog').hidden=v==='map';$('mapTab').classList.toggle('active',v==='map');$('catalogTab').classList.toggle('active',v!=='map');if(v==='map')setTimeout(()=>map.invalidateSize(),0)}$('mapTab').onclick=()=>view('map');$('catalogTab').onclick=()=>{view('catalog');renderCatalog()};
for(const d of [...new Set(D.catalog.map(c=>c.dept))].sort()){const o=el('option',d);o.value=d;$('dept').append(o)}
function renderCatalog(){const q=normalize($('catSearch').value),dep=$('dept').value,method=$('method').value;const rows=D.catalog.filter(c=>(!q||normalize(c.name+' '+c.description+' '+c.dept).includes(q))&&(!dep||c.dept===dep)&&(!method||c.methods.includes(method)));page=Math.min(page,Math.max(0,Math.ceil(rows.length/40)-1));$('catCount').textContent=rows.length+' 個數據集 · 提供方式可重疊';$('tbody').replaceChildren();for(const c of rows.slice(page*40,(page+1)*40)){const tr=el('tr'),name=el('td'),l=layers.get(c.id);name.append(link(c.name,c.url),el('small',c.frequency+' · '+(c.formats||'')));const methodCell=el('td');methodCell.append(badge(c.methods));const status=el('td');if(l?.status==='ready'){const b=el('button','在地圖查看');b.onclick=()=>{source=c.id;category=l.category;query='';routeId='';clearTimeout(searchTimer);syncFilters();view('map');render()};status.append(b)}else{status.textContent=l?'待整理':'未接入';if(l?.note)status.append(el('small',l.note))}tr.append(name,methodCell,el('td',c.dept),status);$('tbody').append(tr)}$('pageLabel').textContent=(rows.length?page+1:0)+' / '+Math.ceil(rows.length/40);$('prev').disabled=page===0;$('next').disabled=(page+1)*40>=rows.length}
for(const id of ['catSearch','dept','method'])$(id).addEventListener(id==='catSearch'?'input':'change',()=>{page=0;renderCatalog()});$('prev').onclick=()=>{page--;renderCatalog()};$('next').onclick=()=>{page++;renderCatalog()};$('coverage').textContent=D.layers.filter(l=>l.status==='ready').length+' 個已接入圖層 · '+D.catalog.length.toLocaleString()+' 個數據集';$('date').textContent='資料快照 · 取得於 '+date(D.generatedAt);syncFilters();render();
