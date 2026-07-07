# Eron Infrastructure — Integration Guide

Infraestrutura remota dockerizada. Serviços integrados via Tailscale (100.92.163.25).

---

## Serviços

### 1. UniFil Exams (Porto 3000)
- **Tech**: Next.js + SQLite
- **Status**: always-on (Docker)
- **Repo**: github.com/Eronponce/UniFil-Exams
- **Acessar**: `http://100.92.163.25:3000`

### 2. Canvas API (Porto 5000)
- **Tech**: Flask + SQLite
- **Status**: always-on (Docker)
- **Repo**: github.com/Eronponce/Canva_Api
- **Acessar**: `http://100.92.163.25:5000`

### 3. LanguageTool (Porto 8081/8082)
- **Tech**: Java (8082) + Python proxy (8081)
- **Status**: always-on (Docker)
- **Repo**: github.com/Eronponce/Eron_language_tool
- **Fluxo**: Chrome WebExtension → :8081 (proxy) → :8082 (Java server)
- **Proxy**: converte JSON → form-encoded, normaliza rotas
- **Acessar**: `http://100.92.163.25:8081`

### 4. Eron Dashboard (Porto 8088) ⭐
- **Tech**: Flask + SQLite + psutil
- **Status**: always-on (Docker)
- **Repo**: github.com/Eronponce/Eron-Dashboard
- **O quê monitora**: CPU, RAM, temperatura, disco, rede, containers Docker
- **Dados**: coletados a cada 15s, histórico 90 dias
- **Acessar**: `http://100.92.163.25:8088`
- **API**: `/api/current` (snapshot), `/api/history?metric=CPU&range=24h`

### 5. Mirror Server (Porto 3001)
- **Tech**: Node.js + SQLite
- **Status**: always-on (PM2, **não Docker**)
- **Função**: espelha Firestore → SQLite local
- **Sync**: automático 12h,14h,16h,18h,19h,20h,21h,22h,23h
- **Por quê**: reduz bater Firebase em leitura de professor
- **Acessar**: `http://100.92.163.25:3001`

### 6. Netdata (Porto 19999)
- **Tech**: Netdata (host)
- **Status**: always-on
- **Função**: monitoramento histórico do host
- **Acessar**: `http://100.92.163.25:19999`

---

## Eron Dashboard — Detalhes

O **Eron Dashboard** é serviço de observabilidade centralizado do servidor Dell Latitude.

### Arquitetura

```
┌─────────────────────────────────────────┐
│  Eron Dashboard (Flask)                 │
│  :8088 — Tailscale 100.92.163.25       │
├─────────────────────────────────────────┤
│ Collector (15s interval)                │
│  • CPU %                   (psutil)     │
│  • RAM % + Swap %          (psutil)     │
│  • Load avg                 (os.load)   │
│  • Temperatura CPU °C      (sensors -j) │
│  • Fan RPM                 (sensors -j) │
│  • Energia RAPL W        (intel-rapl)  │
│  • Disco % + GB           (psutil)     │
│  • Disco I/O MB/s         (psutil)     │
│  • Rede RX/TX MB/s        (/proc/net)  │
│  • Containers CPU/RAM     (docker SDK) │
├─────────────────────────────────────────┤
│ SQLite DB (/data/metrics.db)            │
│  • Retenção: 90 dias                    │
│  • Cleanup automático (ts < now - 90d)  │
│  • Índices: ts                          │
├─────────────────────────────────────────┤
│ API REST                                │
│  • /                       (HTML/Charts)│
│  • /api/current            (snapshot)   │
│  • /api/history (métrica + range)       │
└─────────────────────────────────────────┘
```

### Integração com outros containers

Dashboard acessa:
- `/var/run/docker.sock` → lista + stats dos containers
- `/sys/class/powercap/...` → energia RAPL
- `/proc/*/net/dev` → rede
- `/` (read-only) → disco, temp, sensores

Monitora automaticamente:
- `unifil-exams-release` (CPU/RAM)
- `canvas-bulk-panel` (CPU/RAM)
- `eron-languagetool` (CPU/RAM) — ⚠️ ~99% RAM limit
- `eron-languagetool-proxy` (CPU/RAM)

### Acessar dados

#### Snapshot atual
```bash
curl -s http://100.92.163.25:8088/api/current | jq
```

Retorna:
```json
{
  "ts": 1783456120,
  "cpu": 18.2,
  "ram": 37.8,
  "ram_gb": 2.58,
  "swap": 1.6,
  "load1": 5.74,
  "temp": 63.0,
  "fan_rpm": 0.0,
  "watts": 3.59,
  "disk": 34.4,
  "disk_gb": 31.95,
  "disk_read": 0.547,
  "disk_write": 0.041,
  "net_rx": 0.002,
  "net_tx": 0.008,
  "containers": [
    {"name": "unifil-exams-release", "cpu": 0.02, "mem_mb": 217.0, "mem_pct": 2.8},
    {"name": "canvas-bulk-panel", "cpu": 0.02, "mem_mb": 142.6, "mem_pct": 1.8},
    ...
  ]
}
```

#### Histórico de métrica
```bash
# CPU últimas 24 horas
curl -s 'http://100.92.163.25:8088/api/history?metric=cpu&range=24h' | jq

# Temperatura últimos 7 dias
curl -s 'http://100.92.163.25:8088/api/history?metric=temp&range=7d' | jq

# RAM — 1 hora
curl -s 'http://100.92.163.25:8088/api/history?metric=ram&range=1h' | jq
```

Ranges: `1h`, `6h`, `24h`, `7d`

Métricas: `cpu`, `ram`, `swap`, `load1`, `temp`, `fan_rpm`, `watts`, `disk`, `disk_read`, `disk_write`, `net_rx`, `net_tx`

---

## Deployment

Todos containers via `docker compose up -d` em seus respectivos diretórios.

### Remoto — paths
```
~/UniFil-Exams/         # git repo, docker-compose.yml
~/Canva_Api/            # git repo, docker-compose.yml
~/Eron_language_tool/   # git repo, docker-compose.yml
~/Eron-Dashboard/       # git repo, docker-compose.yml
```

### Atualizar serviço
```bash
ssh eronp@100.92.163.25 'cd ~/UniFil-Exams && git pull && docker compose up --build -d'
ssh eronp@100.92.163.25 'cd ~/Eron-Dashboard && git pull && docker compose up --build -d'
# etc
```

### Ver status
```bash
ssh eronp@100.92.163.25 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
```

### Ver logs
```bash
ssh eronp@100.92.163.25 'docker logs eron-dashboard --tail 50 -f'
```

### Ver recursos (CPU/RAM por container)
```bash
ssh eronp@100.92.163.25 'docker stats --no-stream'
```

---

## Alertas Conhecidos

⚠️ **eron-languagetool ~99% RAM limit**
- Container limitado a 700 MiB
- Monitorar via Dashboard
- Se OOM ocorrer, aumentar em `docker-compose.yml`:
  ```yaml
  deploy:
    resources:
      limits:
        memory: 1024m
  ```

⚠️ **Fan RPM = 0 (sensor dell_smm)**
- Sensor pode não estar disponível
- Verificar com: `ssh eronp@100.92.163.25 'sensors'`
- Se CPU > 80°C, verificar fisicamente

⚠️ **Build cache Docker: 3.9 GB**
- Liberar com: `ssh eronp@100.92.163.25 'docker builder prune -a -f'`

---

## Próximos Passos

- [ ] Adicionar alertas via Slack/email se CPU > 80% ou temp > 85°C
- [ ] Histórico de alertas (dashboard log)
- [ ] Export de métricas (Prometheus format?)
- [ ] Integração com Netdata (sincronizar dados)
- [ ] Health check de serviços via Dashboard

---

## Suporte

**SSH (preferido via Tailscale):**
```bash
ssh -i ~/.ssh/id_ed25519 eronp@100.92.163.25
```

**Serviço em dúvida?** Verificar logs:
```bash
docker logs <container> --tail 100
```

**Remoto fora do ar?** Verificar:
```bash
ping 100.92.163.25              # conectado?
ssh ... 'uptime'                # ligado?
ssh ... 'docker ps'             # containers rodando?
```
