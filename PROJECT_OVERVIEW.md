# PROJECT_OVERVIEW.md — Guia para agentes de manutenção

> Leitura rápida para quem vai corrigir bugs ou dar manutenção neste repo.
> Ver também `README.md` (uso), `DEPLOY.md` e `DEV-COMMANDS.md` (versionamento).

## O que é

CLI Python (`tunnel`) que automatiza túneis SSH reversos via Jump Host para acessar
servidores internos, gerando um `.code-workspace` (SSH FS) pronto para abrir no
Cursor/VS Code.

**Instalação 100% local** (sem Docker desde a v3.9.0) — via `pip`/`pipx`, direto na
máquina do usuário.

## Como roda

- Entry point real: `src/main.py`, exposto como comando `tunnel` via
  `entry_points` do `setup.py` (`console_scripts`).
- `install.sh`: script que o usuário roda no host (Mac/Linux/WSL) para instalar.
  Detecta Python 3.10+, exige `sshpass` no sistema, e instala o pacote via `pipx`
  (preferencial, isolado) ou `pip install --user` como fallback — sempre puxando
  do GitHub (`git+https://github.com/igor-rl/ssh_dev_tunnel.git`).
- `uninstall.sh`: remove o pacote (pipx/pip) e opcionalmente os dados em
  `~/.dev_tunnel`.
- `setup.py`: empacotamento pip/pipx (única forma de distribuição atual).
- **Atualização automática**: a cada execução, `main.check_for_update()` consulta
  as tags do GitHub (`igor-rl/ssh_dev_tunnel`), compara com `__version__` e, se
  houver versão mais nova, oferece atualizar na hora (via `pipx upgrade` ou
  `pip install --upgrade`). Falha silenciosamente se estiver offline.

## Estrutura de `src/` (mapa de responsabilidades)

| Arquivo | Responsabilidade | Quando mexer aqui |
|---|---|---|
| `main.py` | Orquestração/CLI: parse de args, checagem de atualização (`check_for_update`), escolha de porta, fluxo do menu inicial (jump host → servidor → sessão). | Mudar o fluxo geral do menu, novos args de CLI, lógica de auto-update. |
| `config.py` | Caminhos (`BASE_DIR = ~/.dev_tunnel`, `DATA_DIR`, `WS_ROOT`, etc.), leitura/escrita de `servers.json`, metadados (`__version__`). | Mudar onde dados são persistidos, versionamento, estrutura do config JSON. |
| `session.py` | Fluxo de uma sessão completa: autenticação (com retry), escolha de PEM, geração de workspace, abertura/travamento do túnel. | Mudar o fluxo de login/sessão, retry de autenticação, ordem das etapas. |
| `tunnel.py` | Operações SSH puras: porta livre (`find_available_port`), teste de conexão (`test_ssh`), busca/cópia de chave `.pem` do jump host (`choose_pem_for_server`), abertura do túnel reverso (`start_tunnel`). | Bugs de conexão SSH, timeout, cópia de chave, porta ocupada. |
| `vault.py` | Persistência de senhas em duas camadas: **OS Keyring** (Keychain/Credential Manager/Secret Service) quando disponível, com **fallback** em arquivo local criptografado (Fernet/AES) quando não há backend de keyring. Migra automaticamente arquivos legados em texto plano. | Mudar estratégia de armazenamento de senha, backends suportados. |
| `ui.py` | Toda a camada de terminal: cores (`C`), header adaptativo (`draw_header`), menu interativo com setas (`interactive_menu`), leitura de senha mascarada (`safe_getpass`), input com prefill (`safe_input`). | Bugs visuais, navegação do menu, comportamento de teclado (ex: bug de backspace já corrigido em `_redraw`). |
| `workspace.py` | Geração do arquivo `.code-workspace` (config SSH FS para Cursor/VS Code, conecta como `root` no servidor remoto), CRUD de workspaces salvos dentro do `servers.json`, instruções exibidas ao usuário para abrir o editor. | Bugs no arquivo `.code-workspace` gerado, permissões no editor remoto, lista de workspaces salvos. |

## Fluxo principal (feliz caminho)

1. `main.main()` chama `check_for_update()` (consulta GitHub, oferece atualizar).
2. Carrega config (`config.load_config`) e mostra workspaces salvos
   (`workspace.workspace_crud_screen`).
3. Se o usuário escolher um salvo → `session.reconnect_saved_workspace` → `run_session`.
4. Se novo → usuário escolhe/cria Jump Host e Servidor Interno via menus.
5. `session.run_session` executa: autenticar (`session.authenticate` → `vault` + `tunnel.test_ssh`),
   escolher/copiar PEM (`tunnel.choose_pem_for_server`), gerar workspace
   (`workspace.write_workspace`), salvar entrada (`workspace.save_workspace_entry`),
   mostrar instruções (`workspace.show_editor_instructions`), abrir túnel
   (`tunnel.start_tunnel`) e bloquear até ENTER.

## Persistência (dados do usuário)

Tudo em `~/.dev_tunnel/.data/` (caminho fixo, sem variação por ambiente):

- `servers.json` (via `config.py`): jump hosts, servidores, mapeamento PEM por
  servidor, workspaces salvos.
- `.passwords` + `.passwords.key`: vault de senhas (ver `vault.py`) — vazio/ausente
  se o OS Keyring estiver disponível (caso comum em macOS/Windows).
- `.ssh/`: chaves `.pem`/`.ppk` copiadas dos jump hosts.
- `workspaces/<alias>/<alias>.code-workspace`: arquivo gerado por servidor, com o
  caminho absoluto real da máquina (sem tradução de path — não há mais container).

## Pontos sensíveis / decisões conhecidas (não são bugs)

- Senha salva automaticamente sem perguntar ao usuário (`session.py`) — decisão de
  UX aceita explicitamente. A camada de armazenamento (`vault.py`) já usa Keychain/
  Credential Manager quando disponível; só cai para arquivo criptografado como
  fallback.
- Workspace conecta como `root` via sudo no SSH FS (`workspace.py`) — workaround
  para erro de permissão do editor ao criar arquivos **no servidor remoto** (não
  relacionado à instalação local da ferramenta).
- `show_editor_instructions` não verifica se `cursor`/`code` existe no PATH —
  apenas exibe o comando para o usuário rodar.
- **Atualização não é instantânea entre commits**: `check_for_update()` compara
  contra tags do GitHub, então só detecta uma versão nova depois que ela for
  commitada, taggeada (`vX.Y.Z`) e pushada.

## Histórico: remoção do Docker (v3.9.0)

Até a v3.8.x, a ferramenta rodava dentro de um container Docker (`Dockerfile`,
`docker-compose.yaml`, `entrypoint.sh`, publish via GHCR). Isso trazia:
`HOST_PROJECT_PATH`/`to_host_path`/`to_wsl_path` para traduzir caminhos
container↔host, `chown(1000, 1000)` espalhado pelo código (uid fixo do container),
e `BASE_DIR` com múltiplos candidatos (`/home/tunnel/.dev_tunnel`, `/app/.dev_tunnel`).

Tudo isso foi removido na v3.9.0: a ferramenta roda direto na máquina do usuário,
`BASE_DIR` é sempre `~/.dev_tunnel`, sem tradução de path e sem chown artificial.
Se encontrar referências a Docker em versões antigas do histórico do git, é
esperado — não é regressão, é o estado anterior à migração.

## Versionamento

- Versão fica em `src/config.py` (`__version__`) **e** em `setup.py` (`version=`)
  — os dois precisam ficar sincronizados manualmente a cada bump.
- Commits recentes seguem padrão `vX.Y.Z: fix: issue: <descrição>` — ver
  `DEV-COMMANDS.md`/`DEPLOY.md` para o fluxo de tag + push.
- **Importante**: `check_for_update()` depende da tag `vX.Y.Z` existir no GitHub
  para detectar a versão nova — sem tag, o auto-update não enxerga o release.
