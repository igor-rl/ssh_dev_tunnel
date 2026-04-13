#!/usr/bin/env python3
"""
main.py — Ponto de entrada. Orquestra os módulos; sem lógica de negócio aqui.
"""
import argparse, sys, time

from src.config import __version__, __company__, __author__, load_config, save_config, normalize_root
from src.ui     import C, DIV, draw_header as _draw_header, interactive_menu, safe_input, abort
from src.tunnel import find_available_port
from src.workspace import workspace_crud_screen
from src.session import reconnect_saved_workspace, run_session

# ─── CLI ────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="SSH Dev Tunnel")
parser.add_argument('--port', '-p', type=int, default=2222,
                    help='Porta local preferencial para o túnel (Padrão: 2222).')
args = parser.parse_args()

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
    config = load_config()

    # ── Tela Inicial: CRUD de Workspaces ────────────────────────
    saved_ws = workspace_crud_screen(config, draw_header_fn=header)

    if saved_ws:
        reconnect_saved_workspace(saved_ws, config, TUNNEL_PORT, header, menu_fn)
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
    run_session(jump, server, config, TUNNEL_PORT, header, menu_fn)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {C.DIM}Cancelado.{C.RESET}\n")
        sys.exit(0)