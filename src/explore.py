#!/usr/bin/env python3
"""
explore.py — Ponto de entrada do `tunnel-explore`.

Lista os túneis SSH atualmente ativos (abertos via `tunnel`), deixa o
usuário escolher um, prepara CLAUDE.md/GEMINI.md com o comando SSH de
leitura (mesma porta/chave do túnel) e as regras da sessão, e abre a CLI
de IA escolhida (Claude Code ou Gemini CLI) já apontada para essa pasta.

Sem mount, sem sync, sem dependência extra (sshfs/rsync): a IA lê arquivos
remotos rodando `ssh ... cat/find/grep` via Bash, sempre em tempo real.
O usuário aplica as mudanças manualmente (Cursor) e testa.
"""
import os, shutil, sys

from src.config import __version__, __company__
from src.tunnel import list_active_tunnels
from src.ui import C, DIV, interactive_menu

EXPLORE_ROOT = os.path.expanduser("~/.dev_tunnel/explore")

# ─── CLIs de IA suportadas ────────────────────────────────────────
# (nome exibido, binário no PATH, arquivo de contexto que essa CLI lê)
AGENTS = [
    ("Claude Code", "claude", "CLAUDE.md"),
    ("Gemini CLI",  "gemini", "GEMINI.md"),
]

CONTEXT_MD_TEMPLATE = """# Sessão de exploração remota (somente leitura) — {alias}

Conexão ativa: `{route}` (túnel SSH na porta local {port}).

Não há mount local. Para ler qualquer arquivo/pasta remota, rode via Bash
(as flags -o HostKeyAlgorithms/PubkeyAcceptedKeyTypes são necessárias porque
servidores mais antigos só oferecem ssh-rsa, que o SSH moderno desativa por
padrão — sem elas a conexão falha com "no matching host key type found").

IMPORTANTE: os arquivos remotos estão em ISO-8859-1 (Latin-1), não UTF-8.
Sempre que o comando mostrar conteúdo de arquivo (cat/grep), passe a saída
por `iconv -f ISO-8859-1 -t UTF-8` — sem isso, acentos e caracteres especiais
aparecem corrompidos (ex: "pre�o" em vez de "preço"):

    ssh -p {port} -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedKeyTypes=+ssh-rsa -i {pem} {user}@127.0.0.1 "cat '<caminho remoto>'" | iconv -f ISO-8859-1 -t UTF-8
    ssh -p {port} -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedKeyTypes=+ssh-rsa -i {pem} {user}@127.0.0.1 "find '<pasta>' -iname '*termo*'"
    ssh -p {port} -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedKeyTypes=+ssh-rsa -i {pem} {user}@127.0.0.1 "grep -rn 'termo' '<pasta>' --include='*.php'" | iconv -f ISO-8859-1 -t UTF-8
    ssh -p {port} -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedKeyTypes=+ssh-rsa -i {pem} {user}@127.0.0.1 "wc -l '<arquivo>'"

Raiz remota configurada: `{root}`

## O que você PODE fazer
- Rodar os comandos SSH acima (só leitura: cat/find/grep/ls/wc/head/tail).
- Diagnosticar bugs, explicar comportamento, sugerir trechos de código
  corrigidos ou novas implementações.
- Rastrear dependências entre arquivos/pastas remotos.

## O que você NÃO PODE fazer
- Rodar qualquer comando remoto de escrita (>, sed -i, rm, mv, cp para lá,
  echo/tee para arquivo, etc). Mesmo que tecnicamente funcione, não é o
  fluxo de trabalho desta sessão — é só investigação e sugestão.
- Assumir que uma sugestão foi aplicada — o usuário SEMPRE aplica as
  mudanças e testa manualmente (normalmente no Cursor), fora desta sessão.

## Escopo — evite varredura cega (pode ter milhões de arquivos lá)
- Nunca rode `find`/`grep -r` na raiz `{root}` sem restringir a uma
  subpasta específica e, se possível, `--include` por extensão.
- Peça ao usuário o caminho aproximado se não souber onde procurar, em vez
  de varrer tudo.
- Antes de ler um arquivo grande, confira o tamanho com `wc -l`.

## Como responder
1. Cite o caminho completo do arquivo remoto e a linha.
2. Ao final de cada resposta, resuma em 1-2 frases o que foi encontrado ou
   sugerido, e o que falta o usuário fazer (aplicar, testar).
"""


def _draw_header(breadcrumb: str = "") -> None:
    os.system("clear")
    d = DIV()
    print(d)
    print(f"  {C.BOLD}{C.INFO}{__company__.upper()}{C.RESET}  {C.DIVIDER}│{C.RESET}  "
          f"{C.ACCENT}{C.BOLD}TUNNEL EXPLORE{C.RESET}  {C.DIM}v{__version__}{C.RESET}")
    print(d)
    if breadcrumb:
        print(f"  {C.LABEL}Conexão:{C.RESET}  {breadcrumb}")
        print(d)


def _ensure_context_files(project_dir: str, tunnel: dict) -> None:
    """Escreve CLAUDE.md e GEMINI.md (mesmo conteúdo) — cada CLI lê o seu."""
    content = CONTEXT_MD_TEMPLATE.format(
        alias=tunnel["alias"], route=tunnel["route"], port=tunnel["port"],
        pem=tunnel["pem"], user=tunnel["user"], root=tunnel["root"],
    )
    for _, _, filename in AGENTS:
        with open(os.path.join(project_dir, filename), "w") as f:
            f.write(content)


# ─── Helpers reutilizáveis (usados também por `tunnel --ia`) ─────
def prepare_context_files(tunnel: dict) -> str:
    """Cria o project_dir (se preciso) e escreve CLAUDE.md/GEMINI.md. Retorna o project_dir."""
    project_dir = os.path.join(EXPLORE_ROOT, tunnel["alias"])
    os.makedirs(project_dir, exist_ok=True)
    _ensure_context_files(project_dir, tunnel)
    return project_dir


def pick_agent(preferred: str | None = None, breadcrumb: str = "",
               draw_header_fn=None) -> tuple[str | None, str | None]:
    """
    Retorna (label, binário) do agente de IA a usar.
    `preferred`: None/'auto' pergunta se houver mais de um; 'claude'/'gemini'
    força esse binário (se instalado, senão cai para a escolha normal).
    Retorna (None, None) se nenhuma CLI de IA estiver instalada.
    """
    available = [(label, b, f) for label, b, f in AGENTS if shutil.which(b)]
    if not available:
        return None, None

    if preferred and preferred != "auto":
        match = next(((label, b) for label, b, _ in available if b == preferred), None)
        if match:
            return match

    if len(available) == 1:
        label, b, _ = available[0]
        return label, b

    options = [label for label, _, _ in available]
    idx = interactive_menu(options, "Qual assistente usar?", breadcrumb,
                            draw_header_fn=draw_header_fn)
    label, b, _ = available[idx]
    return label, b


def main() -> None:
    _draw_header()

    tunnels = list_active_tunnels()
    if not tunnels:
        print(f"\n  {C.WARN}⚠  Nenhum túnel ativo encontrado.{C.RESET}")
        print(f"  {C.DIM}Abra um com 'tunnel' em outro terminal antes de rodar isso.{C.RESET}\n")
        sys.exit(1)

    # ─── 1. Escolhe a conexão ──────────────────────────────────────
    options = [f"{t['alias'].ljust(16)}  │  {t['route']}" for t in tunnels]
    idx = interactive_menu(options, "Qual conexão acessar?", "",
                            draw_header_fn=_draw_header)
    chosen = tunnels[idx]

    # ─── 2. Escolhe a CLI de IA ─────────────────────────────────────
    agent_label, agent_bin = pick_agent(breadcrumb=chosen["alias"], draw_header_fn=_draw_header)
    if not agent_bin:
        print(f"\n  {C.ERROR}✘  Nenhuma CLI de IA encontrada no PATH (claude/gemini).{C.RESET}\n")
        sys.exit(1)

    project_dir = prepare_context_files(chosen)

    print(f"\n  {C.SUCCESS}✔  Pronto. Sessão de leitura para {chosen['alias']} configurada.{C.RESET}")
    print(f"  {C.DIM}Abrindo o {agent_label}...{C.RESET}\n")

    os.chdir(project_dir)
    os.execvp(agent_bin, [agent_bin])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {C.DIM}Cancelado.{C.RESET}\n")
        sys.exit(0)
