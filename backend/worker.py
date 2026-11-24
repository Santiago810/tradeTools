import json
import sys
from backend.provider import fetch

if __name__ == '__main__':
    request=json.loads(sys.argv[1])
    try:
        result=fetch(request['action'],request['params'],request.get('source','eastmoney'))
        print('__RESULT__'+json.dumps({'data':result},ensure_ascii=False,allow_nan=False))
    except Exception as exc:
        print('__RESULT__'+json.dumps({'error':f'{type(exc).__name__}: {str(exc)[:350]}'},ensure_ascii=False))
