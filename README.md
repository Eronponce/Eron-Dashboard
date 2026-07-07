# Infraestrutura Remota — Eron Lab

Servidor remoto: **Dell Latitude 7490** rodando Ubuntu 24.04, acessível via Tailscale.

---

## Acesso Rápido

```bash
ssh -i ~/.ssh/id_rsa eronp@100.92.163.25   # Tailscale (preferido)
ssh -i ~/.ssh/id_rsa eronp@189.90.67.22    # IP público (fallback)
```

**Teste de conexão:**
```bash
ssh -i ~/.ssh/id_rsa -o BatchMode=yes eronp@100.92.163.25 'echo OK'
```

---

## Hardware

| | |
|---|---|
| Máquina | Dell Latitude 7490 |
| CPU | Intel Core i7-8650U (4c/8t, 1.9–4.2 GHz) |
| RAM | 7.6 GiB + 4 GiB Swap |
| Disco | SSD LITEON 256 GB |
| OS | Ubuntu 24.04.4 LTS (kernel 6.8.0-107) |
| User | `eronp` |

---

## Serviços Rodando

| Serviço | URL | Porta | Status |
|---|---|---|---|
| UniFil Exams | http://100.92.163.25:3000 | 3000 | ✅ always-on (Docker) |
| Canvas API | http://100.92.163.25:5000 | 5000 | ✅ always-on (Docker) |
| LanguageTool | http://100.92.163.25:8081 | 8081 | ✅ always-on (Docker) |
| **Mirror Server** | **http://100.92.163.25:3001** | **3001** | **✅ always-on (PM2)** |
| Netdata (monit.) | http://100.92.163.25:19999 | 19999 | ✅ always-on |

---

## Arquitetura

```
Internet / Tailscale
        │
        ├── :3000 ──► [unifil-exams-release]  Next.js app + SQLite (Docker)
        │
        ├── :5000 ──► [canvas-bulk-panel]     Flask app + SQLite (Docker)
        │
        ├── :8081 ──► [eron-languagetool-proxy]  Python HTTP proxy (Docker)
        │                       │
        │               converte JSON → form-encoded
        │               normaliza /check → /v2/check
        │                       │
        │              :8082 ──► [eron-languagetool]  Java LT server (Docker)
        │
        ├── :3001 ──► [mirror-server]  Node.js + SQLite (PM2, não Docker)
        │                       │
        │               espelha Firestore → SQLite local
        │               serve leituras do professor sem bater Firebase
        │               sync programado: 12h,14h,16h,18h,19h,20h,21h,22h,23h
        │
        └── :19999 ──► [Netdata]  monitoramento (host, não Docker)
```

### Por que o proxy no LanguageTool?

A extensão Chrome (`webextension-chrome-ng` v11) envia JSON no body e usa `/check`.
O servidor Java do LanguageTool só aceita `application/x-www-form-urlencoded` e rota `/v2/check`.
O proxy Python faz a conversão transparentemente e adiciona headers CORS.

---

## Diretórios no Remoto

```
~/UniFil-Exams/          → código + compose
~/Canva_Api/             → código + compose
~/Eron_language_tool/    → código + compose + docker/proxy.py
```

---

## Comandos Úteis

### Ver status de todos os containers
```bash
ssh eronp@100.92.163.25 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
```

### Ver uso de recursos (CPU/RAM por container)
```bash
ssh eronp@100.92.163.25 'docker stats --no-stream'
```

### Ver logs de um serviço
```bash
ssh eronp@100.92.163.25 'docker logs eron-languagetool --tail 50'
ssh eronp@100.92.163.25 'docker logs canvas-bulk-panel --tail 50'
ssh eronp@100.92.163.25 'docker logs unifil-exams-release --tail 50'
```

### Temperaturas e fan
```bash
ssh eronp@100.92.163.25 'sensors'
```

### Atualizar um serviço (git pull + rebuild)
```bash
# UniFil Exams
ssh eronp@100.92.163.25 'cd ~/UniFil-Exams && git pull && docker compose up --build -d'

# Canvas API
ssh eronp@100.92.163.25 'cd ~/Canva_Api && git pull && docker compose up --build -d'

# LanguageTool
ssh eronp@100.92.163.25 'cd ~/Eron_language_tool && git pull && docker compose up --build -d'
```

### Reiniciar um serviço sem rebuild
```bash
ssh eronp@100.92.163.25 'docker restart canvas-bulk-panel'
ssh eronp@100.92.163.25 'docker restart eron-languagetool eron-languagetool-proxy'
ssh eronp@100.92.163.25 'docker restart unifil-exams-release'
```

### Parar/subir tudo
```bash
# parar
ssh eronp@100.92.163.25 'cd ~/Canva_Api && docker compose down'

# subir
ssh eronp@100.92.163.25 'cd ~/Canva_Api && docker compose up -d'
```

---

## Guias por Serviço

- [UniFil Exams](./unifil-exams.md)
- [Canvas API](./canvas-api.md)
- [LanguageTool](./languagetool.md)
- [Mirror Server (Digital Logic Sim)](./mirror-server.md)

---

## Firebase — Digital Logic Sim

O projeto **Digital Logic Sim Teacher Web** usa Firebase (Firestore) como banco de dados principal para armazenar projetos dos alunos, resultados de avaliação e sincronização com o jogo Unity.

### Credenciais

Arquivo de service account (Admin SDK):

```
C:\Eron_Lab\conexao-remota\logisim-eron-firebase-adminsdk-fbsvc-3f27613a5a.json
```

| Campo | Valor |
|---|---|
| **Project ID** | `logisim-eron` |
| **Service Account** | `firebase-adminsdk-fbsvc@logisim-eron.iam.gserviceaccount.com` |
| **Key ID** | `3f27613a5a6836db4edcacbf34d450e5abd61e03` |

> ⚠️ Nunca versionar este arquivo. Nunca subir para o GitHub.

### Como usar nas funções Firebase

O arquivo de credenciais é referenciado via variável de ambiente ou caminho direto ao inicializar o Admin SDK:

```ts
// functions/src/index.ts (ou similar)
import * as admin from 'firebase-admin';
import serviceAccount from 'C:/Eron_Lab/conexao-remota/logisim-eron-firebase-adminsdk-fbsvc-3f27613a5a.json';

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount as admin.ServiceAccount),
});
```

Em produção (Cloud Functions deploy), as credenciais são injetadas automaticamente pelo ambiente Firebase — o arquivo local é só para desenvolvimento e scripts locais.

### Arquitetura — Digital Logic Sim

```
[Unity Game — DLS]
        │
        │  salva projetos via Firebase SDK (cliente)
        ▼
[Firestore — logisim-eron]
        │
        │  lê/avalia via Admin SDK
        ▼
[Teacher Web — Next.js/React]   ←──  Professor monitora alunos
        │
        │  Cloud Functions (avaliação lógica)
        ▼
[ValidationStatus por aluno]
   PASSED / FAILED / PASSED_WITH_REMAP / ...
```

### Projetos Relacionados

| Repo | Caminho local | Descrição |
|---|---|---|
| Digital-Logic-Sim-Teacher-Web | `C:\Eron_Lab\Digital-Logic-Sim-Teacher-Web` | Frontend professor + Cloud Functions de avaliação |
| Digital-Logic-Sim-Unifil | *(Unity project)* | Jogo Unity que os alunos usam para montar circuitos |
