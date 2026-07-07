# Conexão Remota — Docker Migration

## Acesso SSH

```bash
ssh -i ~/.ssh/id_ed25519 eronp@100.92.163.25   # via Tailscale (preferido)
ssh -i ~/.ssh/id_ed25519 eronp@189.90.67.22    # via IP público
ssh -i ~/.ssh/id_ed25519 eronp@192.168.3.34    # via LAN (mesmo roteador)
```

Claude usa sem senha — chave pública já está em `~/.ssh/authorized_keys` no remoto.

## Histórico de Chaves SSH

| Data | Chave | Status | Motivo |
|---|---|---|---|
| anterior | `~/.ssh/id_rsa` (RSA 4096) | ❌ perdida | arquivo deletado do Windows |
| 2026-05-21 | `~/.ssh/id_ed25519` (ED25519) | ✅ ativa | gerada nova, adicionada via AnyDesk |

**Como a chave foi restaurada (2026-05-21):**
1. `id_rsa` original sumiu — só `known_hosts` restava em `~/.ssh/`
2. Nova chave gerada: `ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""`
3. Acesso ao servidor via AnyDesk → PC Windows na mesma LAN → `ssh eronp@192.168.3.34`
4. Chave pública adicionada em `~/.ssh/authorized_keys` no remoto
5. Ajuste manual necessário: espaço faltando entre tipo e key (`ssh-ed25519AAAA...` → `ssh-ed25519 AAAA...`)

## PC Remoto — Info

- **OS:** Ubuntu 24.04.4 LTS (kernel 6.8.0-107-generic x86_64)
- **User:** `eronp`
- **Hostname:** `eron`
- **IP Tailscale:** `100.92.163.25` (preferido)
- **IP público:** `189.90.67.22`
- **IP local (LAN):** `192.168.3.34`
- **Disco:** 98GB total, ~17% usado (16G/98G)
- **RAM:** 7.6 GiB + 4 GiB Swap (~28% em uso = 2.1 GiB)

## Segurança SSH

- Chave privada (`~/.ssh/id_ed25519`) = só neste PC Windows. Ninguém externo acessa.
- Remoto tem apenas a chave pública em `authorized_keys` — inútil sem a privada.
- Permissões corretas no remoto: `~/.ssh` = 700, `authorized_keys` = 600.
- `authorized_keys` contém também chave RSA antiga (`eronponcepereira@gmail.com`) — pode remover se quiser limpar.

## Hardware

- **Máquina:** Dell Latitude 7490
- **CPU:** Intel Core i7-8650U (4c/8t, 1.9–4.2 GHz), TDP 22W
- **RAM:** 7.6 GiB + 4 GiB Swap
- **Disco:** SSD LITEON 256 GB

## Sistemas Rodando

| Serviço | Container | Porta | Repo |
|---|---|---|---|
| UniFil Exams | `unifil-exams-release` | 3000 | github.com/Eronponce/UniFil-Exams |
| Canvas API | `canvas-bulk-panel` | 5000 | github.com/Eronponce/Canva_Api |
| LanguageTool | `eron-languagetool` + `eron-languagetool-proxy` | 8081/8082 | github.com/Eronponce/Eron_language_tool |
| Eron Dashboard | `eron-dashboard` | 8088 | `C:\Eron_Lab\conexao-remota\eron-dashboard\` |

### Alertas conhecidos
- `eron-languagetool` roda em ~99% do limite de 700MiB — risco de OOM
- Fan reporta 0 RPM via sensor dell_smm — verificar fisicamente se CPU > 80°C
- Build cache Docker: 3.9 GB liberável com `docker builder prune`

## Teste de Conexão

```bash
ssh -i ~/.ssh/id_ed25519 -o BatchMode=yes eronp@100.92.163.25 'echo OK'
```

Documentação completa: ver `README.md` e docs por serviço nesta pasta.
