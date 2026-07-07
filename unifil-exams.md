# UniFil Exams — Guia Completo

URL de acesso: `http://100.92.163.25:3000`

Interface gráfica de banco de questões para professores (Next.js 16 + SQLite).

---

## Arquitetura

```
Browser
  │  HTTP :3000
  ▼
[unifil-exams-release]  Docker container
  Next.js 16 app (Node.js)
  banco: ./data/unifil-exams.db  (volume SQLite)
  uploads: ./public/uploads/     (volume imagens)
  gabaritos: ./public/gabaritos/ (volume JPEGs)
```

---

## Atualizar / Redesplegar

```bash
ssh -i ~/.ssh/id_rsa eronp@100.92.163.25 \
  'cd ~/UniFil-Exams && git pull && docker compose up --build -d'
```

---

## Dados Persistidos (volumes)

```
~/UniFil-Exams/data/              → banco SQLite (questões, provas, usuários)
~/UniFil-Exams/public/uploads/    → imagens das questões
~/UniFil-Exams/public/gabaritos/  → gabaritos em JPEG
```

Esses diretórios **não são apagados** em rebuild.

---

## Variáveis de Ambiente

Sem `.env` obrigatório — app funciona sem IA por padrão.

Para habilitar IA (opcional), criar `~/UniFil-Exams/.env`:
```env
CLAUDE_API_KEY=           # opcional
GEMINI_API_KEY=           # opcional
OLLAMA_BASE_URL=          # se tiver Ollama no remoto
```

---

## Backup do banco

```bash
# copiar banco para local
scp -i ~/.ssh/id_rsa eronp@100.92.163.25:~/UniFil-Exams/data/unifil-exams.db ./backup.db
```

---

## Restaurar banco (em caso de reset)

```bash
# enviar banco do local para o remoto
scp -i ~/.ssh/id_rsa ./unifil-exams.db eronp@100.92.163.25:~/UniFil-Exams/data/unifil-exams.db
docker restart unifil-exams-release
```

---

## Logs e Debug

```bash
ssh eronp@100.92.163.25 'docker logs unifil-exams-release --tail 100 -f'
```

---

## Repositório

`https://github.com/Eronponce/UniFil-Exams`

Arquivos chave:
- `compose.yml` — config do container (tem `extra_hosts: host.docker.internal:host-gateway`)
- `data/` — banco SQLite (não commitado, só local/remoto)
- `public/uploads/` — imagens (não commitadas)
