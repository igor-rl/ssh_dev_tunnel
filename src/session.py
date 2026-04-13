"""
session.py — Fluxo de sessão: autenticação, PEM, workspace e bloqueio do túnel.
"""
import sys, time
from src.ui import C, DIV, draw_header, ask_yes_no, safe_input
from src.vault import get_secret, save_secret, delete_secret, vault_key_for_jump
from src.tunnel import test_ssh, choose_pem_for_server, start_tunnel, is_port_open
from src.workspace import (
    write_workspace, workspace_path_for,
    show_editor_instructions, save_workspace_entry,
)


# ─── Senha do Jump Host ─────────────────────────────────────────
def get_jump_password(jump: dict, breadcrumb: str, draw_header_fn) -> str:
    """
    Retorna a senha salva silenciosamente, ou solicita ao usuário.

    BUG FIX: a senha só é pedida novamente se NÃO estiver no vault.
    Quando está salva, é retornada sem nenhum prompt.
    """
    from src.ui import safe_getpass  # importação local para evitar circular

    vault_key = vault_key_for_jump(jump)
    saved_pw  = get_secret(vault_key)

    if saved_pw:
        return saved_pw

    draw_header_fn(breadcrumb)
    pw = safe_getpass(f"\n  {C.WARN}Senha {jump['user']}@{jump['host']}:{C.RESET}  ")

    if not pw:
        from src.ui import abort
        abort("Senha não pode ser vazia.")

    if ask_yes_no("Salvar senha para próximas sessões?"):
        save_secret(vault_key, pw)
        print(f"  {C.SUCCESS}✔  Senha salva.{C.RESET}")
        time.sleep(0.5)

    return pw


def clear_jump_password(jump: dict) -> None:
    delete_secret(vault_key_for_jump(jump))


# ─── Validação de conexão com retry ─────────────────────────────
def authenticate(jump: dict, breadcrumb: str, draw_header_fn) -> str:
    """
    Garante autenticação bem-sucedida. Limpa senha salva e repede se falhar.
    Retorna a senha validada.
    """
    session_pw = get_jump_password(jump, breadcrumb, draw_header_fn)

    draw_header_fn(breadcrumb)
    print(f"\n  {C.ACCENT}⟳  Verificando conexão com {jump['user']}@{jump['host']}...{C.RESET}",
          flush=True)

    if not test_ssh(jump, session_pw):
        print(f"\n  {C.ERROR}✘  Falha na autenticação. Removendo senha salva...{C.RESET}")
        clear_jump_password(jump)
        time.sleep(1)
        # Pede a senha novamente (desta vez vault está vazio)
        session_pw = get_jump_password(jump, breadcrumb, draw_header_fn)
        if not test_ssh(jump, session_pw):
            print(f"\n  {C.ERROR}✘  Autenticação falhou novamente.{C.RESET}\n")
            sys.exit(1)

    print(f"  {C.SUCCESS}✔  Conectado a {jump['user']}@{jump['host']}{C.RESET}\n")
    time.sleep(0.4)
    return session_pw


# ─── Bloqueio do túnel ───────────────────────────────────────────
def _wait_for_enter_then_close(proc, server: dict, display_path: str,
                                jump_breadcrumb: str, tunnel_port: int,
                                draw_header_fn) -> None:
    """
    Exibe status do túnel ativo + caminho do workspace e aguarda ENTER.
    BUG FIX (mensagem final): exibe o display_path claramente.
    """
    draw_header_fn(jump_breadcrumb, server)

    print(f"\n  {C.SUCCESS}{C.BOLD}● TÚNEL ATIVO{C.RESET}  "
          f"{C.DIM}localhost:{tunnel_port}{C.RESET}\n")
    print(DIV())
    print(f"\n  {C.LABEL}Workspace:{C.RESET}  {C.ACCENT}{display_path}{C.RESET}\n")
    print(DIV())

    try:
        safe_input(f"\n  {C.WARN}Pressione ENTER para encerrar o túnel...{C.RESET}")
    finally:
        if hasattr(proc, "terminate"):
            proc.terminate()


# ─── Fluxo completo de uma sessão ────────────────────────────────
def run_session(jump: dict, server: dict, config: dict,
                tunnel_port: int, draw_header_fn, menu_fn) -> None:
    """
    Executa a sessão completa:
      1. Autentica no jump host
      2. Escolhe PEM
      3. Gera workspace
      4. Salva entrada de workspace
      5. Mostra instruções do editor
      6. Abre túnel e bloqueia até ENTER
    """
    jump_breadcrumb = f"{jump['user']}@{jump['host']}"

    # 1. Auth
    session_pw = authenticate(jump, jump_breadcrumb, draw_header_fn)

    # 2. PEM
    local_pem, _ = choose_pem_for_server(jump, session_pw, server, config, menu_fn)

    # 3. Workspace
    ws_file, display_path = workspace_path_for(server)
    write_workspace(ws_file, server, local_pem, tunnel_port)

    # 4. Salva entrada
    ws_entry = {
        "alias":        server["alias"],
        "route":        f"{jump['user']}@{jump['host']}  →  {server['user']}@{server['host']}",
        "jump_label":   f"{jump['user']}@{jump['host']}",
        "server_label": f"{server['user']}@{server['host']}",
    }
    save_workspace_entry(config, ws_entry)

    # 5. Instruções do editor (antes de travar o terminal com o túnel)
    show_editor_instructions(display_path, jump_breadcrumb, draw_header_fn)

    # 6. Túnel
    proc = start_tunnel(jump, session_pw, server, tunnel_port)
    _wait_for_enter_then_close(proc, server, display_path,
                                jump_breadcrumb, tunnel_port, draw_header_fn)


# ─── Reconexão de workspace salvo ────────────────────────────────
def reconnect_saved_workspace(ws: dict, config: dict,
                               tunnel_port: int, draw_header_fn, menu_fn) -> None:
    """Reconecta usando dados persistidos, sem re-perguntar configurações."""
    jump_label   = ws.get("jump_label", "")
    server_alias = ws.get("alias", "")

    jump   = next((j for j in config["jump_hosts"]
                   if f"{j['user']}@{j['host']}" == jump_label), None)
    server = next((s for s in config["servers"]
                   if s["alias"] == server_alias), None)

    if not jump or not server:
        print(f"\n  {C.ERROR}✘  Dados desatualizados. Configure novamente.{C.RESET}\n")
        time.sleep(1.5)
        return

    run_session(jump, server, config, tunnel_port, draw_header_fn, menu_fn)