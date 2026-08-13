#!/usr/bin/env python3
"""
main.py — Ponto de entrada. Orquestra os módulos; sem lógica de negócio aqui.
"""
import argparse, json, shutil, subprocess, sys, time, urllib.request

from src.config import __version__, __company__, __author__, load_config, save_config, normalize_root
from src.ui     import C, DIV, draw_header as _draw_header, interactive_menu, safe_input, ask_yes_no, abort
from src.tunnel import find_available_port
from src.workspace import workspace_crud_screen
from src.session import reconnect_saved_workspace, run_session

REPO = "igor-rl/ssh_dev_tunnel"


# ─── Checagem de atualização ──────────────────────────────────────
def _fetch_latest_version() -> str | None:
    """Consulta as tags do GitHub e retorna a maior versão semântica encontrada, ou None."""
    url = f"https://api.github.com/repos/{REPO}/tags"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ssh-dev-tunnel"})
        with urllib.request.urlopen(req, timeout=2) as resp:
            tags = json.load(resp)
    except Exception:
        return None

    versions = []
    for t in tags:
        name = t.get("name", "").lstrip("v")
        parts = name.split(".")
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            versions.append(tuple(int(p) for p in parts))
    if not versions:
        return None
    return ".".join(str(p) for p in max(versions))


def _run_upgrade() -> bool:
    """Tenta atualizar via pipx (preferencial) ou pip. Retorna True se o comando rodou com sucesso."""
    repo_url = f"git+https://github.com/{REPO}.git"

    if shutil.which("pipx"):
        listed = subprocess.run(["pipx", "list", "--short"], capture_output=True, text=True)
        if "ssh-dev-tunnel" in listed.stdout:
            result = subprocess.run(["pipx", "upgrade", "ssh-dev-tunnel"])
            return result.returncode == 0
        result = subprocess.run(["pipx", "install", "--force", repo_url])
        return result.returncode == 0

    result = subprocess.run([sys.executable, "-m", "pip", "install", "--user", "--upgrade", repo_url])
    return result.returncode == 0


def check_for_update() -> None:
    latest = _fetch_latest_version()
    if not latest:
        return

    current_t = tuple(int(p) for p in __version__.split("."))
    latest_t  = tuple(int(p) for p in latest.split("."))
    if latest_t <= current_t:
        return

    print(f"\n  {C.WARN}⚠  Nova versão disponível: v{latest}{C.RESET}  "
          f"{C.DIM}(atual: v{__version__}){C.RESET}")
    if ask_yes_no("Atualizar agora?", default_no=False):
        print(f"\n  {C.ACCENT}⟳  Atualizando...{C.RESET}\n")
        if _run_upgrade():
            print(f"\n  {C.SUCCESS}✔  Atualizado para v{latest}. Rode 'tunnel' novamente.{C.RESET}\n")
        else:
            print(f"\n  {C.ERROR}✘  Falha ao atualizar. Rode manualmente:{C.RESET}")
            print(f"  {C.ACCENT}pipx upgrade ssh-dev-tunnel{C.RESET}\n")
        sys.exit(0)

# ─── CLI ────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="SSH Dev Tunnel")
parser.add_argument('--port', '-p', type=int, default=2222,
                    help='Porta local preferencial para o túnel (Padrão: 2222).')
parser.add_argument('--ia', nargs='?', const='auto', choices=['claude', 'gemini', 'auto'],
                    help='Abre o recurso IA (Claude Code/Gemini). Sem valor, detecta/pergunta.')
parser.add_argument('--terminal', action='store_true',
                    help='Abre um shell SSH direto no servidor (substitui o antigo cmd_tunnel).')
parser.add_argument('--cursor', action='store_true', help='Abre o workspace no Cursor.')
parser.add_argument('--vscode', action='store_true', help='Abre o workspace no VS Code.')
args = parser.parse_args()

if args.cursor and args.vscode:
    print(f"\n  {C.ERROR}Use --cursor OU --vscode, não os dois.{C.RESET}\n")
    sys.exit(1)

_resource_flags = sum([args.terminal, args.ia is not None, args.cursor or args.vscode])
if _resource_flags > 1:
    print(f"\n  {C.ERROR}Use apenas um recurso por vez: --terminal, --ia ou --cursor/--vscode.{C.RESET}\n")
    sys.exit(1)

if args.terminal:
    RESOURCE = "terminal"
elif args.ia is not None:
    RESOURCE = "ia"
elif args.cursor or args.vscode:
    RESOURCE = "ide"
else:
    RESOURCE = None  # decide interativamente no menu

EDITOR_PREF = "cursor" if args.cursor else ("vscode" if args.vscode else None)
IA_PREF = args.ia

TUNNEL_PORT = find_available_port(args.port)
if TUNNEL_PORT != args.port:
    print(f"\n  {C.WARN}⚠  Porta {args.port} ocupada — usando {TUNNEL_PORT}{C.RESET}\n")
    time.sleep(1)


# ─── draw_header com contexto fechado ───────────────────────────
def header(breadcrumb: str = "", server: dict | None = None) -> None:
    _draw_header(breadcrumb, server,
                 version=__version__, company=__company__, tunnel_port=TUNNEL_PORT)


# ─── menu_fn para injetar no tunnel.choose_pem_for_server ───────
def menu_fn(options: list[str], title: str, breadcrumb: str = "") -> int:
    return interactive_menu(options, title, breadcrumb, draw_header_fn=header)


# ─── Main ───────────────────────────────────────────────────────
def main() -> None:
    check_for_update()
    config = load_config()

    # ── Recurso: IDE / IA / Terminal (via flag, ou perguntado aqui) ──
    resource = RESOURCE
    if resource is None:
        resource_options = [
            "IDE       │  Cursor / VS Code",
            "IA        │  Claude Code / Gemini (somente leitura)",
            "Terminal  │  shell SSH direto",
        ]
        r_idx = interactive_menu(resource_options, "Qual recurso você quer usar?",
                                 draw_header_fn=header)
        resource = ["ide", "ia", "terminal"][r_idx]

    # ── Tela Inicial: Conexões Salvas ─────────────────────────────
    saved_ws = workspace_crud_screen(config, draw_header_fn=header)

    if saved_ws:
        reconnect_saved_workspace(saved_ws, config, TUNNEL_PORT, header, menu_fn,
                                   resource=resource, editor_pref=EDITOR_PREF, ia_pref=IA_PREF)
        return

    # ── Fluxo manual: novo workspace ─────────────────────────────

    # 1. Seleção de Jump Host
    j_opts = [f"{j['user']}@{j['host']}" for j in config["jump_hosts"]] + ["+ Novo Jump Host"]
    idx    = interactive_menu(j_opts, "1. Origem — Jump Host", draw_header_fn=header)

    if idx == len(j_opts) - 1:
        header("Novo Jump Host")
        entry = safe_input(f"\n  {C.LABEL}User@Host:{C.RESET}  ").strip()
        if "@" not in entry:
            print(f"\n  {C.ERROR}Formato inválido. Use user@host{C.RESET}\n")
            sys.exit(1)
        u, h = entry.split("@", 1)
        jump = {"host": h, "user": u}
        config["jump_hosts"].append(jump)
        save_config(config)
    else:
        jump = config["jump_hosts"][idx]

    # 2. Seleção de Servidor
    svs    = sorted(config["servers"], key=lambda x: x["alias"].lower())
    s_opts = [f"{s['alias'].ljust(14)}  │  {s['user']}@{s['host']}" for s in svs] + ["+ Novo Servidor"]
    breadcrumb = f"{jump['user']}@{jump['host']}"
    idx    = interactive_menu(s_opts, "2. Destino — Servidor Interno", breadcrumb,
                              draw_header_fn=header)

    if idx == len(s_opts) - 1:
        header("Novo Servidor")
        alias = safe_input(f"\n  {C.LABEL}Alias:{C.RESET}  ").strip()
        raw   = safe_input(f"  {C.LABEL}User@IP:{C.RESET}  ").strip()
        if "@" not in raw:
            print(f"\n  {C.ERROR}Formato inválido. Use user@ip{C.RESET}\n")
            sys.exit(1)
        u, h  = raw.split("@", 1)
        path  = safe_input(f"  {C.LABEL}Path Remoto:{C.RESET}  ").strip()
        server = {"alias": alias, "host": h, "user": u, "root": normalize_root(path)}
        config["servers"].append(server)
        save_config(config)
    else:
        server = svs[idx]

    # 3. Sessão completa
    run_session(jump, server, config, TUNNEL_PORT, header, menu_fn,
                resource=resource, editor_pref=EDITOR_PREF, ia_pref=IA_PREF)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {C.DIM}Cancelado.{C.RESET}\n")
        sys.exit(0)