# Eron Dashboard — Deployment

Dashboard remoto de métricas do servidor.

## Local Setup

```bash
cd eron-dashboard
pip install -r requirements.txt
python app.py
```

Acessa: `http://localhost:8088`

## Docker Deploy (Remoto)

```bash
# SSH to server
ssh -i ~/.ssh/id_ed25519 eronp@100.92.163.25

# Clone repo
cd ~ && git clone https://github.com/Eronponce/Eron-Dashboard.git

# Deploy
cd Eron-Dashboard
docker compose up -d

# Check logs
docker logs eron-dashboard
```

Acessa: `http://100.92.163.25:8088` (via Tailscale)

## Container Info

- **Image**: Python 3.12-slim + Flask
- **Port**: 8088 → 8088
- **Volume**: `/data/` → SQLite DB + metrics.db
- **Access**: `/var/run/docker.sock` (monitorar containers)
- **Host mount**: `/` (leitura-apenas de disco/temperatura/rede)

## Métricas Coletadas

- CPU % (+ load avg)
- RAM % (+ GB usados + Swap %)
- Temperatura CPU °C (+ fan RPM)
- Energia RAPL W (CPU TDP)
- Disco % (+ GB usados + I/O MB/s)
- Rede MB/s (RX/TX)
- Docker containers (CPU % + RAM MB/%)

Histórico: 90 dias (limpeza automática).

## API

### Current Status
```bash
curl http://100.92.163.25:8088/api/current
```

Retorna snapshot atual + todos containers.

### History
```bash
curl 'http://100.92.163.25:8088/api/history?metric=cpu&range=24h'
curl 'http://100.92.163.25:8088/api/history?metric=temp&range=7d'
```

Ranges: `1h`, `6h`, `24h`, `7d`

Métricas válidas: `cpu`, `ram`, `swap`, `load1`, `temp`, `fan_rpm`, `watts`, `disk`, `disk_read`, `disk_write`, `net_rx`, `net_tx`

## Rebuild

```bash
ssh eronp@100.92.163.25 'cd ~/Eron-Dashboard && git pull && docker compose up --build -d'
```

## Troubleshoot

### Sem dados de temperatura
Remoto precisa acesso a `sensors`. Se não tiver:
```bash
sudo apt install lm-sensors
sudo sensors-detect  # select YES all
```

### Sem dados de energia (RAPL)
Arquivo deve existir: `/sys/class/powercap/intel-rapl:0/energy_uj`

Se não, significa CPU não suporta RAPL (ARM, Ryzen antigo, etc).

### Container OOM
Aumentar limite em `docker-compose.yml`:
```yaml
services:
  dashboard:
    deploy:
      resources:
        limits:
          memory: 256m
```

Então: `docker compose up -d`
