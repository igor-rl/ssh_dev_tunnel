"""
session.py — Fluxo de sessão: autenticação, PEM, túnel, e os 3 recursos
que podem ser abertos sobre ele (IDE / IA / Terminal).

FIX: senha é salva automaticamente após autenticação bem-sucedida,
sem perguntar ao usuário ("Salvar senha?"). Estratégia de baixa segurança
aceita pelo usuário para garantir recuperação da senha entre sessões.
"""
import subprocess, sys, time
from src.ui import C, DIV, draw_header, ask_yes_no, safe_input
from src.vault import get_secret, save_secret, delete_secret, vault_key_for_jump
from src.tunnel import (
    test_ssh, choose_pem_for_server, start_tunnel, is_port_open,
    register_active_tunnel, unregister_active_tunnel,
)
from src.config import normalize_root
from src.workspace import (
    write_workspace, workspace_path_for,
    show_editor_instructions, save_workspace_entry,
)
from src.terminal import open_shell


# ─── Senha do Jump Host ─────────────────────────────────────────
def get_jump_password(jump: dict, breadcrumb: str, draw_header_fn) -> str:
    """
    Retorna a senha salva silenciosamente, ou solicita ao usuário.
    FIX: quando não há senha salva, pede e salva automaticamente.
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

    # FIX: salva automaticamente, sem perguntar
    save_secret(vault_key, pw)
    print(f"  {C.SUCCESS}✔  Senha salva localmente.{C.RESET}")
    time.sleep(0.4)

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


# ─── Espera o túnel aceitar conexões ─────────────────────────────
def _wait_tunnel_ready(tunnel_port: int, timeout: float = 8.0) -> None:
    """Espera a porta do túnel abrir antes de seguir (evita ECONNREFUSED no SSH FS)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_port_open(tunnel_port):
            return
        time.sleep(0.3)


# ─── Encerramento do túnel ────────────────────────────────────────
def _close_tunnel(proc, tunnel_port: int) -> None:
    if hasattr(proc, "terminate"):
        proc.terminate()
    unregister_active_tunnel(tunnel_port)


# ─── Bloqueio do túnel (modo IDE) ─────────────────────────────────
def _wait_for_enter_then_close(proc, server: dict, display_path: str,
                                jump_breadcrumb: str, tunnel_port: int,
                                draw_header_fn) -> None:
    draw_header_fn(jump_breadcrumb, server)

    print(f"\n  {C.SUCCESS}{C.BOLD}● TÚNEL ATIVO{C.RESET}  "
          f"{C.DIM}localhost:{tunnel_port}{C.RESET}\n")
    print(DIV())
    print(f"\n  {C.LABEL}Workspace:{C.RESET}  {C.ACCENT}{display_path}{C.RESET}\n")
    print(DIV())
    print(f"\n  {C.DIM}Dica: rode 'tunnel-explore' em outro terminal para investigar"
          f" estes mesmos arquivos com IA (somente leitura).{C.RESET}\n")

    try:
        safe_input(f"\n  {C.WARN}Pressione ENTER para encerrar o túnel...{C.RESET}")
    finally:
        _close_tunnel(proc, tunnel_port)


# ─── Fluxo completo de uma sessão ────────────────────────────────
def run_session(jump: dict, server: dict, config: dict,
                tunnel_port: int, draw_header_fn, menu_fn,
                resource: str = "ide", editor_pref: str | None = None,
                ia_pref: str | None = None) -> None:
    """
    Executa a sessão completa, comum aos 3 recursos:
      1. Autentica no jump host
      2. Escolhe PEM
      3. Abre o túnel e registra/salva a conexão
      4. Executa o recurso escolhido (IDE / IA / Terminal)
    """
    jump_breadcrumb = f"{jump['user']}@{jump['host']}"

    # 1. Auth
    session_pw = authenticate(jump, jump_breadcrumb, draw_header_fn)

    # 2. PEM
    local_pem, _ = choose_pem_for_server(jump, session_pw, server, config, menu_fn)

    # 3. Túnel — comum aos 3 recursos
    proc = start_tunnel(jump, session_pw, server, tunnel_port)
    _wait_tunnel_ready(tunnel_port)

    route = f"{jump['user']}@{jump['host']}  →  {server['user']}@{server['host']}"
    tunnel_entry = {
        "alias": server["alias"], "route": route, "port": tunnel_port,
        "pem":   local_pem, "user": server["user"], "host": server["host"],
        "root":  normalize_root(server.get("root", "/")),
    }
    register_active_tunnel(tunnel_entry)

    # Salva a conexão para reconectar depois, independente do recurso usado
    save_workspace_entry(config, {
        "alias":        server["alias"],
        "route":        route,
        "jump_label":   f"{jump['user']}@{jump['host']}",
        "server_label": f"{server['user']}@{server['host']}",
    })

    # 4. Executa o recurso escolhido
    if resource == "terminal":
        open_shell(server, local_pem, tunnel_port, jump_breadcrumb, draw_header_fn)
        _close_tunnel(proc, tunnel_port)
        return

    if resource == "ia":
        from src.explore import pick_agent, prepare_context_files
        agent_label, agent_bin = pick_agent(ia_pref, breadcrumb=jump_breadcrumb,
                                             draw_header_fn=draw_header_fn)
        if not agent_bin:
            print(f"\n  {C.ERROR}✘  Nenhuma CLI de IA encontrada no PATH (claude/gemini).{C.RESET}\n")
            _close_tunnel(proc, tunnel_port)
            sys.exit(1)

        project_dir = prepare_context_files(tunnel_entry)
        draw_header_fn(jump_breadcrumb, server)
        print(f"\n  {C.SUCCESS}✔  Sessão de leitura pronta. Abrindo {agent_label}...{C.RESET}\n")
        subprocess.run([agent_bin], cwd=project_dir)
        _close_tunnel(proc, tunnel_port)
        return

    # resource == "ide" (padrão)
    ws_file, display_path = workspace_path_for(server)
    write_workspace(ws_file, server, local_pem, tunnel_port)
    show_editor_instructions(display_path, jump_breadcrumb, draw_header_fn,
                              editor_pref=editor_pref, menu_fn=menu_fn)
    _wait_for_enter_then_close(proc, server, display_path,
                                jump_breadcrumb, tunnel_port, draw_header_fn)


# ─── Reconexão de conexão salva ───────────────────────────────────
def reconnect_saved_workspace(ws: dict, config: dict,
                               tunnel_port: int, draw_header_fn, menu_fn,
                               resource: str = "ide", editor_pref: str | None = None,
                               ia_pref: str | None = None) -> None:
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

    run_session(jump, server, config, tunnel_port, draw_header_fn, menu_fn,
                resource=resource, editor_pref=editor_pref, ia_pref=ia_pref)
