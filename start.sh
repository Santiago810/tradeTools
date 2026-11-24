#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

reload=0
install=0
for arg in "$@"; do
  case "$arg" in
    --reload) reload=1 ;;
    --install) install=1 ;;
    -h|--help)
      cat <<'HELP'
用法：./start.sh [--reload] [--install]
  --reload   修改代码后自动重启，供本地开发使用
  --install  重新按 requirements.txt 安装依赖
环境变量：HOST（默认 127.0.0.1）、PORT（默认 8080）
          PYTHON_BIN（首次创建虚拟环境时使用，默认 python3）
首次启动自动创建 .venv 并安装缺失依赖，需要网络。
服务在当前终端运行，按 Ctrl+C 停止。
HELP
      exit 0 ;;
    *) echo "不支持的参数：$arg；使用 ./start.sh --help 查看用法。" >&2; exit 2 ;;
  esac
done

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8080}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ ! -x .venv/bin/python ]]; then
  if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "未找到 $PYTHON_BIN，请先安装 Python 3.11 或以上。" >&2
    exit 1
  fi
  "$PYTHON_BIN" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else "需要 Python 3.11 或以上")'
  echo "正在创建项目虚拟环境 .venv …"
  "$PYTHON_BIN" -m venv .venv
fi

.venv/bin/python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else "现有 .venv 的 Python 版本过低，请用 Python 3.11 或以上重建")'
if [[ "$install" == 1 ]] || ! .venv/bin/python -c 'import fastapi, uvicorn, akshare, httpx, pytest' >/dev/null 2>&1; then
  echo "正在安装项目依赖 …"
  if ! .venv/bin/python -m pip install -r requirements.txt; then
    echo "依赖安装失败，请检查网络和 Python 版本，然后重新运行 ./start.sh --install。" >&2
    exit 1
  fi
fi

# Bind only to check occupancy; release immediately before Uvicorn starts.
# An occupied port is never reclaimed or used to stop an existing process.
set +e
.venv/bin/python - "$HOST" "$PORT" <<'PY'
import json
import socket
import sys
import urllib.request

host, raw_port = sys.argv[1:]
try:
    port = int(raw_port)
    if not 1 <= port <= 65535:
        raise ValueError
except ValueError:
    sys.exit('PORT 必须为 1 到 65535 的整数。')
try:
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM, flags=socket.AI_PASSIVE)
    family, kind, protocol, _, address = addresses[0]
    with socket.socket(family, kind, protocol) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(address)
except OSError as exc:
    target = '127.0.0.1' if host == '0.0.0.0' else ('::1' if host == '::' else host)
    target = f'[{target}]' if ':' in target else target
    url = f'http://{target}:{port}'
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url + '/openapi.json', timeout=2) as result:
            schema = json.load(result)
        if schema.get('info', {}).get('title') == '观市 · A股行情工作台':
            print(f'观市服务已运行：{url}；如需应用代码更新，请先在原启动终端按 Ctrl+C 停止。')
            sys.exit(10)
    except (OSError, ValueError):
        pass
    sys.exit(f'无法使用 {host}:{port}：{exc}。可使用 PORT=8081 ./start.sh 更换端口。')
PY
probe_status=$?
set -e
if [[ "$probe_status" == 10 ]]; then exit 0; fi
if [[ "$probe_status" != 0 ]]; then exit "$probe_status"; fi

display_host="$HOST"
if [[ "$HOST" == "0.0.0.0" ]]; then display_host="127.0.0.1"; fi
if [[ "$HOST" == "::" ]]; then display_host="::1"; fi
if [[ "$display_host" == *:* ]]; then display_host="[$display_host]"; fi
echo "启动观市：http://$display_host:$PORT"
echo "等待终端出现 Uvicorn running 后打开浏览器；按 Ctrl+C 停止。"
args=(backend.main:app --host "$HOST" --port "$PORT")
if [[ "$reload" == 1 ]]; then args+=(--reload); fi
exec .venv/bin/python -m uvicorn "${args[@]}"
