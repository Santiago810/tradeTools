import math


def valid_number(value):
    return isinstance(value,(int,float)) and math.isfinite(value) and value>=0


def mean_field(rows,key,required):
    values=[row.get(key) for row in rows]
    return sum(values)/required if len(values)==required and all(valid_number(v) for v in values) else None


def rolling_indicators(rows):
    """Full sample periods; return_n compares today's close with n sessions ago."""
    for i,row in enumerate(rows):
        for period in (5,20):
            average=mean_field(rows[max(0,i-period+1):i+1],'close',period)
            row[f'ma{period}']=average
            row[f'ma{period}_distance']=(row['close']/average-1)*100 if average else None
            base=rows[i-period].get('close') if i>=period else None
            row[f'return_{period}']=(row['close']/base-1)*100 if valid_number(base) and base>0 else None
        recent=mean_field(rows[max(0,i-4):i+1],'amount',5)
        preceding=mean_field(rows[max(0,i-9):max(0,i-4)],'amount',5)
        row['amount_mean5']=recent
        row['amount_previous_mean5']=preceding
        row['amount_5_change']=(recent/preceding-1)*100 if recent is not None and preceding else None
        volume_base=mean_field(rows[max(0,i-20):i],'volume',20)
        volume=row.get('volume')
        row['volume_ratio20']=volume/volume_base if valid_number(volume) and volume_base else None


def observation(rows):
    if not rows:
        return {}
    latest=rows[-1]
    high=max(rows,key=lambda r:r['close'])
    low=min(rows,key=lambda r:r['close'])
    return {**{key:latest.get(key) for key in ('return_5','return_20','ma5_distance','ma20_distance',
               'amount_mean5','amount_previous_mean5','amount_5_change','volume_ratio20')},
            'start':rows[0]['date'],'end':latest['date'],'samples':len(rows),
            'high_close':high['close'],'high_date':high['date'],
            'low_close':low['close'],'low_date':low['date'],
            'from_high':(latest['close']/high['close']-1)*100 if high['close'] else None}


def compare_histories(own_rows, other_rows):
    own={row['date']:row for row in own_rows}
    other={row['date']:row for row in other_rows}
    shared=sorted(own.keys() & other.keys())
    if not shared:
        return None
    for day in shared:
        if any(not isinstance(row.get('close'),(int,float)) or not math.isfinite(row['close']) or row['close']<=0
               for row in (own[day],other[day])):
            raise ValueError('共同日期包含无效收盘值，无法计算对比')
    first,last=shared[0],shared[-1]
    own_base,other_base=own[first]['close'],other[first]['close']
    rows=[]
    for day in sorted(own.keys() | other.keys()):
        common=day in own and day in other
        rows.append(dict(date=day,own_close=own.get(day,{}).get('close'),other_close=other.get(day,{}).get('close'),
                         own=(own[day]['close']/own_base-1)*100 if common else None,
                         other=(other[day]['close']/other_base-1)*100 if common else None,
                         row_status='common' if common else 'unmatched'))
    return dict(start=first,end=last,count=len(shared),ownReturn=(own[last]['close']/own_base-1)*100,
                otherReturn=(other[last]['close']/other_base-1)*100,rows=rows)


def summarize(rows):
    if not rows:
        return {}
    closes = [r['close'] for r in rows]
    latest = rows[-1]
    previous = closes[-2] if len(rows) > 1 else closes[-1]
    peak, drawdown = closes[0], 0
    for close in closes:
        peak = max(peak, close)
        drawdown = min(drawdown, (close / peak - 1) * 100 if peak else 0)
    # Compare the latest day with PREVIOUS 20 sessions, excluding itself.
    amounts = [r['amount'] for r in rows[-21:-1] if r.get('amount') is not None]
    mean = sum(amounts) / len(amounts) if amounts else None
    return {
        'date': latest['date'], 'close': latest['close'],
        'change': (latest['close'] / previous - 1) * 100 if previous else None,
        'return': (closes[-1] / closes[0] - 1) * 100 if closes[0] else None,
        'drawdown': drawdown, 'amount': latest.get('amount'),
        'volume': latest.get('volume'), 'amount_ratio': latest.get('amount') / mean if mean and latest.get('amount') is not None else None,
        'ma5': sum(closes[-5:]) / len(closes[-5:]),
        'ma20': sum(closes[-20:]) / len(closes[-20:]),
    }
