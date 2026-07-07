# Mirror Server — Digital Logic Sim

Servidor Node.js + SQLite que espelha o Firestore e serve o professor como cache de leitura, eliminando reads diretos do browser ao Firebase durante correções.

**Rodando em:** Ubuntu 24.04 · `100.92.163.25:3001` · gerenciado por PM2 (sem Docker)
**Admin token:** `5d06667cf2656ddde06f4a5caa9f4870ec14412e`
**SQLite:** `/home/eronp/mirror-server/data/mirror.db`
**Source local:** `C:\Eron_Lab\Digital-Logic-Sim-Teacher-Web\read-mirror-server\`

---

## Acesso Rápido

```bash
# Status do processo
ssh eronp@100.92.163.25 'npx pm2 status'

# Logs ao vivo
ssh eronp@100.92.163.25 'npx pm2 logs mirror-server --lines 50'

# Reiniciar após deploy de código
ssh eronp@100.92.163.25 'cd ~/mirror-server && npx pm2 restart mirror-server'

# Forçar sync manual
curl -s -X POST http://100.92.163.25:3001/api/admin/sync \
  -H "Authorization: Bearer 5d06667cf2656ddde06f4a5caa9f4870ec14412e"

# Status do agendador
curl -s http://100.92.163.25:3001/api/admin/status \
  -H "Authorization: Bearer 5d06667cf2656ddde06f4a5caa9f4870ec14412e" | jq .

# Relatório de telemetria (últimas 24h)
FROM=$(node -e "console.log(Date.now()-86400000)")
TO=$(node -e "console.log(Date.now())")
curl -s "http://100.92.163.25:3001/api/admin/telemetry/report?since=$FROM&until=$TO" \
  -H "Authorization: Bearer 5d06667cf2656ddde06f4a5caa9f4870ec14412e" | jq .
```

---

## Arquitetura

```
[Teacher Web — browser do professor]
        │
        │  VITE_READ_API_BASE_URL=http://100.92.163.25:3001
        │  Acesso via Tailscale (só professor conectado)
        ▼
[Mirror Server — Node.js + Express + SQLite]
        │
        │  Firebase Admin SDK (bypassa Security Rules 100%)
        │  Lê Firestore apenas no sync programado
        ▼
[Firestore — logisim-eron]
```

**Importante:** Mirror só está acessível via Tailscale. Alunos (sem Tailscale) chamam o Firestore diretamente. Só o professor beneficia do cache.

### Política de Cache — chips

Desde 2026-06-23, o mirror serve chips **sempre do SQLite** para projetos já cacheados:
- `GET /api/users/:uid/projects/:projectId` → se projeto existe no SQLite → retorna do cache, **nunca** vai ao Firestore para chips
- `?refresh=1` → força re-sync do Firestore (único caso que bypassa cache)
- Chips desatualizados → resolvidos no próximo sync horário

---

## Agendamento de Sync

Sync dispara uma vez por hora, apenas nas horas configuradas (horário local do servidor):

```
12h, 14h, 16h, 18h, 19h, 20h, 21h, 22h, 23h
```

Lógica: um tick de 60s verifica se a hora atual está na lista **e** se o último sync foi antes do início da hora atual. Garante exatamente 1 sync por slot.

**Sem sync noturno** (0h–11h): quota Firestore descansa, nenhuma leitura do mirror.

---

## Endpoints

### Públicos (sem autenticação)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/users/:uid/projects` | Lista projetos cacheados do usuário |
| `GET` | `/api/users/:uid/projects?name=X` | Busca projeto por nome (case-insensitive) |
| `GET` | `/api/users/:uid/projects/:projectId` | Projeto + todos os chips |
| `GET` | `/api/users/:uid/projects/:projectId?refresh=1` | Idem, força re-sync do Firestore |
| `POST` | `/api/telemetry` | Recebe eventos de telemetria do browser |

### Admin (requer `Authorization: Bearer <token>`)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/admin/sync` | Força sync completo imediato |
| `GET` | `/api/admin/status` | Status do agendador + último sync |
| `GET` | `/api/admin/telemetry/report?since=&until=` | Relatório de leituras por tela/path/hora |

---

## Telemetria

O sistema registra eventos de três origens no SQLite (`telemetry_events`):

### 1. Mirror interno (automático)
Toda chamada ao Firestore ou SQLite feita pelo mirror é registrada via `stats.ts` → `recordMirrorEvent()` → `insertTelemetryEvent()`.

### 2. Browser do professor (flush assíncrono)
`teacher-web/src/request-log.ts` captura todos os Firebase calls do browser e envia em batch a cada 3s (ou 20 eventos) via `POST /api/telemetry`. Eventos incluem:
- `screen`: tela ativa no momento da chamada (ex: `"VerifyScreen"`, `"ResultsScreen"`)
- `sessionId`: ID da sessão do browser
- `runtime`: `"browser"`

### 3. Relatório analítico
```
GET /api/admin/telemetry/report?since=<ms>&until=<ms>

Resposta:
{
  period: { from, to },
  byScreen: [{ screen, reads, calls }],
  byPath: [{ path, calls, reads }],
  byHour: [{ hour, reads }],
  totals: { firestoreReads, firestoreWrites, events, mirrorCalls }
}
```

Retenção: 30 dias. Purge automático no startup.

---

## Log Estruturado de Sync

Cada sync bem-sucedido emite uma linha no formato:

```
[sync] ✓ 12.3s | assignments:3 runs:8 results:45 users:12 | chips: 89 synced, 72 cache, 17 firestore (~34 reads)
```

- `chips synced`: total de chips processados
- `cache`: chips servidos do SQLite sem ir ao Firestore
- `firestore`: chips que precisaram de leitura no Firestore
- `~N reads`: estimativa de reads consumidos no ciclo

---

## Bug Raiz (corrigido 2026-06-23)

**Arquivo:** `src/sync.ts`, função `syncStudentProjectChips`

**Causa:** Lookup SQLite usava só `lower(project_name)`. Quando o campo `projectName` no roster do professor era o **doc ID** do Firestore (não o nome display), nunca batia → path A toda ciclo → lia TODO o projeto do Firestore a cada sync.

**Fix:**
```sql
-- Antes:
WHERE user_uid = ? AND lower(project_name) = ?

-- Depois:
WHERE user_uid = ? AND (lower(project_name) = ? OR lower(project_id) = ?)
```

**Impacto:** Eliminava loop de ~7.600 reads/dia confirmados + cascata de chips. De 103k reads/dia → esperado <10k em dias de aula.

---

## Estrutura de Arquivos

```
read-mirror-server/
├── src/
│   ├── index.ts          → entry point, Express setup, PM2
│   ├── db.ts             → SQLite init, schema, telemetry_events, funções de query
│   ├── sync.ts           → lógica de sync Firestore→SQLite
│   ├── stats.ts          → recordMirrorEvent(), persiste em SQLite
│   ├── schedule.ts       → agendador de sync por hora fixa
│   ├── observability.ts  → wrappers trackedSqlite*/trackedFirestore*
│   └── routes/
│       ├── chips.ts      → GET /api/users/:uid/projects/*
│       └── admin.ts      → POST /api/admin/sync, telemetry endpoints
├── data/
│   └── mirror.db         → SQLite (criado automaticamente)
└── package.json
```

### Schema SQLite principal

| Tabela | Conteúdo |
|--------|----------|
| `projects` | uid, project_id, project_name, project_data, chips_synced_at |
| `chips` | uid, project_id, chip_name, chip_data |
| `validation_runs` | run_id, assignment_id, created_at |
| `validation_results` | run_id, student_id, status, details |
| `assignments` | assignment_id, teacher_uid, title |
| `sync_cursors` | key/value (ex: `last_sync_at`) |
| `telemetry_events` | ts, runtime, screen, system, op, label, outcome, reads, writes, trace_id, session_id |

---

## Deploy de Código

```bash
# 1. Copiar arquivos modificados para o servidor
scp -r C:\Eron_Lab\Digital-Logic-Sim-Teacher-Web\read-mirror-server\src\ eronp@100.92.163.25:~/mirror-server/src/

# 2. Compilar e reiniciar
ssh eronp@100.92.163.25 'cd ~/mirror-server && npm run build && npx pm2 restart mirror-server'

# 3. Verificar logs
ssh eronp@100.92.163.25 'npx pm2 logs mirror-server --lines 30'
```

---

## Variáveis de Ambiente (servidor remoto)

| Variável | Valor |
|----------|-------|
| `GOOGLE_APPLICATION_CREDENTIALS` | `/home/eronp/mirror-server/logisim-eron-firebase-adminsdk-*.json` |
| `MIRROR_ADMIN_TOKEN` | `5d06667cf2656ddde06f4a5caa9f4870ec14412e` |
| `PORT` | `3001` |

---

## Diagnóstico Rápido

```bash
# Ver quantos projetos/chips estão no cache
ssh eronp@100.92.163.25 'node -e "
const {DatabaseSync} = require(\"node:sqlite\");
const db = new DatabaseSync(\"/home/eronp/mirror-server/data/mirror.db\");
const p = db.prepare(\"SELECT COUNT(*) as n FROM projects\").get();
const c = db.prepare(\"SELECT COUNT(*) as n FROM chips\").get();
console.log(\"projects:\", p.n, \"chips:\", c.n);
"'

# Ver último sync
curl -s http://100.92.163.25:3001/api/admin/status \
  -H "Authorization: Bearer 5d06667cf2656ddde06f4a5caa9f4870ec14412e" \
  | node -e "const d=require('fs').readFileSync(0,'utf8');const j=JSON.parse(d);console.log('lastSync:',new Date(j.lastSyncAt),'running:',j.syncRunning)"
```
