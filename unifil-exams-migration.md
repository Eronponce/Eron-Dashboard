# UniFil Exams — Migração para Remoto

## Info do Projeto

- **App:** Interface gráfica de banco de questões para professores (Next.js 16)
- **Banco:** SQLite (`./data/unifil-exams.db`) — montado como volume
- **Porta:** 3000
- **URL após migração:** `http://100.92.163.25:3000`
- **GitHub:** https://github.com/Eronponce/UniFil-Exams

## Arquivos a Copiar (além do código)

| Origem (local) | Destino (remoto) | Conteúdo |
|---|---|---|
| `./data/` | `~/UniFil-Exams/data/` | SQLite DB |
| `./public/uploads/` | `~/UniFil-Exams/public/uploads/` | Imagens de questões |
| `./public/gabaritos/` | `~/UniFil-Exams/public/gabaritos/` | 3 JPEGs |

## Variáveis de Ambiente

Sem `.env` local — app funciona sem AI por padrão.
Para habilitar AI no remoto, criar `~/UniFil-Exams/.env`:

```env
CLAUDE_API_KEY=           # opcional
GEMINI_API_KEY=           # opcional
OLLAMA_BASE_URL=          # se tiver Ollama no remoto
```

## Passos de Migração

- [x] 1. Analisar projeto
- [x] 2. Clonar repo no remoto
- [x] 3. Copiar data/ via scp
- [x] 4. Copiar public/uploads/ via scp
- [x] 5. Copiar public/gabaritos/ via scp
- [x] 6. Build e subir container
- [x] 7. Verificar acesso em http://100.92.163.25:3000 → HTTP 200 ✓

## Update de Código (após migração)

```bash
# no remoto
cd ~/UniFil-Exams
git pull
docker compose up --build -d
```

## Observações Técnicas

- `host.docker.internal` já resolvido — compose.yml tem `extra_hosts: host-gateway` ✓
- Banco persiste no volume — update de código não afeta dados ✓
- `restart: unless-stopped` — sobe automaticamente com o PC ✓
