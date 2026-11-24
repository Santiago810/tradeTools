import asyncio
import json
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from . import demo

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'data'/'cache.sqlite3'
LOCKS={}
SOURCE_STATUS={}
WORKERS=asyncio.Semaphore(4)
EASTMONEY_GATE=asyncio.Lock()


class SourceCooling(Exception):
    pass


def now(): return datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds')


def connect():
    DB.parent.mkdir(exist_ok=True)
    db=sqlite3.connect(DB)
    db.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, payload TEXT, saved TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS source_state (source TEXT PRIMARY KEY, payload TEXT)')
    return db


def cached(key):
    with connect() as db:
        row=db.execute('SELECT payload,saved FROM cache WHERE key=?',(key,)).fetchone()
        return (json.loads(row[0]),row[1]) if row else None


def save(key,payload):
    stamp=now()
    with connect() as db:
        db.execute('INSERT OR REPLACE INTO cache VALUES (?,?,?)',(key,json.dumps(payload,ensure_ascii=False,allow_nan=False),stamp))
    return stamp


def source_state(source):
    with connect() as db:
        row=db.execute('SELECT payload FROM source_state WHERE source=?',(source,)).fetchone()
    return json.loads(row[0]) if row else {}


def persist_source(source,state):
    with connect() as db:
        db.execute('INSERT OR REPLACE INTO source_state VALUES (?,?)',(source,json.dumps(state,ensure_ascii=False,allow_nan=False)))


def cooldown_remaining():
    return max(0,int(source_state('eastmoney').get('cooldown_until',0)-time.time()+.999))


def mark_rate_limit(error):
    previous=source_state('eastmoney')
    stamp=time.time()
    streak=previous.get('rate_limit_streak',0)+1 if stamp-previous.get('last_rate_limit',0)<86400 else 1
    seconds=min(300*2**min(streak-1,3),2400)
    state=dict(previous,state='error',checked_at=now(),error=error[:400],last_rate_limit=stamp,
               rate_limit_streak=streak,cooldown_until=stamp+seconds,cooldown_duration=seconds)
    persist_source('eastmoney',state)
    SOURCE_STATUS['eastmoney']=state


async def guarded_worker(action,params,source,timeout):
    if source!='eastmoney':
        return await run_worker(action,params,source,timeout)
    # Waiting requests recheck the persisted cooldown after the active one ends.
    async with EASTMONEY_GATE:
        remaining=cooldown_remaining()
        if remaining:
            raise SourceCooling(f'东方财富限流冷却中，剩余约 {remaining} 秒；已跳过该源')
        try:
            data=await run_worker(action,params,source,timeout)
        except Exception as exc:
            if 'Push2RateLimitError' in str(exc) or re.search(r'\b429\s+(?:Too Many Requests|Client Error)',str(exc)):
                mark_rate_limit(str(exc))
            raise
        state=source_state(source)
        state.update(state='ok',checked_at=now(),error='',cooldown_until=0,rate_limit_streak=0)
        persist_source(source,state)
        return data


def source_plan(action, params):
    if action=='margin': return [('exchanges',37),('jin10',6)]
    if action=='market' or (action=='history' and params.get('kind') in ('index','etf')):
        return [('tencent',14),('eastmoney',25)]
    if action=='catalog': return [('sina',15),('eastmoney',24)]
    if action=='sectors':
        provider=params.get('provider','auto')
        if provider=='eastmoney': return [('eastmoney',39)]
        if provider=='sina': return [('sina',10)]
        return [('sina',10),('eastmoney',29)]
    return [('eastmoney',40)]


def metadata(data, stamp, *, stale=False, cached=False, warning=''):
    messages=[message for message in (data.get('_warning',''),warning) if message]
    return dict(mode='live',source=data.get('_source','公开行情源 · 历史缓存'),
                fetched_at=stamp,stale=stale,cached=cached,warning='；'.join(messages))


async def run_worker(action, params, source, timeout):
    async with WORKERS:
        process=None
        try:
            process=await asyncio.create_subprocess_exec(sys.executable,'-m','backend.worker',
                json.dumps(dict(action=action,params=params,source=source),ensure_ascii=False),
                cwd=ROOT,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
            output,_=await asyncio.wait_for(process.communicate(),timeout=timeout)
            lines=[line[len('__RESULT__'):] for line in output.decode().splitlines() if line.startswith('__RESULT__')]
            if not lines: raise ValueError('行情源未返回有效结果')
            result=json.loads(lines[-1])
            if 'error' in result: raise ValueError(result['error'])
            data=result['data']
            if not data.get('rows',data.get('items',[])): raise ValueError('行情源返回空数据')
            return data
        finally:
            if process and process.returncode is None:
                process.kill()
                await process.communicate()


def source_status():
    states={**SOURCE_STATUS}
    eastmoney=source_state('eastmoney')
    if eastmoney: states['eastmoney']={**eastmoney,**states.get('eastmoney',{})}
    return {'sources':states, 'eastmoney_cooldown_seconds':cooldown_remaining(),
            'cooldown_policy':'东方财富请求串行；连续限流冷却 5 / 10 / 20 / 40 分钟，持久保存；成功后重置',
            'policy':'指数与ETF：腾讯→东方财富；两融：交易所→金十；板块快照与ETF名录：新浪→东方财富',
            'updated_at':now()}


async def query(action, params, mode='live', refresh=False):
    if mode=='demo':
        return dict(data=demo.fetch(action,params),meta=dict(mode='demo',source='合成演示数据',fetched_at=now(),stale=False,warning='演示数据按工作日生成，未使用真实行情或交易日历。'))
    key=action+json.dumps(params,sort_keys=True,ensure_ascii=False)
    async with LOCKS.setdefault(key,asyncio.Lock()):
        entry=cached(key)
        if entry and not refresh and (datetime.fromisoformat(now())-datetime.fromisoformat(entry[1])).total_seconds()<600:
            return dict(data=entry[0],meta=metadata(entry[0],entry[1],cached=True))
        failures=[]
        for source,timeout in source_plan(action,params):
            started=time.monotonic()
            try:
                data=await guarded_worker(action,params,source,timeout)
                SOURCE_STATUS[source]=dict(state='ok',checked_at=now(),elapsed_seconds=round(time.monotonic()-started,2))
                if failures: data['_warning']='已使用备用数据源；'+'；'.join(failures)+'；'+data.get('_warning','')
                stamp=save(key,data)
                return dict(data=data,meta=metadata(data,stamp))
            except Exception as exc:
                error=f'{source} 请求超时（{timeout} 秒）' if isinstance(exc,asyncio.TimeoutError) else str(exc)
                failures.append(error)
                if isinstance(exc,SourceCooling):
                    continue
                SOURCE_STATUS[source]=dict(state='error',checked_at=now(),error=error[:400])
        error='；'.join(failures)
        if entry:
            return dict(data=entry[0],meta=metadata(entry[0],entry[1],stale=True,cached=True,warning=error))
        return dict(data=None,meta=dict(mode='live',source='公开行情源',fetched_at=None,stale=True,error=error,
                    warning='所有可用数据源均未返回有效行情。请稍后重试；也可主动切换演示模式查看功能。'))
