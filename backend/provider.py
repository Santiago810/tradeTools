"""AKShare public data adapter. All amounts are yuan; volume units remain explicit."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import math
from .catalog import INDICES


def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (ValueError, TypeError):
        return None


def date(value):
    return str(value)[:10]


def normalize(df, english=False):
    fields = {'date':'date', 'open':'open', 'close':'close', 'high':'high', 'low':'low', 'volume':'volume', 'amount':'amount'} if english else {'日期':'date','开盘':'open','收盘':'close','最高':'high','最低':'low','成交量':'volume','成交额':'amount','换手率':'turnover'}
    rows=[]
    for raw in df.to_dict('records'):
        row = {target: date(raw[key]) if target=='date' else number(raw[key]) for key,target in fields.items() if key in raw}
        if row.get('date') and row.get('close') is not None:
            rows.append(row)
    return sorted(rows, key=lambda r:r['date'])


def fetch_eastmoney(action, params):
    import akshare as ak
    from akshare.utils.context import config
    config.timeout = (4, 8)
    end = datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d')
    start = (datetime.now(ZoneInfo('Asia/Shanghai'))-timedelta(days=200)).strftime('%Y%m%d')
    if action == 'history':
        code, kind = params['code'], params['kind']
        if kind == 'index':
            item = next((x for x in INDICES if x['code']==code), None)
            if not item:
                raise ValueError('暂不支持该指数代码，请从指数列表选择')
            df = ak.index_zh_daily_em(symbol=item['symbol'], start_date=start, end_date=end)
            return {'rows': normalize(df, True), 'volume_unit': '手', 'adjustment': '指数原始点位'}
        if kind == 'etf':
            df = ak.fund_etf_hist_em(symbol=code, period='daily', start_date=start, end_date=end, adjust='')
            return {'rows': normalize(df), 'volume_unit': '手', 'adjustment': '不复权；区间收益未计分红'}
        from .sources import eastmoney_sector_history
        return eastmoney_sector_history(code,params.get('category','industry'))
    if action == 'market':
        sh = normalize(ak.index_zh_daily_em(symbol='sh000001', start_date=start, end_date=end), True)
        sz = normalize(ak.index_zh_daily_em(symbol='sz399106', start_date=start, end_date=end), True)
        mapped = {r['date']:r for r in sz}
        rows=[]
        for a in sh:
            b=mapped.get(a['date'])
            if b and a.get('amount') is not None and b.get('amount') is not None:
                rows.append(dict(date=a['date'],close=a['close'],amount=a['amount']+b['amount'],volume=a['volume']+b['volume'] if a.get('volume') is not None and b.get('volume') is not None else None))
        return {'rows':rows, 'indices':[{'code':'000001','name':'上证指数','rows':sh},{'code':'399106','name':'深证综指','rows':sz}], 'scope':'上证综指 + 深证综指行情口径；含 B 股，不含北交所', 'volume_unit':'手'}
    if action == 'sectors':
        # AKShare's name adapter drops f6 (amount); retain the upstream field for ranking.
        from akshare.utils.func import fetch_paginated_data
        df=fetch_paginated_data('https://17.push2.eastmoney.com/api/qt/clist/get',{
            'pn':'1','pz':'100','po':'1','np':'1','fltt':'2','invt':'2','fid':'f3',
            'ut':'bd1d9ddb04089700cf9c27f6f7426281',
            'fs':'m:90 t:3 f:!50' if params.get('category')=='concept' else 'm:90 t:2 f:!50',
            'fields':'f3,f6,f8,f12,f14,f104,f105'})
        return {'items':[dict(code=str(r.get('f12','')),name=r['f14'],change=number(r.get('f3')),turnover=number(r.get('f8')),advancing=number(r.get('f104')),declining=number(r.get('f105')),amount=number(r.get('f6'))) for r in df.to_dict('records')]}
    if action == 'catalog':
        df=ak.fund_etf_spot_em()
        return {'items': INDICES + [dict(code=str(r['代码']),name=r['名称'],kind='etf') for r in df.to_dict('records')]}
    if action == 'margin':
        # Both exchanges must be present for an aggregate. Never present SSE alone as all-market.
        sh=ak.stock_margin_sse_js()
        sz=ak.stock_margin_szse_js()
        def map_rows(df):
            result={}
            for r in df.to_dict('records'):
                raw=str(r.get('信用交易日期',r.get('日期',''))).replace('-','')[:8]
                if len(raw)!=8: continue
                result[f'{raw[:4]}-{raw[4:6]}-{raw[6:]}']={
                    'financing':number(r.get('融资余额')), 'securities':number(r.get('融券余量金额',r.get('融券余额'))),
                    'total':number(r.get('融资融券余额')), 'buy':number(r.get('融资买入额'))}
            return result
        a,b=map_rows(sh),map_rows(sz)
        rows=[]
        for d in sorted(a.keys() & b.keys()):
            if d.replace('-','') < start or d.replace('-','') > end: continue
            values={key:a[d][key]+b[d][key] if a[d][key] is not None and b[d][key] is not None else None for key in ('financing','securities','total','buy')}
            if values['total'] is not None: rows.append(dict(date=d,**values))
        if not rows: raise ValueError('交易所融资融券数据列发生变化，未能取得沪深共同日期数据')
        return {'rows':rows,'scope':'金十沪深两融报告共同日期合计；不含北交所'}
    raise ValueError('未知数据类型')


def fetch(action, params, source='eastmoney'):
    if source == 'tencent':
        from .sources import tencent
        data = tencent(action, params)
        data['_source'] = '腾讯证券 · 不复权日线'
        return data
    if source == 'exchanges':
        from .sources import official_margin
        data = official_margin()
        data['_source'] = '上交所 + 深交所 · 官方汇总 / 金十历史报告'
        return data
    if source == 'jin10':
        from .sources import jin10_margin
        data = jin10_margin()
        data['_source'] = '金十 · 沪深两融报告'
        return data
    if source == 'sina':
        if action=='sectors':
            from .sources import sina_sectors
            data=sina_sectors(params.get('category','industry'))
            data['_source']='新浪财经 · 板块分类快照（源未提供日期）'
            return data
        import akshare as ak
        from akshare.utils.context import config
        config.timeout = (4, 8)
        df = ak.fund_etf_category_sina(symbol='ETF基金')
        data = {'items': INDICES + [dict(code=str(row['代码'])[-6:], name=row['名称'], kind='etf')
                                   for row in df.to_dict('records')]}
        data['_source'] = 'AKShare / 新浪财经 · ETF 名录'
        return data
    data = fetch_eastmoney(action, params)
    data['_source'] = 'AKShare / 金十（沪深两融报告）' if action == 'margin' else 'AKShare / 东方财富'
    return data
