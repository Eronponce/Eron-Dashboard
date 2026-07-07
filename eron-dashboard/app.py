import os, time, threading, sqlite3, subprocess, json
from flask import Flask, jsonify, render_template, request
import psutil
import docker as docker_sdk

app = Flask(__name__)
DB = '/data/metrics.db'
RAPL = '/sys/class/powercap/intel-rapl:0/energy_uj'

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def init_db():
    os.makedirs('/data', exist_ok=True)
    with sqlite3.connect(DB) as c:
        c.execute('''CREATE TABLE IF NOT EXISTS metrics (
            ts INTEGER PRIMARY KEY,
            cpu REAL, ram REAL, ram_gb REAL,
            swap REAL, load1 REAL,
            temp REAL, fan_rpm REAL,
            watts REAL,
            disk REAL, disk_gb REAL,
            disk_read REAL, disk_write REAL,
            net_rx REAL, net_tx REAL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS containers (
            ts INTEGER, name TEXT, cpu REAL, mem_mb REAL, mem_pct REAL,
            PRIMARY KEY (ts, name)
        )''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_ts ON metrics(ts)')
        # migrate old DB without new columns
        existing = {r[1] for r in c.execute('PRAGMA table_info(metrics)')}
        for col, typ in [('swap','REAL'),('load1','REAL'),('fan_rpm','REAL'),
                         ('disk_read','REAL'),('disk_write','REAL')]:
            if col not in existing:
                c.execute(f'ALTER TABLE metrics ADD COLUMN {col} {typ}')


# ---------------------------------------------------------------------------
# Collectors
# ---------------------------------------------------------------------------

_rapl_prev = {}
_net_prev = {}
_disk_prev = {}


def read_watts():
    try:
        with open(RAPL) as f:
            energy = int(f.read().strip())
        now = time.time()
        if _rapl_prev:
            dt = now - _rapl_prev['t']
            w = (energy - _rapl_prev['e']) / dt / 1e6 if dt > 0 else None
            _rapl_prev.update({'e': energy, 't': now})
            wr = round(w, 2) if w is not None else None
            return wr if wr and wr > 0 else None
        _rapl_prev.update({'e': energy, 't': now})
    except Exception:
        pass
    return None


def read_temp_fan():
    temp = fan = None
    try:
        result = subprocess.run(['sensors', '-j'], capture_output=True, text=True, timeout=5)
        data = json.loads(result.stdout)
        # coretemp Package id 0 → most accurate
        for adapter, sensors in data.items():
            if 'coretemp' in adapter:
                for key, val in sensors.items():
                    if isinstance(val, dict) and 'Package' in key:
                        for k, v in val.items():
                            if 'input' in k and isinstance(v, (int, float)):
                                temp = round(v, 1)
                                break
                    if temp is not None:
                        break
                break
        # fallback: dell_smm CPU sensor
        if temp is None:
            for adapter, sensors in data.items():
                if 'dell_smm' in adapter:
                    for key, val in sensors.items():
                        if isinstance(val, dict) and key == 'CPU':
                            for k, v in val.items():
                                if 'input' in k and isinstance(v, (int, float)):
                                    temp = round(v, 1)
                                    break
                    break
        # fan: dell_smm Processor Fan
        for adapter, sensors in data.items():
            if 'dell_smm' in adapter:
                for key, val in sensors.items():
                    if isinstance(val, dict) and 'Fan' in key:
                        for k, v in val.items():
                            if 'input' in k and isinstance(v, (int, float)):
                                fan = round(v, 0)
                                break
                break
    except Exception as e:
        print(f'[sensors] {e}')
    return temp, fan


def read_net():
    try:
        with open('/proc/1/net/dev') as f:
            lines = f.readlines()[2:]
        rx = tx = 0
        for line in lines:
            parts = line.split()
            iface = parts[0].rstrip(':')
            if iface.startswith(('enp', 'eth', 'ens', 'tailscale')):
                rx += int(parts[1])
                tx += int(parts[9])
        now = time.time()
        net_rx = net_tx = None
        if _net_prev:
            dt = now - _net_prev['t']
            if dt > 0:
                net_rx = round((rx - _net_prev['rx']) / dt / 1024**2, 3)
                net_tx = round((tx - _net_prev['tx']) / dt / 1024**2, 3)
        _net_prev.update({'rx': rx, 'tx': tx, 't': now})
        return net_rx, net_tx
    except Exception:
        return None, None


def read_disk_io():
    try:
        d = psutil.disk_io_counters()
        now = time.time()
        read_mbs = write_mbs = None
        if _disk_prev:
            dt = now - _disk_prev['t']
            if dt > 0:
                read_mbs = round((d.read_bytes - _disk_prev['r']) / dt / 1024**2, 3)
                write_mbs = round((d.write_bytes - _disk_prev['w']) / dt / 1024**2, 3)
        _disk_prev.update({'r': d.read_bytes, 'w': d.write_bytes, 't': now})
        return read_mbs, write_mbs
    except Exception:
        return None, None


def read_containers():
    result = []
    try:
        client = docker_sdk.from_env()
        for c in client.containers.list():
            try:
                s = c.stats(stream=False)
                cpu_d = s['cpu_stats']['cpu_usage']['total_usage'] - s['precpu_stats']['cpu_usage']['total_usage']
                sys_d = s['cpu_stats']['system_cpu_usage'] - s['precpu_stats']['system_cpu_usage']
                ncpu = s['cpu_stats'].get('online_cpus') or len(s['cpu_stats']['cpu_usage'].get('percpu_usage', [1]))
                cpu_pct = round((cpu_d / sys_d) * ncpu * 100, 2) if sys_d > 0 else 0
                mem_u = s['memory_stats'].get('usage', 0)
                mem_l = s['memory_stats'].get('limit', 1)
                result.append({
                    'name': c.name,
                    'cpu': cpu_pct,
                    'mem_mb': round(mem_u / 1024**2, 1),
                    'mem_pct': round(mem_u / mem_l * 100, 1)
                })
            except Exception:
                pass
    except Exception:
        pass
    return result


def collect():
    ts = int(time.time())
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    load1 = round(os.getloadavg()[0], 2)
    disk = psutil.disk_usage('/host') if os.path.ismount('/host') else psutil.disk_usage('/')
    temp, fan = read_temp_fan()
    watts = read_watts()
    net_rx, net_tx = read_net()
    disk_read, disk_write = read_disk_io()
    containers = read_containers()

    with sqlite3.connect(DB) as c:
        c.execute(
            '''INSERT OR REPLACE INTO metrics
               (ts, cpu, ram, ram_gb, swap, load1, temp, fan_rpm, watts,
                disk, disk_gb, disk_read, disk_write, net_rx, net_tx)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (ts, cpu,
             round(mem.percent, 1), round(mem.used / 1024**3, 2),
             round(swap.percent, 1), load1,
             temp, fan,
             watts,
             round(disk.percent, 1), round(disk.used / 1024**3, 2),
             disk_read, disk_write,
             net_rx, net_tx)
        )
        for ct in containers:
            c.execute('INSERT OR REPLACE INTO containers VALUES (?,?,?,?,?)',
                      (ts, ct['name'], ct['cpu'], ct['mem_mb'], ct['mem_pct']))
        cutoff = ts - 90 * 86400
        c.execute('DELETE FROM metrics WHERE ts < ?', (cutoff,))
        c.execute('DELETE FROM containers WHERE ts < ?', (cutoff,))


INTERVAL = 15

_last_collect = 0.0
_collect_lock = threading.Lock()

def maybe_collect():
    global _last_collect
    now = time.time()
    if now - _last_collect < INTERVAL - 1:
        return
    with _collect_lock:
        if time.time() - _last_collect < INTERVAL - 1:
            return
        try:
            collect()
            _last_collect = time.time()
        except Exception as e:
            print(f'[collector] {e}')

def collector_loop():
    while True:
        maybe_collect()
        time.sleep(INTERVAL)

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

RANGES = {'1h': 3600, '6h': 21600, '24h': 86400, '7d': 604800}
VALID_METRICS = {'cpu', 'ram', 'swap', 'load1', 'temp', 'fan_rpm',
                 'watts', 'disk', 'disk_read', 'disk_write', 'net_rx', 'net_tx'}


@app.route('/api/current')
def api_current():
    maybe_collect()
    with sqlite3.connect(DB) as c:
        row = c.execute(
            'SELECT ts, cpu, ram, ram_gb, swap, load1, temp, fan_rpm, watts, '
            'disk, disk_gb, disk_read, disk_write, net_rx, net_tx '
            'FROM metrics ORDER BY ts DESC LIMIT 1'
        ).fetchone()
        ctrs = c.execute(
            'SELECT name, cpu, mem_mb, mem_pct FROM containers WHERE ts=(SELECT MAX(ts) FROM containers)'
        ).fetchall()
    if not row:
        return jsonify({})
    keys = ['ts', 'cpu', 'ram', 'ram_gb', 'swap', 'load1',
            'temp', 'fan_rpm', 'watts', 'disk', 'disk_gb',
            'disk_read', 'disk_write', 'net_rx', 'net_tx']
    data = dict(zip(keys, row))
    data['containers'] = [{'name': r[0], 'cpu': r[1], 'mem_mb': r[2], 'mem_pct': r[3]} for r in ctrs]
    return jsonify(data)


@app.route('/api/history')
def api_history():
    metric = request.args.get('metric', 'cpu')
    if metric not in VALID_METRICS:
        return jsonify({'error': 'invalid metric'}), 400
    range_key = request.args.get('range', '24h')
    seconds = RANGES.get(range_key, 86400)
    cutoff = int(time.time()) - seconds
    bucket = {'7d': 3600, '24h': 300, '6h': 60}.get(range_key, 0)

    with sqlite3.connect(DB) as c:
        if bucket:
            rows = c.execute(
                f'SELECT (ts/{bucket})*{bucket}, AVG({metric}) FROM metrics '
                f'WHERE ts>? AND {metric} IS NOT NULL GROUP BY 1 ORDER BY 1',
                (cutoff,)
            ).fetchall()
        else:
            rows = c.execute(
                f'SELECT ts, {metric} FROM metrics WHERE ts>? AND {metric} IS NOT NULL ORDER BY ts',
                (cutoff,)
            ).fetchall()

    return jsonify({'labels': [r[0] * 1000 for r in rows],
                    'values': [r[1] for r in rows]})


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    init_db()
    read_watts(); read_net(); read_disk_io()
    threading.Thread(target=collector_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=8088, debug=False)
