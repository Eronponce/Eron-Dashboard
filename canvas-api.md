# Canvas API — Guia Completo

URL de acesso: `http://100.92.163.25:5000`

Painel Flask para gerenciar comunicados, mensagens e recorrências no Canvas LMS via API oficial.

---

## Arquitetura

```
Browser
  │  HTTP :5000
  ▼
[canvas-bulk-panel]  Docker container
  Flask app (Python 3.12-slim)
  porta interna: 5000
  dados persistidos em: ./data/  (volume)
  config em: ./.env              (volume)
```

---

## Configuração

### Variáveis de ambiente (.env no remoto)

Arquivo em `~/Canva_Api/.env` — montado como volume no container.

Variáveis principais:
```env
CANVAS_BASE_URL=https://sua-instituicao.instructure.com
CANVAS_BASE_URL_TEST=https://sua-instituicao.test.instructure.com
```

O token de acesso é informado pelo usuário diretamente na interface (não fica no .env).

### Editar o .env no remoto
```bash
ssh -i ~/.ssh/id_rsa eronp@100.92.163.25 'nano ~/Canva_Api/.env'
# após editar, reiniciar:
docker restart canvas-bulk-panel
```

---

## Atualizar / Redesplegar

```bash
ssh -i ~/.ssh/id_rsa eronp@100.92.163.25 \
  'cd ~/Canva_Api && git pull && docker compose up --build -d'
```

> Se o git pull falhar por mudanças locais no remoto: `git stash` antes do `git pull`.

---

## Idle Shutdown (desabilitado)

O app tem mecanismo de desligamento automático por inatividade. Está **desabilitado**:

```yaml
PANEL_IDLE_SHUTDOWN_ENABLED: "false"
PANEL_IDLE_TIMEOUT_SECONDS: "10800"   # 3h (ignorado enquanto desabilitado)
```

Para reativar: mudar para `"true"` no `docker-compose.yml` → push → rebuild.

---

## Dados Persistidos

```
~/Canva_Api/data/    → banco SQLite com cursos, grupos, recorrências, histórico
~/Canva_Api/logs/    → logs de operação
~/Canva_Api/.env     → configuração
```

Esses diretórios são volumes Docker — **não são apagados** em rebuild ou `docker compose down`.

---

## Logs e Debug

```bash
ssh eronp@100.92.163.25 'docker logs canvas-bulk-panel --tail 100 -f'
```

**Healthcheck:** o container verifica `http://127.0.0.1:5000/healthz` a cada 30s.

---

## Repositório

`https://github.com/Eronponce/Canva_Api`

Arquivos chave:
- `docker-compose.yml` — config do container
- `Dockerfile` — build Python 3.12-slim
- `templates/index.html` — UI principal (single-page)
- `static/favicon.png` — favicon Canvas
- `static/css/styles.css` — estilos
- `static/js/app.js` — lógica frontend
