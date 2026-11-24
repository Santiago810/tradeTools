const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];
const escape = v => String(v ?? '').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function stored(key, fallback) { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } }
function persist(key,value) { try { localStorage.setItem(key,JSON.stringify(value)); } catch { toast('浏览器无法保存设置'); } }
const state = { page:'market', days:40, mode:stored('guanshi-mode','live'), category:'industry', sectorProvider:'auto', assetKind:'index', catalog:[], selected:{code:'000300',name:'沪深300',kind:'index'}, watch:stored('guanshi-watch',[]), chartMetric:'amount', marginMetric:'total', request:0, latest:null, exportTarget:'market', compare:'', sectorItems:[] };
if (!['live','demo'].includes(state.mode)) state.mode='live';
if (!Array.isArray(state.watch)) state.watch=[];
$('#mode').value=state.mode;
const titles={market:['市场总览','把握市场温度，观察资金流向，让每一次决策更有依据。'],sectors:['板块观察','从行业到主题，发现市场中的活跃方向。'],assets:['指数与 ETF','聚焦你关注的资产，观察价格与成交的变化。'],watchlist:['我的自选','把关心的指数与 ETF，放在一起持续观察。']};
const num=(v,d=2)=>v===null||v===undefined||!Number.isFinite(Number(v))?'—':Number(v).toLocaleString('zh-CN',{minimumFractionDigits:d,maximumFractionDigits:d});
const pct=v=>v===null||v===undefined?'—':`${v>=0?'+':''}${num(v)}%`;
const color=v=>v>0?'up':v<0?'down':'neutral';
const money=v=>v===null||v===undefined?'—':num(v/1e8);
function toast(message){$('#toast').textContent=message;$('#toast').hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('#toast').hidden=true,3000);}
function source(result){const m=result?.meta;if(!m)return '';return `<div class="source">${escape(m.source)}${m.fetched_at?` · 获取时间 ${escape(m.fetched_at.replace('T',' ').slice(0,19))}`:''}${m.stale?' · 缓存已过期，请勿视作最新行情':''}${m.mode==='demo'?' · 合成数据':''}${m.warning?`<br><span class="${m.data_delayed?'up':''}">${escape(m.warning)}</span>`:''}</div>`;}
function unavailable(result,label='行情'){return `<div class="empty"><span style="font-size:30px;color:#b7c1d6">⌁</span><strong>${escape(label)}暂不可用</strong><p>${escape(result?.meta?.warning||'请稍后重试')}</p><p>${escape(result?.meta?.error||'')}</p><button class="button retry">↻ 重新查询</button></div>`;}
function loading(){return '<div class="loading"><span class="spinner"></span> 正在获取行情数据…</div>';}
function panel(title,body,actions='',sub=''){return `<section class="panel"><div class="panel-head"><div><h2>${title}</h2>${sub?`<div class="panel-sub">${sub}</div>`:''}</div>${actions}</div>${body}</section>`;}
async function api(path,params={}){const query=new URLSearchParams({mode:state.mode,days:state.days,...params});const res=await fetch(`/api/${path}?${query}`,{signal:AbortSignal.timeout(55000)});if(!res.ok)throw new Error(`请求失败 (${res.status})`);return res.json();}
function notice(){const el=$('#notice');el.hidden=state.mode!=='demo';el.textContent='演示模式 · 在线查询区域展示合成示例，日期仅按工作日生成，不能用于投资决策。切换「真实行情」可查询公开数据源。';}
function dateLabel(result){const rows=result?.data?.rows;$('#asof').textContent=rows?.length?`截至 ${rows.at(-1).date} · ${rows.length} 个交易日${result.meta?.mode==='demo'?'（演示）':''}`:'以各模块数据日期为准';}
function marginCoverage(data){const c=data?.coverage;if(!c)return '';return `<p class="inline-help">${escape(c.start)} 至 ${escape(c.end)} · 已有 ${c.available} / ${c.sessions} 个交易日${c.missing?` · 缺失 ${c.missing} 日`:' · 数据齐全'}。${escape(c.calendar_basis)}。${data.missing_dates?.length?`<br>缺失日期：${data.missing_dates.map(escape).join('、')}`:''}</p>`;}
function stat(label,value,unit,bottom,icon='⌁'){return `<article class="stat"><div class="stat-top">${label}<span class="stat-icon">${icon}</span></div><div class="stat-value">${value}<small>${unit}</small></div><div class="stat-bottom">${bottom}</div></article>`;}
function metrics(rows){if(!rows?.length)return {};const first=rows[0].close,last=rows.at(-1).close,prev=rows.at(-2)?.close??last;let peak=first,dd=0;for(const r of rows){peak=Math.max(peak,r.close);dd=Math.min(dd,(r.close/peak-1)*100);}return {return:(last/first-1)*100,change:(last/prev-1)*100,close:last,drawdown:dd};}
function chart(container,rows,series,{bar=false,percent=false,unit='',formatter=null}={}){
  if(!rows?.length){container.innerHTML='<div class="empty">暂无趋势数据</div>';return;}
  const width=900,height=255,pad={l:59,r:18,t:20,b:31},iw=width-pad.l-pad.r,ih=height-pad.t-pad.b;
  const all=series.flatMap(s=>rows.map((r,i)=>s.value(r,i)).filter(Number.isFinite));
  if(!all.length){container.innerHTML='<div class="empty">该数据源未提供此指标</div>';return;}
  let low=bar?0:Math.min(...all),high=Math.max(...all);const delta=high-low||Math.abs(high)*.01||1;if(!bar)low-=delta*.15;high+=delta*.18;
  const x=i=>pad.l+(rows.length===1?iw/2:i*iw/(rows.length-1)),y=v=>pad.t+(high-v)/(high-low)*ih;
  const format=formatter || (v=>`${num(v,Math.abs(high)>100?0:2)}${percent?'%':''}`);
  let svg=`<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escape(series.map(s=>s.label).join('、'))}趋势图"><defs><linearGradient id="fill-${container.id}" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="${series[0].color}" stop-opacity=".17"/><stop offset="100%" stop-color="${series[0].color}" stop-opacity=".01"/></linearGradient></defs>`;
  for(let j=0;j<5;j++){const v=low+(high-low)*j/4;svg+=`<line class="grid" x1="${pad.l}" y1="${y(v)}" x2="${width-pad.r}" y2="${y(v)}"/><text x="${pad.l-10}" y="${y(v)+3}" text-anchor="end">${escape(format(v))}</text>`;}
  const labels=[...new Set([0,Math.floor(rows.length*.25),Math.floor(rows.length*.5),Math.floor(rows.length*.75),rows.length-1])];
  for(const i of labels)svg+=`<text x="${x(i)}" y="${height-9}" text-anchor="middle">${rows[i].date.slice(5)}</text>`;
  series.forEach((s,si)=>{const points=rows.map((r,i)=>({i,v:s.value(r,i)})).filter(p=>Number.isFinite(p.v));if(!points.length)return;
    if(bar){const bw=Math.min(17,iw/rows.length*.62);points.forEach(p=>svg+=`<rect x="${x(p.i)-bw/2}" y="${y(p.v)}" width="${bw}" height="${Math.max(1,y(0)-y(p.v))}" fill="${p.i===rows.length-1?'#536ded':'#acb9ee'}" rx="2"/>`);}
    else{const path=points.map((p,j)=>`${j&&p.i===points[j-1].i+1?'L':'M'}${x(p.i).toFixed(2)},${y(p.v).toFixed(2)}`).join(' ');if(si===0&&series.length===1&&points.length===rows.length)svg+=`<path d="${path} L${x(points.at(-1).i)},${y(low)} L${x(points[0].i)},${y(low)} Z" fill="url(#fill-${container.id})"/>`;svg+=`<path d="${path}" fill="none" stroke="${s.color}" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" ${s.dash?'stroke-dasharray="5 5"':''}/>`;points.filter((p,i)=>!i||p.i!==points[i-1].i+1||i===points.length-1).forEach(p=>svg+=`<circle cx="${x(p.i)}" cy="${y(p.v)}" r="2" fill="${s.color}"/>`);}
  });
  svg+=`<line id="crosshair" x1="0" x2="0" y1="${pad.t}" y2="${height-pad.b}" stroke="#a6b0c8" stroke-dasharray="3 4" visibility="hidden"/><rect class="hit-area" x="${pad.l}" y="${pad.t}" width="${iw}" height="${ih}" fill="transparent"/></svg><div class="chart-tooltip" hidden></div>`;
  container.innerHTML=svg;
  const svgEl=$('svg',container),tooltip=$('.chart-tooltip',container),cross=$('#crosshair',container);
  function move(event){const box=svgEl.getBoundingClientRect();const coordinate=(event.clientX-box.left)/box.width*width;const i=Math.max(0,Math.min(rows.length-1,Math.round((coordinate-pad.l)/iw*(rows.length-1))));tooltip.hidden=false;tooltip.innerHTML=`${rows[i].date}<br>${series.map(s=>`${escape(s.label)}：${escape(format(s.value(rows[i],i)))} ${escape(unit)}`).join('<br>')}`;cross.setAttribute('x1',x(i));cross.setAttribute('x2',x(i));cross.setAttribute('visibility','visible');}
  svgEl.addEventListener('pointermove',move);svgEl.addEventListener('pointerleave',()=>{tooltip.hidden=true;cross.setAttribute('visibility','hidden');});
}
async function render(refresh=false){
  const token=++state.request;notice();$$('#nav button').forEach(b=>b.classList.toggle('active',b.dataset.page===state.page));$('#page-title').innerHTML=`${titles[state.page][0]}<span class="title-dot">.</span>`;$('#breadcrumb').textContent=titles[state.page][0];$('#page-description').textContent=titles[state.page][1];$('#content').innerHTML=loading();$('#refresh').disabled=true;
  try{if(state.page==='market')await renderMarket(token,refresh);else if(state.page==='sectors')await renderSectors(token,refresh);else if(state.page==='assets')await renderAssets(token,refresh);else await renderWatch(token,refresh);}catch(err){if(token===state.request)$('#content').innerHTML=panel('查询失败',unavailable({meta:{warning:err.message}}));}finally{if(token===state.request){$('#refresh').disabled=false;bindCommon();}}
}
async function renderMarket(token,refresh){
  state.exportTarget='market';
  $('#content').innerHTML=loading();
  const [market,margin]=await Promise.all([api('market',{refresh}),api('margin',{refresh})]);if(token!==state.request)return;
  state.latest=market;dateLabel(market);const rows=market.data?.rows,s=market.data?.summary||{},mrows=margin.data?.rows?.length?margin.data.rows:null,mlast=mrows?.at(-1),mprev=mrows?.at(-2);
  let cards=stat('沪深成交额',money(s.amount),'亿元',s.amount_ratio!=null?`<span class="${s.amount_ratio>=1?'up':'down'}">${num(s.amount_ratio)} 倍</span> 前 20 日均值`:'等待有效成交额','▥');
  cards+=stat('市场成交量',s.volume!=null?num(s.volume/1e8):'—',s.volume!=null?`亿${market.data.volume_unit}`:'',rows?`统计日期 ${rows.at(-1).date}`:'等待行情数据','▤');
  cards+=stat('融资融券余额',money(mlast?.total),'亿元',mlast?`截至 ${mlast.date}`:'等待交易所披露数据','⇄');
  const consecutive=mlast&&mprev&&(!mlast.previous_session||mlast.previous_session===mprev.date);
  const delta=consecutive?mlast.total-mprev.total:null;
  cards+=stat('两融余额日变化',delta!=null?`${delta>=0?'+':''}${money(delta)}`:'—','亿元',delta!=null?`<span class="${color(delta)}">较上一交易日 ${pct(delta/mprev.total*100)}</span>`:mlast?.previous_session?`缺少 ${mlast.previous_session} 共同数据`:'按共同披露日比较','↗');
  const indexRows=market.data?.indices||[];
  let indexTable=`<div class="table-wrap"><table><thead><tr><th>指数</th><th>最新点位</th><th>日涨跌</th><th>区间涨跌</th><th>趋势</th></tr></thead><tbody>${indexRows.map((item,i)=>`<tr class="clickable" data-index="${escape(item.code)}"><td>${escape(item.name)}<span class="code">${escape(item.code)}</span></td><td>${num(item.summary.close)}</td><td class="${color(item.summary.change)}">${pct(item.summary.change)}</td><td class="${color(item.summary.return)}">${pct(item.summary.return)}</td><td><svg viewBox="0 0 75 25" width="75" height="25"><polyline points="${spark(item.rows)}" fill="none" stroke="${item.summary.return>=0?'#df747b':'#47ad95'}" stroke-width="1.5"/></svg></td></tr>`).join('')}</tbody></table></div>`;
  $('#content').innerHTML=`<div class="stats">${cards}</div>`+panel('市场量能趋势',rows?`<div class="volume-label" id="market-unit">单位：亿元</div><div class="chart" id="market-chart"></div><div class="chart-summary"><span>区间交易日 <b>${rows.length} 日</b></span><span>区间日均成交额 <b>${money(rows.reduce((a,r)=>a+r.amount,0)/rows.length)} 亿元</b></span><span>最新 / 前 20 日均值 <b>${num(s.amount_ratio)} 倍</b></span></div><p class="inline-help">${escape(market.data.scope)}。盘中日线可能尚未完成；40 个交易日约为两个月。</p><div class="chart-summary"><span>近 5 日日均成交额 <b>${money(market.data.observation?.amount_mean5)} 亿元</b></span><span>较之前 5 日 <b>${pct(market.data.observation?.amount_5_change)}</b></span></div><p class="inline-help">两个 5 日区间互不重叠，最近区间包含最新日线；盘中成交额尚未完成。</p>${source(market)}`:unavailable(market,'市场行情'),`<div class="tabs" id="market-tabs"><button data-metric="amount" class="${state.chartMetric==='amount'?'active':''}">成交额</button><button data-metric="volume" class="${state.chartMetric==='volume'?'active':''}">成交量</button></div>`)+`<div class="two-columns">${panel('融资融券趋势',mrows?`<div class="volume-label">单位：亿元 · 截至 ${mlast.date}</div><div class="chart" id="margin-chart"></div><div class="legend"><span><i style="background:#7388e8"></i><span id="margin-legend">两融余额</span></span></div><div class="chart-summary"><span>融资余额 <b>${money(mlast.financing)} 亿</b></span><span>融券余额 <b>${money(mlast.securities)} 亿</b></span></div><p class="inline-help">${escape(margin.data.scope)}。两融数据随交易所披露更新，可能滞后于行情。</p>${marginCoverage(margin.data)}${source(margin)}<details style="margin-top:15px"><summary style="font-size:11px;color:#8592a8;cursor:pointer">查看每日两融数据与来源</summary><div class="table-wrap" style="max-height:260px;overflow:auto;margin-top:10px"><table><thead><tr><th>日期</th><th>两融余额（亿）</th><th>融资买入（亿）</th><th>当日来源</th></tr></thead><tbody>${[...mrows].reverse().map(r=>`<tr><td>${r.date}</td><td>${money(r.total)}</td><td>${money(r.buy)}</td><td>${escape(r.source||margin.meta.source)}</td></tr>`).join('')}</tbody></table></div></details>`:unavailable(margin,'融资融券'),`<div class="tabs" id="margin-tabs"><button data-metric="total" class="active">余额</button><button data-metric="buy">融资买入</button></div><button class="link-button" id="export-margin">导出两融 ↓</button>`)}${panel('主要指数',indexRows.length?`${indexTable}<p class="inline-help">区间涨跌为所选范围首尾点位变化。点击指数查看详细行情。</p>${source(market)}`:unavailable(market,'指数行情'),'<button class="link-button" id="all-assets">全部指数 ↗</button>')}</div>`;
  function drawMarket(){const metric=state.chartMetric;$('#market-unit').textContent=metric==='amount'?'单位：亿元':`单位：亿${market.data.volume_unit}`;chart($('#market-chart'),rows,[{label:metric==='amount'?'成交额':'成交量',color:'#7388e8',value:r=>r[metric]==null?NaN:r[metric]/1e8}],{bar:true,unit:metric==='amount'?'亿元':`亿${market.data.volume_unit}`});}
  if(rows)drawMarket();
  $$('#market-tabs button').forEach(b=>b.onclick=()=>{state.chartMetric=b.dataset.metric;$$('#market-tabs button').forEach(x=>x.classList.toggle('active',x===b));if(rows)drawMarket();});
  function drawMargin(){const metric=state.marginMetric;$('#margin-legend').textContent=metric==='total'?'两融余额':'融资买入额';const missing=margin.data.missing_dates||[];const dated=[...mrows,...missing.map(date=>({date}))].sort((a,b)=>a.date.localeCompare(b.date));chart($('#margin-chart'),dated,[{label:metric==='total'?'两融余额':'融资买入额',color:'#7388e8',value:r=>r[metric]==null?NaN:r[metric]/1e8}],{unit:'亿元'});}
  if(mrows)drawMargin();
  $$('#margin-tabs button').forEach(b=>{b.classList.toggle('active',b.dataset.metric===state.marginMetric);b.onclick=()=>{state.marginMetric=b.dataset.metric;$$('#margin-tabs button').forEach(x=>x.classList.toggle('active',x===b));if(mrows)drawMargin();};});
  $('#export-margin').onclick=()=>downloadCSV({mode:state.mode,days:state.days,target:'margin'},'两融');
  $('#all-assets').onclick=()=>navigate('assets');$$('[data-index]').forEach(r=>r.onclick=()=>{state.selected={code:r.dataset.index,name:$('td',r).childNodes[0].textContent,kind:'index'};navigate('assets');});
}
function spark(rows){const vals=rows.map(r=>r.close),min=Math.min(...vals),max=Math.max(...vals);return vals.map((v,i)=>`${i/(vals.length-1||1)*73+1},${23-(v-min)/(max-min||1)*21}`).join(' ');}
async function renderSectors(token,refresh){
  state.exportTarget='history';
  const [result,directory]=await Promise.all([
    api('sectors',{category:state.category,provider:state.sectorProvider,refresh}).catch(error=>({data:null,meta:{warning:error.message}})),
    api('indices').catch(()=>({items:[]}))
  ]);if(token!==state.request)return;
  const sectorIndices=(directory.items||[]).filter(x=>x.group);
  const indexPanel=sectorIndices.length?panel('行业／主题指数观察',`<p class="inline-help">按指数成分范围观察近 ${state.days} 个交易日的量价变化。点击查看走势、区间对比、加入自选或导出。</p><div class="sector-index-list">${sectorIndices.map(x=>`<button class="asset-button" data-sector-index="${escape(x.code)}"><span>${escape(x.name)}<span class="code">${escape(x.code)}</span></span><span class="pill">${x.group==='industry'?'行业指数':'主题指数'} ↗</span></button>`).join('')}</div><p class="inline-help">${escape(directory.scope)}</p><div id="sector-index-overview">${loading()}</div>`):'';
  state.sectorItems=result.data?.items||[];
  $('#content').innerHTML=indexPanel+`<div class="search-row"><div class="tabs" id="sector-category"><button data-category="industry" class="${state.category==='industry'?'active':''}">行业板块</button><button data-category="concept" class="${state.category==='concept'?'active':''}">概念板块</button></div><label class="search-box">⌕ <input id="sector-search" placeholder="搜索板块名称" aria-label="搜索板块"></label><select class="sort-select" id="sector-provider" aria-label="板块数据源"><option value="auto">自动选择数据源</option><option value="sina">新浪分类快照</option><option value="eastmoney">东方财富 · 支持历史</option></select><select class="sort-select" id="sector-sort" aria-label="板块排序"><option value="change">按涨跌幅排序</option><option value="turnover">按换手率排序</option><option value="amount">按成交额排序</option></select></div><form id="sector-direct" class="search-row"><label class="search-box">⌕ <input id="sector-code" placeholder="输入东方财富板块代码，如 BK0715" aria-label="直接查询板块代码" maxlength="6"></label><button class="button" type="submit">查询板块历史</button><span class="inline-help">按当前行业 / 概念分类查询；与新浪快照分类独立。</span></form><div id="sector-board"></div><div id="sector-detail"></div>${source(result)}`;
  function board(){const search=$('#sector-search').value.trim(),sort=$('#sector-sort').value;const items=state.sectorItems.filter(x=>x.name.includes(search)).sort((a,b)=>(b[sort]??-Infinity)-(a[sort]??-Infinity));
    $('#sector-board').innerHTML=result.data?`<div class="heatmap">${items.slice(0,12).map(x=>`<button class="heat-tile ${x.change<0?'negative':''}" data-sector="${escape(x.code)}"><strong>${escape(x.name)}</strong><b>${pct(x.change)}</b></button>`).join('')}</div>`+panel('板块行情',`<div class="table-wrap"><table><thead><tr><th>板块名称</th><th>涨跌幅</th><th>换手率</th><th>成交额（亿元）</th><th>上涨 / 下跌家数</th><th></th></tr></thead><tbody>${items.map(x=>`<tr class="clickable" data-sector="${escape(x.code)}"><td>${escape(x.name)}<span class="code">${escape(x.code)}</span></td><td class="${color(x.change)}">${pct(x.change)}</td><td>${x.turnover==null?'—':num(x.turnover)+'%'}</td><td>${money(x.amount)}</td><td>${num(x.advancing,0)} / ${num(x.declining,0)}</td><td class="neutral">↗</td></tr>`).join('')||'<tr><td colspan="6">未找到匹配板块</td></tr>'}</tbody></table></div><p class="inline-help">板块列表为行情快照。主源板块支持近 ${state.days} 日历史；新浪备用列表提供分类快照。源未提供字段显示「—」。</p>`):panel('板块行情',unavailable(result,'板块数据'));
    $$('[data-sector]').forEach(b=>b.onclick=()=>selectSector(state.sectorItems.find(x=>x.code===b.dataset.sector)));bindCommon();}
  $$('[data-sector-index]').forEach(button=>button.onclick=()=>{state.selected=sectorIndices.find(x=>x.code===button.dataset.sectorIndex);state.compare='';navigate('assets');});
  if(sectorIndices.length)void renderSectorIndexOverview(token,refresh);
  board();$('#sector-provider').value=state.sectorProvider;$('#sector-provider').onchange=e=>{state.sectorProvider=e.target.value;state.selected={code:'000300',name:'沪深300',kind:'index'};render();};$('#sector-search').oninput=board;$('#sector-sort').onchange=board;$$('#sector-category button').forEach(b=>b.onclick=()=>{state.category=b.dataset.category;render();});
  $('#sector-direct').onsubmit=async event=>{event.preventDefault();const code=$('#sector-code').value.trim().toUpperCase();if(!/^BK\d{4}$/.test(code)){toast('请输入 BK 加四位数字的板块代码');return;}const known=state.sectorItems.find(x=>x.code===code);await selectSector({...known,code,name:known?.name||`东方财富 ${code}`,provider:'eastmoney',history_supported:true,direct:true});};
  if(state.selected.kind==='sector'&&state.selected.category===state.category&&(result.data||state.selected.direct))await selectSector(state.selected,refresh);
}
async function renderSectorIndexOverview(token,refresh){
  const mode=state.mode,days=state.days;
  try{
    const res=await fetch(`/api/sector-indices?${new URLSearchParams({mode,days,refresh})}`,{signal:AbortSignal.timeout(120000)});
    if(!res.ok)throw new Error(`指数概览查询失败 (${res.status})`);
    const overview=await res.json();
    if(token!==state.request||state.page!=='sectors')return;
    const root=$('#sector-index-overview');if(!root)return;
    root.innerHTML=`<div class="search-row"><span class="inline-help">可用 ${overview.available} / ${overview.items.length} 项 · 所选 ${days} 个交易日</span><select id="sector-index-sort" aria-label="指数概览排序"><option value="return_5">按近 5 日涨跌</option><option value="return_20">按近 20 日涨跌</option><option value="amount_5_change">按近 5 日成交额变化</option><option value="amount">按最新成交额</option></select><button class="link-button" id="export-index-overview">导出概览 ↓</button></div><div id="sector-index-table"></div><p class="inline-help">先按数据截至日期分组，同日期内按所选指标从高到低排序；不同日期不可直接作为同期排行。近 5 / 20 日涨跌按对应交易日前收盘计算；成交额变化比较最近与之前两个不重叠的 5 日均额。盘中日线可能未完成，缺失数据留空；只覆盖上方 6 个指数。</p>`;
    function table(){
      const sort=$('#sector-index-sort').value,value=item=>sort==='amount'?item.summary?.amount:item.observation?.[sort];
      const items=[...overview.items].sort((a,b)=>Number(b.available)-Number(a.available)||(b.end||'').localeCompare(a.end||'')||(value(b)??-Infinity)-(value(a)??-Infinity));
      $('#sector-index-table').innerHTML=`<div class="table-wrap"><table><thead><tr><th>指数</th><th>日涨跌</th><th>近 5 日</th><th>近 20 日</th><th>成交额（亿）</th><th>5 日均额变化</th><th>数据截至 / 样本</th></tr></thead><tbody>${items.map(x=>{const s=x.summary||{},o=x.observation||{};return `<tr><td><button class="link-button" data-overview-index="${escape(x.code)}">${escape(x.name)} ↗</button><span class="code">${escape(x.code)}</span></td><td class="${color(s.change)}">${pct(s.change)}</td><td class="${color(o.return_5)}">${pct(o.return_5)}</td><td class="${color(o.return_20)}">${pct(o.return_20)}</td><td>${money(s.amount)}</td><td class="${color(o.amount_5_change)}">${pct(o.amount_5_change)}</td><td>${x.end?escape(x.end):'暂不可用'}<span class="code">${x.samples} 日${x.meta.stale?' · 过期缓存':''}${x.meta.data_delayed?' · 数据滞后':''}${mode==='demo'?' · 演示':''}</span></td></tr>`;}).join('')}</tbody></table></div><details><summary class="inline-help">各指数来源、获取时间与查询状态</summary>${items.map(x=>`<div class="source"><strong>${escape(x.name)}</strong>${source({meta:x.meta})}${x.available?`<span>${escape(x.start)} 至 ${escape(x.end)} · ${x.samples} 日${x.samples<days?' · 少于请求窗口':''}</span>`:''}${x.meta.error?`<p>${escape(x.meta.error)}</p>`:''}</div>`).join('')}</details>`;
      $$('[data-overview-index]').forEach(button=>button.onclick=()=>{state.selected=overview.items.find(x=>x.code===button.dataset.overviewIndex);navigate('assets');});
    }
    table();$('#sector-index-sort').onchange=table;
    $('#export-index-overview').onclick=()=>downloadCSV({mode,days},'行业主题指数概览','/api/sector-indices/export');
  }catch(error){
    if(token!==state.request||state.page!=='sectors')return;
    const root=$('#sector-index-overview');if(root)root.innerHTML=`<p class="inline-help">${escape(error.message)}；仍可通过上方入口查询单个指数。</p>`;
  }
}
async function selectSector(item,refresh=false){if(!item)return;state.selected={...item,kind:'sector',category:state.category};state.exportTarget='history';const selected=state.selected;if(item.history_supported===false){state.latest=null;$('#sector-detail').innerHTML=panel(`${escape(item.name)} · 板块快照`,`<div class="detail-stats"><div><span>快照涨跌幅</span><b class="${color(item.change)}">${pct(item.change)}</b></div><div><span>成交额（亿元）</span><b>${money(item.amount)}</b></div><div><span>公司家数</span><b>${num(item.companies,0)}</b></div></div><p class="inline-help">新浪分类快照未提供交易日期、换手率或历史日线；此板块的两个月趋势和 CSV 导出暂不可用。数据更新时间以来源实际披露为准。</p>`);return;}$('#sector-detail').innerHTML=panel(`${escape(item.name)} · 近期交易`,loading());$('#sector-detail').scrollIntoView({behavior:'smooth',block:'start'});const token=state.request;try{const result=await api('history',{...selected,refresh});if(token!==state.request||state.selected.code!==selected.code||state.selected.category!==selected.category)return;state.latest=result;dateLabel(result);$('#sector-detail').innerHTML=detailHTML(result,selected);drawDetail(result);bindCommon();}catch(e){if(token===state.request)$('#sector-detail').innerHTML=panel('板块查询失败',unavailable({meta:{warning:e.message}}));}}
async function renderAssets(token,refresh){
  state.exportTarget='history';const result=await api('catalog',{refresh});if(token!==state.request)return;state.catalog=result.data?.items||[];
  if(state.selected.kind==='sector')state.selected={code:'000300',name:'沪深300',kind:'index'};
  state.assetKind=state.selected.kind;
  $('#content').innerHTML=`<div class="search-row"><div class="tabs" id="asset-kind"><button data-kind="index" class="${state.assetKind==='index'?'active':''}">常用指数</button><button data-kind="etf" class="${state.assetKind==='etf'?'active':''}">ETF 基金</button></div><label class="search-box">⌕ <input id="asset-search" placeholder="搜索名称或输入六位 ETF 代码" aria-label="搜索指数或ETF"></label></div><div class="asset-layout"><section class="panel"><div class="panel-head"><h2>资产列表</h2><span class="pill" id="asset-count"></span></div><div class="asset-list" id="asset-list"></div>${source(result)}</section><div id="asset-detail">${loading()}</div></div>`;
  function list(){const search=$('#asset-search').value.trim();let items=state.catalog.filter(x=>x.kind===state.assetKind&&(x.code.includes(search)||x.name.toLowerCase().includes(search.toLowerCase())));if(/^\d{6}$/.test(search)&&!items.length&&state.assetKind==='etf')items=[{code:search,name:`ETF ${search}`,kind:'etf'}];$('#asset-count').textContent=`${items.length} 项`;$('#asset-list').innerHTML=items.slice(0,250).map(x=>`<button class="asset-button ${x.code===state.selected.code&&x.kind===state.selected.kind?'active':''}" data-asset="${escape(x.code)}"><span>${escape(x.name)}<span class="code">${escape(x.code)}</span></span><span class="pill">${x.kind==='etf'?'ETF':'指数'}</span></button>`).join('')||'<div class="empty">没有匹配的资产</div>';$$('[data-asset]').forEach(b=>b.onclick=()=>{state.selected=items.find(x=>x.code===b.dataset.asset);state.compare='';list();selectAsset(refresh);});}
  list();$('#asset-search').oninput=list;$$('#asset-kind button').forEach(b=>b.onclick=()=>{state.assetKind=b.dataset.kind;$$('#asset-kind button').forEach(x=>x.classList.toggle('active',x===b));list();});await selectAsset(refresh);
}
async function selectAsset(refresh=false){const selected={...state.selected},token=state.request;$('#asset-detail').innerHTML=loading();try{const result=await api('history',{code:selected.code,kind:selected.kind,refresh});if(token!==state.request||state.selected.code!==selected.code||state.selected.kind!==selected.kind)return;state.latest=result;dateLabel(result);$('#asset-detail').innerHTML=detailHTML(result,selected);drawDetail(result);bindCommon();}catch(e){if(token===state.request)$('#asset-detail').innerHTML=panel('资产查询失败',unavailable({meta:{warning:e.message}}));}}
function saved(item){return state.watch.some(x=>x.code===item.code&&x.kind===item.kind);}
function observationHTML(result,item){
  const o=result.data?.observation;
  if(!o)return '';
  const digits=item.kind==='etf'?3:2;
  return `<details class="observation" open><summary>量价观察 · ${escape(o.start)} 至 ${escape(o.end)}</summary><div class="detail-stats"><div><span>近 5 日涨跌</span><b class="${color(o.return_5)}">${pct(o.return_5)}</b></div><div><span>近 20 日涨跌</span><b class="${color(o.return_20)}">${pct(o.return_20)}</b></div><div><span>距 MA5</span><b class="${color(o.ma5_distance)}">${pct(o.ma5_distance)}</b></div><div><span>距 MA20</span><b class="${color(o.ma20_distance)}">${pct(o.ma20_distance)}</b></div><div><span>近 5 日成交额变化</span><b class="${color(o.amount_5_change)}">${pct(o.amount_5_change)}</b></div><div><span>成交量 / 前 20 日均量</span><b>${num(o.volume_ratio20)} 倍</b></div><div><span>区间最高收盘 · ${escape(o.high_date)}</span><b>${num(o.high_close,digits)}</b></div><div><span>区间最低收盘 · ${escape(o.low_date)}</span><b>${num(o.low_close,digits)}</b></div></div><p class="inline-help">近 N 日涨跌比较最新收盘与 N 个交易日前收盘，需要 N+1 个样本；距均线 = 最新收盘 / 均线 − 1。成交额变化比较最近 5 日与之前 5 日的日均值，两组不重叠且包含最新日线。区间高低点按所选范围的收盘值计算。样本不足或字段缺失显示「—」。盘中成交数据可能尚未完成。</p></details>`;
}
function comparisonOptions(item,search=''){
  const text=search.trim().toLowerCase();
  const choices=state.catalog.filter(x=>!(x.code===item.code&&x.kind===item.kind));
  let matches=choices.filter(x=>x.code.includes(text)||x.name.toLowerCase().includes(text));
  if(/^\d{6}$/.test(text)&&!(item.kind==='etf'&&item.code===text)&&!state.catalog.some(x=>x.code===text))matches.push({kind:'etf',code:text,name:`ETF ${text}`});
  const selected=choices.find(x=>`${x.kind}:${x.code}`===state.compare);
  if(selected&&!matches.includes(selected))matches.unshift(selected);
  if(state.compare&&!matches.some(x=>`${x.kind}:${x.code}`===state.compare)){
    const [kind,code]=state.compare.split(':');if(code)matches.unshift({kind,code,name:`${kind==='etf'?'ETF':'指数'} ${code}`});
  }
  return matches.map(x=>`<option value="${x.kind}:${x.code}" ${state.compare===`${x.kind}:${x.code}`?'selected':''}>${escape(x.name)} · ${escape(x.code)}</option>`).join('');
}
function detailHTML(result,item){const rows=result.data?.rows,s=result.data?.summary||{};const star=item.kind==='sector'?'':`<button class="star ${saved(item)?'saved':''}" id="detail-star" aria-label="${saved(item)?'移出自选':'加入自选'}">${saved(item)?'★':'☆'}</button>`;
  return panel(`${escape(item.name)} ${star}`,rows?`<div class="section-meta">${escape(item.code)}<span class="pill">${item.kind==='etf'?'ETF':item.kind==='sector'?'板块':'指数'}</span><span>截至 ${rows.at(-1).date}</span></div>${result.data.scope?`<p class="inline-help">${escape(result.data.scope)}</p>`:''}<div class="detail-stats"><div><span>最新${item.kind==='index'||item.kind==='sector'?'点位':'价格'}</span><b>${num(s.close,item.kind==='etf'?3:2)}</b></div><div><span>日涨跌幅</span><b class="${color(s.change)}">${pct(s.change)}</b></div><div><span>区间涨跌幅</span><b class="${color(s.return)}">${pct(s.return)}</b></div><div><span>区间最大回撤</span><b class="down">${num(s.drawdown)}%</b></div></div><div class="panel-head"><div class="tabs" id="detail-tabs"><button data-view="price" class="active">价格走势</button><button data-view="amount">成交额</button><button data-view="volume">成交量</button><button data-view="relative">区间对比</button></div>${item.kind!=='sector'?`<div class="compare-controls"><input id="compare-search" class="compare-search" placeholder="搜索对比名称 / 代码" aria-label="搜索对比资产" maxlength="80"><select id="compare" class="compare-select" aria-label="选择对比资产"><option value="">选择对比资产</option>${comparisonOptions(item)}</select></div>`:''}</div><div class="volume-label" id="detail-unit">${escape(result.data.adjustment)}</div><div class="chart" id="detail-chart"></div><div class="legend" id="detail-legend"></div><div id="comparison-info"></div>${observationHTML(result,item)}<div class="chart-summary"><span>最新成交额 <b>${money(s.amount)} 亿元</b></span><span>相对前 20 日均值 <b>${num(s.amount_ratio)} 倍</b></span></div><p class="detail-info">区间涨跌按首尾收盘值计算；最大回撤按区间内收盘值计算。${escape(result.data.adjustment)}。最新日线可能包含尚未收盘的盘中数据。</p>${source(result)}<details style="margin-top:18px"><summary style="font-size:11px;color:#8592a8;cursor:pointer">查看每日交易数据 · ${rows.length} 日</summary><div class="table-wrap" style="max-height:300px;overflow:auto;margin-top:12px"><table><thead><tr><th>日期</th><th>收盘</th><th>成交额（亿元）</th><th>成交量（${escape(result.data.volume_unit)}）</th><th>换手率</th></tr></thead><tbody>${[...rows].reverse().map(r=>`<tr><td>${r.date}</td><td>${num(r.close,3)}</td><td>${money(r.amount)}</td><td>${num(r.volume,0)}</td><td>${r.turnover==null?'—':num(r.turnover)+'%'}</td></tr>`).join('')}</tbody></table></div></details>`:unavailable(result,escape(item.name)));
}
function drawDetail(result){
  const rows=result.data?.rows;
  if(!rows?.length)return;
  let view='price',other=null,comparisonLoading=false,comparisonError='',comparisonRequest=0;
  function draw(){
    const container=$('#detail-chart');
    if(!container)return;
    const info=$('#comparison-info');
    info.innerHTML='';
    let series,opts={},plotRows=rows;
    if(view==='amount'||view==='volume'){
      const amount=view==='amount';
      series=[{label:amount?'成交额':'成交量',color:'#7388e8',value:r=>r[view]==null?NaN:r[view]/(amount?1e8:1e4)}];
      opts={bar:true,unit:amount?'亿元':`万${result.data.volume_unit}`};
      $('#detail-unit').textContent=`单位：${opts.unit}`;
    }else if(view==='relative'){
      if(comparisonLoading||comparisonError){
        container.innerHTML=comparisonLoading?loading():`<div class="empty">${escape(comparisonError)}</div>`;
        $('#detail-legend').innerHTML='';
        return;
      }
      if(other){
        const comparison=other.comparison;
        if(!comparison){
          container.innerHTML='<div class="empty">两个资产没有可用于比较的共同交易日期</div>';
          $('#detail-legend').innerHTML='';
          return;
        }
        plotRows=comparison.rows;
        series=[{label:state.selected.name,color:'#687fe7',value:r=>r.own??NaN},
          {label:other.name,color:'#e9ae65',value:r=>r.other??NaN}];
        info.innerHTML=`<p class="inline-help">共同区间 ${comparison.start} 至 ${comparison.end} · ${comparison.count} 个交易日；双方按共同首日归一化。${comparison.count<2?'仅有一个共同日期，无法观察区间变化。':''}</p><div class="table-wrap"><table><thead><tr><th>资产</th><th>共同区间涨跌</th><th>数据截至</th></tr></thead><tbody><tr><td>${escape(state.selected.name)}</td><td class="${color(comparison.ownReturn)}">${pct(comparison.ownReturn)}</td><td>${other.ownAsset.asof}</td></tr><tr><td>${escape(other.name)}</td><td class="${color(comparison.otherReturn)}">${pct(comparison.otherReturn)}</td><td>${other.asset.asof}</td></tr></tbody></table></div><p class="inline-help">对比资产 ${escape(other.name)} · ${escape(other.adjustment)}</p>${other.asset.scope?`<p class="inline-help">${escape(other.asset.scope)}</p>`:''}${source(other.ownResult)}${source(other.result)}<button class="button" id="export-comparison">导出对比数据 ↓</button>`;
        $('#export-comparison').onclick=()=>downloadCSV({target:'compare',mode:state.mode,days:state.days,code:other.ownAsset.code,kind:other.ownAsset.kind,other_code:other.asset.code,other_kind:other.asset.kind},'资产对比');
        $('#detail-unit').textContent='共同交易日首日归一为 0%；未计分红';
      }else{
        series=[{label:state.selected.name,color:'#687fe7',value:r=>(r.close/rows[0].close-1)*100}];
        $('#detail-unit').textContent='所选资产区间首日归一为 0%；选择另一个资产进行对比';
      }
      opts={percent:true};
    }else{
      series=[{label:'收盘',color:'#687fe7',value:r=>r.close},
        {label:'MA5',color:'#edb568',value:r=>r.ma5??NaN},
        {label:'MA20',color:'#9fc9bb',dash:true,value:r=>r.ma20??NaN}];
      $('#detail-unit').textContent=result.data.adjustment+' · MA5 / MA20 使用完整 5 / 20 日样本';
    }
    chart(container,plotRows,series,opts);
    $('#detail-legend').innerHTML=series.map(s=>`<span><i style="background:${s.color}"></i>${escape(s.label)}</span>`).join('');
  }
  function setView(next){
    view=next;
    $$('#detail-tabs button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));
    draw();
  }
  async function loadComparison(value){
    state.compare=value;
    other=null;comparisonError='';
    const sequence=++comparisonRequest;
    comparisonLoading=!!value;
    if(!value){draw();return;}
    setView('relative');
    const [kind,code]=value.split(':'),token=state.request,ownCode=state.selected.code;
    const asset=state.catalog.find(x=>x.code===code&&x.kind===kind);
    try{
      const data=await api('compare',{code:ownCode,kind:state.selected.kind,other_code:code,other_kind:kind});
      if(sequence!==comparisonRequest||token!==state.request||ownCode!==state.selected.code)return;
      if(data.data?.rows?.length)other={comparison:data.data,name:asset?.name||code,asset:data.assets.other,ownAsset:data.assets.own,result:{meta:data.assets.other.meta},ownResult:{meta:data.assets.own.meta},adjustment:data.assets.other.adjustment};
      else comparisonError=[data.meta?.warning,data.assets?.own.meta.warning,data.assets?.other.meta.warning].filter(Boolean).join('；')||'对比行情暂不可用';
    }catch(e){
      if(sequence!==comparisonRequest||token!==state.request)return;
      comparisonError=e.message||'对比查询失败';
    }
    comparisonLoading=false;
    draw();
  }
  draw();
  $$('#detail-tabs button').forEach(b=>b.onclick=()=>setView(b.dataset.view));
  if($('#detail-star'))$('#detail-star').onclick=()=>{toggleWatch(state.selected);$('#detail-star').classList.toggle('saved',saved(state.selected));$('#detail-star').textContent=saved(state.selected)?'★':'☆';$('#detail-star').setAttribute('aria-label',saved(state.selected)?'移出自选':'加入自选');};
  if($('#compare')){
    $('#compare').onchange=e=>loadComparison(e.target.value);
    $('#compare-search').oninput=e=>{
      const select=$('#compare');
      select.innerHTML='<option value="">选择对比资产</option>'+comparisonOptions(state.selected,e.target.value);
      select.value=state.compare||'';
    };
    if(state.compare)loadComparison(state.compare);
  }
}
function toggleWatch(item){if(saved(item)){state.watch=state.watch.filter(x=>!(x.code===item.code&&x.kind===item.kind));toast('已移出自选');}else{state.watch.push({code:item.code,name:item.name,kind:item.kind});toast('已加入自选');}persist('guanshi-watch',state.watch);$('#watch-count').textContent=state.watch.length;}
async function renderWatch(token,refresh){state.exportTarget='history';if(!state.watch.length){$('#content').innerHTML=panel('我的自选','<div class="empty"><span style="font-size:32px;color:#afbbda">☆</span><strong>为关心的资产留一个位置</strong><p>在「指数与 ETF」中点击星标，将资产加入自选。自选保存在当前浏览器中。</p><button class="button dark" id="add-watch">浏览指数与 ETF ↗</button></div>');$('#add-watch').onclick=()=>navigate('assets');return;}
  const items=[...state.watch];const results=await Promise.all(items.map(async item=>{try{return {item,result:await api('history',{code:item.code,kind:item.kind,refresh})};}catch{return {item,result:null};}}));if(token!==state.request)return;
  $('#content').innerHTML=panel(`我的自选 <span class="pill">${items.length} 项</span>`,`<div class="table-wrap"><table><thead><tr><th>资产</th><th>最新价格 / 点位</th><th>日涨跌</th><th>区间涨跌</th><th>成交额（亿元）</th><th>数据截至</th><th></th></tr></thead><tbody>${results.map(({item,result},i)=>{const s=result?.data?.summary||{};return `<tr class="clickable" data-watch="${i}"><td>${escape(item.name)}<span class="code">${escape(item.code)} · ${item.kind==='etf'?'ETF':'指数'}</span></td><td>${num(s.close,item.kind==='etf'?3:2)}</td><td class="${color(s.change)}">${pct(s.change)}</td><td class="${color(s.return)}">${pct(s.return)}</td><td>${money(s.amount)}</td><td>${s.date||'暂无行情'}${result?.meta?.stale?' · 过期缓存':''}</td><td><button class="star saved" data-remove="${i}" aria-label="移出自选">★</button></td></tr>`;}).join('')}</tbody></table></div><p class="inline-help">自选保存在当前浏览器。点击资产查看走势和成交情况。</p>`,'<button class="link-button" id="more-watch">添加自选 ↗</button>');$('#more-watch').onclick=()=>navigate('assets');$$('[data-watch]').forEach(r=>r.onclick=()=>{state.selected=items[Number(r.dataset.watch)];navigate('assets');});$$('[data-remove]').forEach(b=>b.onclick=e=>{e.stopPropagation();toggleWatch(items[Number(b.dataset.remove)]);render();});
}
function bindCommon(){$$('.retry').forEach(b=>b.onclick=()=>render(true));}
function navigate(page){state.page=page;state.compare='';render();window.scrollTo({top:0,behavior:'smooth'});}
$$('#nav button').forEach(b=>b.onclick=()=>navigate(b.dataset.page));
$$('#periods button').forEach(b=>b.onclick=()=>{state.days=Number(b.dataset.days);$$('#periods button').forEach(x=>x.classList.toggle('active',x===b));render();});
$('#mode').onchange=e=>{state.mode=e.target.value;persist('guanshi-mode',state.mode);render();};
$('#refresh').onclick=()=>render(true);
async function downloadCSV(params,label,endpoint='/api/export'){try{const res=await fetch(`${endpoint}?${new URLSearchParams(params)}`);if(!res.ok)throw new Error('暂无可导出的行情数据');const blob=await res.blob(),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`观市-${label||'行情'}-${state.mode==='demo'?'演示':'行情'}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('数据已导出，包含来源、模式和获取时间');}catch(e){toast(e.message);}}
$('#export').onclick=async()=>{if(state.page==='sectors'&&state.selected.history_supported===false){toast('该备用板块源未提供历史日线，暂无可导出数据');return;}if(state.page==='watchlist'){toast('点击自选资产进入详情后导出');return;}if(state.page==='sectors'&&state.selected.kind!=='sector'){toast('请先选择一个板块，再导出每日数据');return;}const params={mode:state.mode,days:state.days,target:state.exportTarget};if(params.target==='history')Object.assign(params,{code:state.selected.code,kind:state.selected.kind,name:state.selected.name,category:state.selected.category||state.category});downloadCSV(params,params.target==='market'?'大盘':state.selected.name);};
$('#watch-count').textContent=state.watch.length;
$('#close-sources').onclick=()=>$('#sources-dialog').close();
$('#source-status').onclick=async()=>{const dialog=$('#sources-dialog');if(!dialog.open)dialog.showModal();$('#sources-content').innerHTML=loading();try{const result=await fetch('/api/sources').then(r=>r.json());const names={tencent:'腾讯证券',eastmoney:'东方财富',exchanges:'沪深交易所',jin10:'金十报告',sina:'新浪财经'};$('#sources-content').innerHTML=`<p class="inline-help">状态来自实际查询；东方财富状态与冷却时间在重启后保留。打开本面板不会额外请求行情源。</p>${Object.entries(names).map(([key,name])=>{const status=result.sources[key];return `<div class="source-row"><div>${name}<small>${status?.checked_at?escape(status.checked_at.replace('T',' ').slice(0,19)):'尚未查询'}${status?.error?'<br>'+escape(status.error):''}</small></div><span class="source-label ${status?.state==='error'?'failed':''}">${status?.state==='ok'?'最近请求成功':status?.state==='error'?'最近请求失败':'未查询'}</span></div>`;}).join('')}<p class="inline-help">${escape(result.policy)}。${escape(result.cooldown_policy||'')}。${result.eastmoney_cooldown_seconds?`东方财富冷却剩余约 ${result.eastmoney_cooldown_seconds} 秒。`:''}请求成功代表返回有效数据，实际截至日期请查看各模块。</p>`;}catch(e){$('#sources-content').innerHTML=unavailable({meta:{warning:e.message}},'数据源状态');}};
render();
