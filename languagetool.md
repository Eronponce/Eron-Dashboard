# LanguageTool — Guia Completo

URL de acesso: `http://100.92.163.25:8081`

---

## Arquitetura

```
Chrome Extension (webextension-chrome-ng v11)
        │  POST /check  (body: JSON, Content-Type: application/json)
        ▼
[eron-languagetool-proxy]  porta 8081
  Python HTTP proxy (docker/proxy.py)
  network_mode: host
        │
        │  Converte: JSON → application/x-www-form-urlencoded
        │  Normaliza: /check → /v2/check
        │  Adiciona: headers CORS
        ▼
[eron-languagetool]  porta 8082 (interna)
  Java LT server 6.6
  mem_limit: 700m
  LT_JAVA_XMX: 512m
```

### Por que network_mode: host no proxy?

O servidor Java LanguageTool rejeita conexões POST vindas de IPs Docker internos (172.x.x.x) — comportamento do HTTP server Java. Com `network_mode: host`, o proxy acessa via `127.0.0.1:8082` e o Java aceita normalmente.

---

## Configuração de Memória

O LanguageTool Java é guloso. Configuração atual no `docker-compose.yml`:

```yaml
mem_limit: 700m
memswap_limit: 700m
environment:
  LT_JAVA_XMS: "128m"   # heap inicial
  LT_JAVA_XMX: "512m"   # heap máximo
```

> ⚠️ Container frequentemente em ~98% do limite (687/700 MB).
> Se cair por OOM, aumente `mem_limit` e `LT_JAVA_XMX`:

```yaml
mem_limit: 1g
memswap_limit: 1g
environment:
  LT_JAVA_XMX: "768m"
```

Depois: `git push` + `docker compose up --build -d` no remoto.

---

## Atualizar / Redesplegar

```bash
# no remoto
cd ~/Eron_language_tool
git pull
docker compose up --build -d
```

Ou via SSH local:
```bash
ssh -i ~/.ssh/id_rsa eronp@100.92.163.25 \
  'cd ~/Eron_language_tool && git pull && docker compose up --build -d'
```

---

## Mudar Porta de Acesso

Por padrão o proxy escuta na `8081`. Para mudar:

Em `docker-compose.yml` (serviço `proxy`):
```yaml
environment:
  LT_PROXY_PORT: "9090"   # nova porta
```

E na extensão Chrome: `http://100.92.163.25:9090`

---

## Configurar a Extensão Chrome

1. Abrir extensão `LanguageTool` no Chrome
2. Configurações → "Local server"
3. URL: `http://100.92.163.25:8081`
4. Salvar e reiniciar o browser

**Testar manualmente:**
```bash
curl -s -X POST http://100.92.163.25:8081/v2/check \
  -d "language=pt-BR&text=Esto+é+um+teste" | python3 -m json.tool
```

---

## Logs e Debug

```bash
# logs do servidor Java
ssh eronp@100.92.163.25 'docker logs eron-languagetool --tail 100 -f'

# logs do proxy Python
ssh eronp@100.92.163.25 'docker logs eron-languagetool-proxy --tail 50 -f'
```

**Erro comum — OutOfMemoryError:**
```
java.lang.OutOfMemoryError: Java heap space
```
→ Aumentar `LT_JAVA_XMX` e `mem_limit` (ver seção acima).

**Erro comum — RemoteDisconnected:**
→ Proxy tentando acessar LT via IP Docker interno. Verificar se `network_mode: host` está no serviço `proxy`.

---

## Repositório

`https://github.com/Eronponce/Eron_language_tool`

Arquivos chave:
- `docker-compose.yml` — config dos dois containers
- `docker/proxy.py` — código do proxy Python
- `docker/nginx.conf` — nginx antigo (não usado, mantido no repo)
