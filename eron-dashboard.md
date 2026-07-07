# Eron Dashboard — Guia Completo

URL de acesso: `http://100.92.163.25:8088`

Dashboard customizado de monitoramento do servidor. Mostra CPU, RAM, temperatura, consumo de energia (Intel RAPL), disco, rede e containers Docker — com histórico de 90 dias.

---

## Arquitetura

```
Browser
  │  HTTP :8088
  ▼
[eron-dashboard]  Docker container (privileged + pid:host)
  Flask app (Python 3.12-slim)
  Collector thread: a cada 15s → SQLite /data/metrics.db
  porta interna: 8088
  dados em: volume Docker dashboard_data → /data/metrics.db
```

---

## Localização

| Local | Path |
|---|---|
| Código-fonte (Windows) | `C:\Eron_Lab\conexao-remota\eron-dashboard\` |
| Deploy no servidor | `/home/eronp/eron-dashboard/` |
| Banco de dados | volume Docker `eron-dashboard_dashboard_data` |

---

## Métricas coletadas

| Métrica | Fonte | Intervalo |
|---|---|---|
| CPU % | psutil | 15s |
| RAM % + GB | psutil | 15s |
| Swap % | psutil | 15s |
| Load average (1min) | os.getloadavg() | 15s |
| Temperatura CPU | `sensors -j` → coretemp Package id 0 | 15s |
| Fan RPM | `sensors -j` → dell_smm Processor Fan | 15s |
| Consumo energia (W) | Intel RAPL `/sys/class/powercap/intel-rapl:0/energy_uj` | 15s |
| Disco % + GB | psutil `/host` (mount do host) | 15s |
| Disco I/O (MB/s) | psutil disk_io_counters | 15s |
| Rede RX/TX (KB/s) | `/proc/1/net/dev` (interfaces enp*, tailscale*) | 15s |
| Docker containers | Docker SDK (CPU%, RAM MB, RAM%) | 15s |

---

## Histórico

- Retenção: **90 dias**
- Resolução raw: 15s
- Agregação automática na API:
  - 1H → raw (15s)
  - 6H → bucket 60s
  - 24H → bucket 5min
  - 7D → bucket 1h

---

## Deploy e rebuild

```bash
# No servidor remoto
cd ~/eron-dashboard
docker compose down
docker compose build
docker compose up -d

# Ou via Claude (SSH automático com chave ~/.ssh/id_ed25519):
# SCP dos arquivos + rebuild
```

```bash
# Ver logs
docker logs eron-dashboard -f

# Ver DB
docker exec eron-dashboard python3 -c "
import sqlite3
conn = sqlite3.connect('/data/metrics.db')
print(conn.execute('SELECT COUNT(*) FROM metrics').fetchone())
"
```

---

## Dependências do container

```
privileged: true   → leitura RAPL (/sys/class/powercap/)
pid: host          → psutil lê métricas do host via /proc
/:/host:ro         → psutil.disk_usage('/host') = disco real do host
/var/run/docker.sock → Docker SDK para stats dos containers
lm-sensors         → comando `sensors -j` para temperatura/fan
```

---

## Estrutura dos arquivos

```
eron-dashboard/
├── Dockerfile          # python:3.12-slim + lm-sensors
├── docker-compose.yml  # privileged, pid:host, volumes
├── requirements.txt    # flask, psutil, docker, gunicorn
├── app.py              # Flask app + collector thread + API
└── templates/
    └── index.html      # Dashboard UI (Chart.js + CSS puro)
```

---

## API endpoints

| Endpoint | Descrição |
|---|---|
| `GET /` | Dashboard UI |
| `GET /api/current` | Métricas mais recentes + containers |
| `GET /api/history?metric=cpu&range=24h` | Histórico agregado |

Métricas válidas: `cpu`, `ram`, `swap`, `load1`, `temp`, `fan_rpm`, `watts`, `disk`, `disk_read`, `disk_write`, `net_rx`, `net_tx`

Ranges válidos: `1h`, `6h`, `24h`, `7d`

---

## Alertas visuais (UI)

| Condição | Visual |
|---|---|
| Temperatura ≥ 85°C | Vermelho |
| Temperatura ≥ 70°C | Laranja |
| Container RAM ≥ 95% | Vermelho |
| Container RAM ≥ 80% | Laranja |

---

## Histórico de problemas e soluções

| Problema | Causa | Fix |
|---|---|---|
| Temperatura 0.4°C | psutil hwmon mapping errado no container | `sensors -j` subprocess |
| Disco 0.0% | psutil lê `/` do container (overlay) | mount `/:/host:ro` |
| Colunas invertidas no DB | ALTER TABLE adiciona colunas no final, INSERT usava `VALUES (?,...)` sem nomes | INSERT com nomes explícitos |
| Gráfico rede sempre 0 | `round(0.001, 2) = 0.0` na API | Removido round() na resposta |
| Gráfico cai a 0 no gap | `fill: true` + gap de NULL | `spanGaps: true` nos datasets |
| Build com código antigo | `docker compose restart` não rebuilda | Sempre usar `build + up` |
