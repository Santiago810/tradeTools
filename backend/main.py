import asyncio
import csv
import io
import re
from datetime import datetime, date
from zoneinfo import ZoneInfo
from typing import Literal
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from .service import query, ROOT, source_status
from .analytics import summarize, compare_histories, rolling_indicators, observation
from .catalog import INDICES, ETFS, SECTOR_INDICES, SECTOR_INDEX_SCOPE

app=FastAPI(title='观市 · A股行情工作台',version='1.0.0')


def validate_asset(code,kind,mode):
    if kind in ('index','etf') and not re.fullmatch(r'\d{6}',code):
        raise HTTPException(422,'指数和 ETF 代码必须为六位数字')
    if kind=='sector' and mode=='live' and not re.fullmatch(r'BK\d{4}',code):
        raise HTTPException(422,'板块历史仅支持东方财富 BK 加四位数字的代码；新浪快照代码没有历史日线')


def csv_response(rows,extras,filename):
    out=io.StringIO()
    fields=list(dict.fromkeys([*('row_source' if k=='source' else k for row in rows for k in row),*extras]))
    writer=csv.DictWriter(out,fieldnames=fields)
    writer.writeheader()
    for row in rows:
        values={**{('row_source' if k=='source' else k):v for k,v in row.items()},**extras}
        safe={k:("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v) for k,v in values.items()}
        writer.writerow(safe)
    return StreamingResponse(iter(['\ufeff'+out.getvalue()]),media_type='text/csv; charset=utf-8',
                             headers={'Content-Disposition':f'attachment; filename="{filename}"'})


async def comparison_response(code,kind,other_code,other_kind,mode,refresh,days):
    validate_asset(code,kind,mode)
    validate_asset(other_code,other_kind,mode)
    results=await asyncio.gather(*(response('history',dict(code=c,kind=k,name='',category='industry'),mode,refresh,days)
                                   for c,k in ((code,kind),(other_code,other_kind))))
    own,other=results
    assets={key:dict(code=c,kind=k,meta=r['meta'],asof=r['data']['rows'][-1]['date'] if r['data'] and r['data'].get('rows') else None,
                    adjustment=r['data'].get('adjustment','') if r['data'] else '',
                    scope=r['data'].get('scope','') if r['data'] else '')
            for key,c,k,r in (('own',code,kind,own),('other',other_code,other_kind,other))}
    if not all(r['data'] and r['data'].get('rows') for r in results):
        return dict(data=None,assets=assets,meta=dict(mode=mode,warning='双方行情均可用时才能比较，请查看各资产数据状态。'))
    try:
        comparison=compare_histories(own['data']['rows'],other['data']['rows'])
    except ValueError as exc:
        return dict(data=None,assets=assets,meta=dict(mode=mode,warning=str(exc)))
    return dict(data=comparison,assets=assets,meta=dict(mode=mode,warning='' if comparison else '双方没有共同交易日期，无法比较。'))


def window_margin(data, meta, days):
    # Legacy caches also contain known missing dates; never stretch a window by
    # counting only the successfully merged rows.
    sessions=sorted(set(data.get('sessions', [])) | {r['date'] for r in data['rows']} | set(data.get('missing_dates', [])))[-days:]
    selected=set(sessions)
    data['rows']=[r for r in data['rows'] if r['date'] in selected]
    available={r['date'] for r in data['rows']}
    data['sessions']=sessions
    data['missing_dates']=[day for day in sessions if day not in available]
    data['coverage']=dict(requested=days,sessions=len(sessions),available=len(available),
                          missing=len(data['missing_dates']),start=sessions[0] if sessions else None,
                          end=sessions[-1] if sessions else None,
                          calendar_basis=data.get('calendar_basis','来源已披露日期及已知缺失日期'))
    # Remove old global cache notices before adding selected-window notices.
    warning=re.sub(r'有 \d+ 个交易日缺少沪深共同数据；曲线在缺失日期处断开。\s*','',meta.get('warning',''))
    warning=warning.replace('部分历史日期来自金十报告，每日数据表和 CSV 标注各行来源。','').strip()
    notices=[warning] if warning else []
    if data['missing_dates']:
        notices.append(f"所选 {len(sessions)} 个交易日有 {len(data['missing_dates'])} 日缺少沪深共同数据，曲线断开，导出中标为缺失。")
    if len(sessions)<days:
        notices.append(f'来源仅提供 {len(sessions)} 个交易日，少于请求的 {days} 日。')
    if any(r.get('source','').startswith('金十') for r in data['rows']):
        notices.append('部分历史日期来自金十报告，每日数据表和 CSV 标注各行来源。')
    meta['warning']='；'.join(notices)


async def response(action,params,mode,refresh,days):
    result=await query(action,params,mode,refresh)
    if action=='history' and params.get('kind')=='index' and result['data']:
        item=next((x for x in SECTOR_INDICES if x['code']==params.get('code')),None)
        if item:
            result['data'].update(code=item['code'],name=item['name'],group=item['group'],
                                  scope=SECTOR_INDEX_SCOPE if mode=='live' else '合成指数日线，仅供演示；不代表真实成分证券成交。')
    return prepare_response(result,action,mode,days)


def prepare_response(result,action,mode,days):
    if result['data'] and 'rows' in result['data']:
        data=result['data']
        full_summary=summarize(data['rows']) if action!='margin' else {}
        if action=='margin':
            window_margin(data,result['meta'],days)
        else:
            rolling_indicators(data['rows'])
            data['rows']=data['rows'][-days:]
            data['observation']=observation(data['rows'])
        if mode=='live' and data['rows']:
            age=(datetime.now(ZoneInfo('Asia/Shanghai')).date()-date.fromisoformat(data['rows'][-1]['date'])).days
            if age>4:
                result['meta']['data_delayed']=True
                result['meta']['warning']=f"数据截至 {data['rows'][-1]['date']}，距今天 {age} 天；请勿视为当前行情。" + result['meta'].get('warning','')
        if action!='margin':
            data['summary']=summarize(data['rows'])
            if len(data['rows'])<2:
                data['summary']['change']=None
            data['summary']['amount_ratio']=full_summary.get('amount_ratio')
            for key in ('ma5','ma20'):
                data['summary'][key]=data['rows'][-1][key] if data['rows'] else None
            data['coverage']=dict(requested=days,available=len(data['rows']),
                                  start=data['rows'][0]['date'] if data['rows'] else None,
                                  end=data['rows'][-1]['date'] if data['rows'] else None)
            if len(data['rows'])<days:
                warning=f"来源仅提供 {len(data['rows'])} 个交易日，少于请求的 {days} 日；区间指标按实际样本计算。"
                result['meta']['warning']='；'.join(filter(None,(result['meta'].get('warning',''),warning)))
        for item in data.get('indices',[]):
            rolling_indicators(item['rows'])
            item['rows']=item['rows'][-days:]
            item['summary']=summarize(item['rows'])
            item['observation']=observation(item['rows'])
    return result


@app.get('/api/health')
def health(): return {'status':'ok','version':'1.0.0'}


@app.get('/api/sources')
def sources(): return source_status()


@app.get('/api/market')
async def market(days:int=Query(40,ge=5,le=100),mode:Literal['live','demo']='live',refresh:bool=False):
    return await response('market',{},mode,refresh,days)


@app.get('/api/margin')
async def margin(days:int=Query(40,ge=5,le=100),mode:Literal['live','demo']='live',refresh:bool=False):
    return await response('margin',{},mode,refresh,days)


@app.get('/api/sectors')
async def sectors(category:Literal['industry','concept']='industry',provider:Literal['auto','sina','eastmoney']='auto',mode:Literal['live','demo']='live',refresh:bool=False):
    return await query('sectors',{'category':category,'provider':provider},mode,refresh)


@app.get('/api/catalog')
async def catalog(mode:Literal['live','demo']='live',refresh:bool=False):
    result=await query('catalog',{},mode,refresh)
    if result['data'] is None:
        result['data']={'items':INDICES+ETFS,'limited':True}
        result['meta']['warning']='在线 ETF 名录不可用，展示常用代码列表；此列表不代表行情数据。'
    # Keep the local index directory current even when the online ETF directory
    # came from an older cache. Directory entries are not live quotes.
    result['data']['items']=[*INDICES,*[x for x in result['data']['items'] if x.get('kind')!='index']]
    return result


@app.get('/api/indices')
async def indices():
    return {'items':INDICES,'scope':SECTOR_INDEX_SCOPE,'directory_only':True}


async def sector_index_overview(mode,refresh,days):
    async def load(item):
        try:
            result=await response('history',dict(code=item['code'],kind='index',name='',category='industry'),mode,refresh,days)
        except Exception:
            result={'data':None,'meta':{'mode':mode,'warning':'该指数查询失败，请在详情页重试。','stale':True}}
        data=result['data'] or {}
        rows=data.get('rows',[])
        return dict(**item,available=bool(rows),summary=data.get('summary',{}),
                    observation=data.get('observation',{}),meta=result['meta'],
                    volume_unit=data.get('volume_unit',''),scope=data.get('scope',''),
                    start=rows[0]['date'] if rows else None,end=rows[-1]['date'] if rows else None,samples=len(rows))
    items=await asyncio.gather(*(load(item) for item in SECTOR_INDICES))
    dates=sorted({item['end'] for item in items if item['end']})
    return dict(items=items,days=days,dates=dates,available=sum(item['available'] for item in items),
                scope=SECTOR_INDEX_SCOPE if mode=='live' else '合成指数量价数据，仅供演示。',mode=mode)


@app.get('/api/sector-indices')
async def sector_indices(days:int=Query(40,ge=5,le=100),mode:Literal['live','demo']='live',refresh:bool=False):
    return await sector_index_overview(mode,refresh,days)


@app.get('/api/sector-indices/export')
async def export_sector_indices(days:int=Query(40,ge=5,le=100),mode:Literal['live','demo']='live'):
    overview=await sector_index_overview(mode,False,days)
    rows=[]
    for item in overview['items']:
        rows.append({'code':item['code'],'name':item['name'],'group':item['group'],
                     'row_status':'available' if item['available'] else 'unavailable',
                     'start':item['start'],'end':item['end'],'samples':item['samples'],
                     **item['summary'],**item['observation'],'volume_unit':item['volume_unit'],
                     'scope':item['scope'] or overview['scope'],
                     **{key:item['meta'].get(key) for key in ('source','fetched_at','stale','cached','warning','error')}})
    return csv_response(rows,dict(data_mode=mode,requested_days=days),f'guanshi-sector-indices-{mode}.csv')


@app.get('/api/history')
async def history(code:str=Query(...,pattern=r'^[A-Za-z0-9_]{2,40}$'),kind:Literal['index','etf','sector']='index',name:str=Query('',max_length=80),category:Literal['industry','concept']='industry',days:int=Query(40,ge=5,le=100),mode:Literal['live','demo']='live',refresh:bool=False):
    validate_asset(code,kind,mode)
    return await response('history',dict(code=code,kind=kind,name=name,category=category),mode,refresh,days)


@app.get('/api/compare')
async def compare(code:str=Query(...,pattern=r'^\d{6}$'),kind:Literal['index','etf']='index',other_code:str=Query(...,pattern=r'^\d{6}$'),other_kind:Literal['index','etf']='etf',days:int=Query(40,ge=5,le=100),mode:Literal['live','demo']='live',refresh:bool=False):
    return await comparison_response(code,kind,other_code,other_kind,mode,refresh,days)


@app.get('/api/export')
async def export(target:Literal['market','margin','history','compare']='market',code:str=Query('000001',pattern=r'^[A-Za-z0-9]{2,12}$'),kind:Literal['index','etf','sector']='index',name:str=Query('',max_length=80),category:Literal['industry','concept']='industry',days:int=Query(40,ge=5,le=100),mode:Literal['live','demo']='live',other_code:str=Query('',max_length=6),other_kind:Literal['index','etf']='etf'):
    if target in ('history','compare'): validate_asset(code,kind,mode)
    if target=='compare':
        if kind=='sector': raise HTTPException(422,'资产对比仅支持指数或 ETF')
        result=await comparison_response(code,kind,other_code,other_kind,mode,False,days)
        if not result['data']: raise HTTPException(503,result['meta']['warning'])
        extras={'data_mode':mode,'common_start':result['data']['start'],'common_end':result['data']['end'],'return_unit':'percent'}
        for label,asset in result['assets'].items():
            meta=asset['meta']
            extras.update({f'{label}_{k}':asset[k] for k in ('code','kind','asof','adjustment','scope')})
            extras.update({f'{label}_{k}':meta.get(k) for k in ('source','fetched_at','stale','warning')})
        return csv_response(result['data']['rows'],extras,f'guanshi-compare-{mode}.csv')
    result=await response(target,dict(code=code,kind=kind,name=name,category=category) if target=='history' else {},mode,False,days)
    if not result['data'] or not result['data'].get('rows'): raise HTTPException(503,'无可导出数据')
    rows=result['data']['rows']
    if target=='margin':
        rows=[dict(r,row_status='available') for r in rows]
        rows.extend(dict(date=day,row_status='missing') for day in result['data'].get('missing_dates',[]))
        rows.sort(key=lambda r:r['date'])
    return csv_response(rows,dict(data_mode=mode,source=result['meta']['source'],fetched_at=result['meta']['fetched_at'],stale=result['meta']['stale'],
                                  scope=result['data'].get('scope',''),volume_unit=result['data'].get('volume_unit',''),
                                  adjustment=result['data'].get('adjustment',''),warning=result['meta'].get('warning','')),
                        f'guanshi-{target}-{mode}.csv')

app.mount('/',StaticFiles(directory=ROOT/'frontend',html=True),name='frontend')
