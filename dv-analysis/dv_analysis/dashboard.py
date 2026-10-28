import datetime, json

HTML = r"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Telemetria do Mapeamento · DV</title>
<style>
:root{--bg:#f4f5f7;--card:#fff;--tx:#14171c;--mu:#6b7280;--ln:#e3e6ea;--ok:#1b7f4d;--open:#a15c00;--bad:#b42318}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:14px/1.45 Inter,system-ui,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:28px 18px 60px}
.eyebrow{font:600 11px ui-monospace,monospace;letter-spacing:.08em;color:var(--mu)}
h1{margin:6px 0 4px;font-size:30px}h2{margin:34px 0 12px;font-size:19px}
.sub{color:var(--mu);max-width:820px}
.cols{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}@media(max-width:800px){.cols{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--ln);border-radius:12px;padding:16px;overflow:auto}
.card h3{margin:0 0 10px;font-size:15px;display:flex;gap:8px;align-items:center}
.tag{font:700 10px ui-monospace,monospace;padding:2px 7px;border-radius:99px;border:1px solid}
.tag.ok{color:var(--ok);border-color:var(--ok)}.tag.open{color:var(--open);border-color:var(--open)}
.item{padding:10px 0;border-top:1px solid var(--ln)}.item:first-of-type{border-top:0}
.item b{display:block}.item p{margin:2px 0 4px;color:#3b4350;font-size:13px}.item code{font:11px ui-monospace,monospace;color:var(--mu)}
table{border-collapse:collapse;width:100%;font-size:13px}th{font:600 10px ui-monospace,monospace;color:var(--mu);text-align:right;padding:6px 8px;letter-spacing:.04em}
td{padding:7px 8px;text-align:right;border-top:1px solid var(--ln);font-variant-numeric:tabular-nums}th:first-child,td:first-child{text-align:left}
.leg{display:flex;gap:14px;flex-wrap:wrap;color:var(--mu);font-size:12px;margin-top:6px}.leg i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px}
.pills{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 14px}.pills button{border:1px solid var(--ln);background:#fff;border-radius:99px;padding:5px 12px;cursor:pointer;font-size:12px}
.pills button.on{background:var(--tx);color:#fff;border-color:var(--tx)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px;margin-top:10px}
.kpis small{display:block;font:600 10px ui-monospace,monospace;color:var(--mu)}.kpis b{font-size:17px}
.grid2{display:grid;grid-template-columns:1.4fr 1fr;gap:14px}@media(max-width:900px){.grid2{grid-template-columns:1fr}}
svg text{font:10px ui-monospace,monospace;fill:#6b7280}.foot{color:var(--mu);font-size:12px;margin-top:30px}
</style></head><body><div class="wrap">
<div class="eyebrow">UNICAMP E-RACING · DRIVERLESS · MAPEAMENTO</div>
<h1>Telemetria do Mapeamento</h1>
<p class="sub" id="sub"></p>
<div class="cols"><div class="card"><h3><span class="tag ok">VALIDADO</span> Funciona</h3><div id="okl"></div></div>
<div class="card"><h3><span class="tag open">EM ABERTO</span> Precisa de atenção</h3><div id="openl"></div></div></div>
<h2>Resumo por sessão</h2><div class="card"><table id="tbl"></table></div>
<h2>Volta a volta</h2><div class="cols">
<div class="card"><h3>Tempo de volta</h3><div id="c_lap"></div><div class="leg" id="l_lap"></div></div>
<div class="card"><h3>Latência da percepção e do mapeamento (ms)</h3><div id="c_lat"></div><div class="leg"><span><i style="background:#2979d6"></i>p50</span><span><i style="background:#e8590c"></i>p95</span></div></div></div>
<h2>Explorar uma sessão</h2><div class="pills" id="pills"></div>
<div class="grid2"><div class="card"><h3>Mapa · <span id="mname"></span></h3><div id="c_map"></div>
<div class="leg"><span>○ referência</span><span><i style="background:#d9a400"></i>amarelo</span><span><i style="background:#1c6dd0"></i>azul</span><span style="color:#b42318">✕ fantasma</span><span>— trajetória</span></div></div>
<div class="card"><h3>Velocidade e steering</h3><div id="c_st"></div><div class="leg"><span><i style="background:#2979d6"></i>comando</span><span><i style="background:#e8590c"></i>real</span><span><i style="background:#1baa7a"></i>velocidade (m/s)</span></div><div class="kpis" id="kpi"></div></div></div>
<p class="foot" id="foot"></p></div>
<script>
const D=__DATA__;const $=s=>document.querySelector(s);
const COL={0:'#8b93a1',1:'#d9a400',2:'#1c6dd0',3:'#ff8a3d',4:'#ff5a1f'},PAL=['#1baa7a','#2979d6','#e8590c','#7c4dd6','#c2185b','#00838f'];
const f=(x,d=1)=>x==null?'—':Number(x).toFixed(d),pc=x=>x==null?'—':Math.round(x*100)+'%';
function line(series,w=520,h=210){const P={l:38,r:8,t:8,b:20};let xs=[],ys=[];
 series.forEach(s=>s.x.forEach((x,i)=>{if(s.y[i]!=null){xs.push(x);ys.push(s.y[i])}}));
 if(!xs.length)return'<p class="sub">sem dados</p>';
 const x0=Math.min(...xs),x1=Math.max(...xs),y0=Math.min(0,...ys),y1=Math.max(...ys)||1;
 const X=x=>P.l+(x-x0)/((x1-x0)||1)*(w-P.l-P.r),Y=y=>h-P.b-(y-y0)/((y1-y0)||1)*(h-P.t-P.b);
 let g='';for(let i=0;i<=4;i++){const v=y0+(y1-y0)*i/4;g+=`<line x1="${P.l}" x2="${w-P.r}" y1="${Y(v)}" y2="${Y(v)}" stroke="#e3e6ea"/><text x="${P.l-4}" y="${Y(v)+3}" text-anchor="end">${v.toFixed(v<10?1:0)}</text>`}
 g+=`<text x="${P.l}" y="${h-4}">${x0.toFixed(0)}</text><text x="${w-P.r}" y="${h-4}" text-anchor="end">${x1.toFixed(0)}</text>`;
 series.forEach(s=>{let d='',pen=false;s.x.forEach((x,i)=>{if(s.y[i]==null){pen=false;return}d+=(pen?'L':'M')+X(x).toFixed(1)+' '+Y(s.y[i]).toFixed(1);pen=true});
  g+=`<path d="${d}" fill="none" stroke="${s.c}" stroke-width="1.6"/>`;if(s.dots)s.x.forEach((x,i)=>g+=`<circle cx="${X(x)}" cy="${Y(s.y[i])}" r="3" fill="${s.c}"/>`)});
 return`<svg viewBox="0 0 ${w} ${h}" width="100%">${g}</svg>`}
function bars(w=520,h=210){const P={l:38,r:8,t:8,b:34},S=D.sessions;const mx=Math.max(1,...S.flatMap(s=>[s.perc_lat?.p95||0,s.map_lat?.p95||0]));
 const bw=(w-P.l-P.r)/S.length;let g='';
 S.forEach((s,i)=>{const x=P.l+i*bw;[['perc',s.perc_lat],['map',s.map_lat]].forEach(([k,L],j)=>{if(!L)return;
  [['p50','#2979d6'],['p95','#e8590c']].forEach(([q,c],m)=>{const v=L[q],hh=v/mx*(h-P.t-P.b);const bx=x+4+j*bw*.45+m*bw*.2;
   g+=`<rect x="${bx}" y="${h-P.b-hh}" width="${bw*.18}" height="${hh}" fill="${c}" opacity="${k=='perc'?1:.55}"/>`})});
  g+=`<text x="${x+bw/2}" y="${h-20}" text-anchor="middle">${s.name.slice(-9)}</text><text x="${x+4}" y="${h-8}">perc</text><text x="${x+bw*.5}" y="${h-8}">map</text>`;
  if(!s.perc_lat)g+=`<text x="${x+4}" y="${P.t+10}" fill="#a15c00">perc não medida</text>`});
 g+=`<text x="2" y="${P.t+8}">${mx.toFixed(0)}</text>`;return`<svg viewBox="0 0 ${w} ${h}" width="100%">${g}</svg>`}
function mapsvg(s,w=640,h=520){const pts=[...s.ref,...s.built,...s.traj];if(!pts.length)return'';
 const xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]),x0=Math.min(...xs),x1=Math.max(...xs),y0=Math.min(...ys),y1=Math.max(...ys),pad=24;
 const k=Math.min((w-2*pad)/((x1-x0)||1),(h-2*pad)/((y1-y0)||1)),X=x=>pad+(x-x0)*k+((w-2*pad)-(x1-x0)*k)/2,Y=y=>h-pad-(y-y0)*k-((h-2*pad)-(y1-y0)*k)/2;
 let g=`<path d="${s.traj.map((p,i)=>(i?'L':'M')+X(p[0]).toFixed(1)+' '+Y(p[1]).toFixed(1)).join('')}" fill="none" stroke="#7c4dd6" stroke-opacity=".5" stroke-width="1.5"/>`;
 s.ref.forEach(c=>g+=`<circle cx="${X(c[0])}" cy="${Y(c[1])}" r="6" fill="none" stroke="#8b93a1"/>`);
 s.built.forEach(c=>g+=`<circle cx="${X(c[0])}" cy="${Y(c[1])}" r="3.5" fill="${COL[c[2]]||COL[0]}"/>`);
 s.ghosts.forEach(c=>g+=`<path d="M${X(c[0])-3} ${Y(c[1])-3}l6 6m0-6l-6 6" stroke="#b42318" stroke-width="1.2"/>`);
 return`<svg viewBox="0 0 ${w} ${h}" width="100%">${g}</svg>`}
// cabeçalho
$('#sub').textContent=`${D.sessions.length} sessão(ões) analisadas · mapa montado a partir das coordenadas da percepção + pose (latência assumida ${D.params.latency*1000} ms, confirmação com ${D.params.confirm} detecções).`;
$('#foot').textContent=`Gerado em ${D.generated}. Regere com: python3 dv-analysis/plotmap.py sessions/*.jsonl. A referência é o ground truth quando existe (simulador); em carro real é o mapa publicado pelo mapeamento, então as métricas medem a consistência percepção × mapeamento, não o erro absoluto.`;
// validado / em aberto
const grp={};D.sessions.forEach(s=>s.findings.forEach(x=>{(grp[x.title]??={body:x.body,items:[]}).items.push({n:s.name,...x})}));
const okh=[],oph=[];Object.entries(grp).forEach(([t,g])=>{const bad=g.items.filter(i=>i.status!='ok'),pick=bad[0]||g.items[0];
 const h=`<div class="item"><b>${t}</b><p>${g.body}</p><code>${pick.metric}${bad.length?` · ${bad.length}/${g.items.length} sessões`:''}${D.sessions.length>1?` · ${pick.n}`:''}</code></div>`;(bad.length?oph:okh).push(h)});
$('#okl').innerHTML=okh.join('')||'<p class="sub">nada ainda</p>';$('#openl').innerHTML=oph.join('')||'<p class="sub">nenhum alerta</p>';
// tabela
const hd=['SESSÃO','DURAÇÃO','VOLTAS','VOLTA 1','MELHOR','MEDIANA 2+','VEL. MÉD','CONES/FRAME','PRECISÃO','RECALL','RMSE V1','RMSE FINAL','FANTASMAS','RMS STEER'];
$('#tbl').innerHTML='<tr>'+hd.map(h=>`<th>${h}</th>`).join('')+'</tr>'+D.sessions.map(s=>`<tr><td>${s.name}</td><td>${f(s.duration,0)} s</td><td>${s.lap_times.length}</td><td>${f(s.lap1)} s</td><td>${f(s.best_lap)} s</td><td>${f(s.median_2plus)} s</td><td>${f(s.speed_mean)} m/s</td><td>${f(s.cones_per_frame)}</td><td>${pc(s.map_final.precision)}</td><td>${pc(s.map_final.recall)}</td><td>${f(s.map_v1.rmse,2)} m</td><td>${f(s.map_final.rmse,2)} m</td><td>${s.n_ghost}</td><td>${s.steer?f(s.steer.rms_err,2)+'°':'—'}</td></tr>`).join('');
// gráficos
$('#c_lap').innerHTML=line(D.sessions.map((s,i)=>({c:PAL[i%6],x:s.lap_times.map((_,j)=>j+1),y:s.lap_times,dots:1})));
$('#l_lap').innerHTML=D.sessions.map((s,i)=>`<span><i style="background:${PAL[i%6]}"></i>${s.name}</span>`).join('');
$('#c_lat').innerHTML=bars();
// explorador
let cur=0;function show(){const s=D.sessions[cur];$('#mname').textContent=s.name;$('#c_map').innerHTML=mapsvg(s);
 $('#c_st').innerHTML=line([{c:'#2979d6',x:s.series.t,y:s.series.cmd},{c:'#e8590c',x:s.series.t,y:s.series.angle},{c:'#1baa7a',x:s.series.t,y:s.series.speed}]);
 const k=[['ESTADO',s.as_state],['VOLTAS',s.lap_times.length],['VOLTA 1',f(s.lap1)+' s'],['MELHOR',f(s.best_lap)+' s'],['CONES CONFIRMADOS',s.n_confirmed],['FANTASMAS',s.n_ghost],['PRECISÃO',pc(s.map_final.precision)],['RECALL',pc(s.map_final.recall)],['COR',pc(s.map_final.color_acc)],['ERRO STEER',s.steer?f(s.steer.rms_err,2)+'°':'—'],['CORRENTE MÁX',s.steer?f(s.steer.max_current)+' A':'—'],['TEMP MÁX',s.steer?f(s.steer.max_temp,0)+' °C':'—']];
 $('#kpi').innerHTML=k.map(([a,b])=>`<div><small>${a}</small><b>${b}</b></div>`).join('');
 document.querySelectorAll('#pills button').forEach((b,i)=>b.classList.toggle('on',i==cur))}
$('#pills').innerHTML=D.sessions.map((s,i)=>`<button>${s.name}</button>`).join('');
document.querySelectorAll('#pills button').forEach((b,i)=>b.onclick=()=>{cur=i;show()});show();
</script></body></html>"""


def render(sessions, params):
    data = dict(sessions=sessions, params=params, generated=datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))
    return HTML.replace("__DATA__", json.dumps(data).replace("</", "<\\/"))
