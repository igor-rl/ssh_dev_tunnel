"""
workspace.py — Geração de .code-workspace e gerenciamento de entradas salvas.

FIXES:
- SSH FS conecta como root diretamente (username: root), eliminando
  o erro NoPermissions ao criar/editar arquivos via interface do editor.
- Remove verificação do comando cursor/code no PATH do container.
- Senha salva automaticamente.
"""
import json, os, time
from src.config import WS_ROOT, CONFIG_FILE, to_host_path, to_wsl_path, normalize_root, save_config
from src.ui import C, DIV, draw_header, interactive_menu, safe_input, abort


# ─── Geração do arquivo .code-workspace ──────────────────────────
def write_workspace(ws_file: str, server: dict, local_pem: str, tunnel_port: int) -> None:
    key_path_for_json = to_host_path(local_pem)
    server_root = normalize_root(server.get("root", "/"))

    # FIX: conecta como root para ter permissão total de leitura/escrita.
    # Requer que /root/.ssh/authorized_keys exista no servidor remoto
    # com a mesma chave pública do usuário original (ex: opc).
    # Setup no servidor (uma vez só):
    #   sudo mkdir -p /root/.ssh
    #   sudo cp ~/.ssh/authorized_keys /root/.ssh/authorized_keys
    #   sudo chmod 700 /root/.ssh && sudo chmod 600 /root/.ssh/authorized_keys
    #   sudo grep -i PermitRootLogin /etc/ssh/sshd_config
    #   # se necessário: sudo sed -i 's/^.*PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
    #   sudo systemctl restart sshd
    ssh_username = "root"

    ws_data = {
        "folders": [
            {
                "name": f"SSH FS - {server['alias']}",
                "uri":  f"ssh://{server['alias']}/"
            }
        ],
        "settings": {
            "sshfs.configs": [{
                "name":           server["alias"],
                "host":           "127.0.0.1",
                "port":           tunnel_port,
                "username":       ssh_username,
                "privateKeyPath": key_path_for_json,
                "root":           server_root,
                "sudo":           False,
                "algorithms": {
                    "serverHostKey": ["ssh-rsa", "ssh-dss", "ecdsa-sha2-nistp256", "ssh-ed25519"],
                    "pubkey":        ["ssh-rsa", "ecdsa-sha2-nistp256", "ssh-ed25519"]
                }
            }]
        }
    }

    with open(ws_file, "w") as f:
        json.dump(ws_data, f, indent=4)

    try:
        os.chown(ws_file, 1000, 1000)
        os.chown(os.path.dirname(ws_file), 1000, 1000)
    except PermissionError:
        pass


def workspace_path_for(server: dict) -> tuple[str, str]:
    """Retorna (ws_file_interno, display_path_no_host)."""
    ws_dir  = os.path.join(WS_ROOT, server["alias"])
    os.makedirs(ws_dir, mode=0o755, exist_ok=True)
    ws_file      = os.path.join(ws_dir, f"{server['alias']}.code-workspace")
    display_path = to_wsl_path(ws_file)
    return ws_file, display_path


# ─── Instrução para abrir editor ─────────────────────────────────
def show_editor_instructions(display_path: str, breadcrumb: str,
                              draw_header_fn) -> None:
    draw_header_fn(breadcrumb)
    print(f"\n  {C.BOLD}{C.INFO}ABRIR WORKSPACE NO EDITOR{C.RESET}\n")
    print(f"  {C.LABEL}Caminho do workspace:{C.RESET}")
    print(f"  {C.ACCENT}{display_path}{C.RESET}\n")
    print(f"{DIV()}")
    print(f"  {C.DIM}Rode um dos comandos abaixo no terminal do HOST:{C.RESET}\n")
    print(f"  {C.LABEL}Cursor :{C.RESET}  {C.ACCENT}cursor \"{display_path}\"{C.RESET}")
    print(f"  {C.LABEL}VS Code:{C.RESET}  {C.ACCENT}code   \"{display_path}\"{C.RESET}\n")
    print(f"{DIV()}")
    print(f"  {C.DIM}Pressione ENTER para continuar e abrir o túnel...{C.RESET}  ", end="", flush=True)
    try:
        input()
    except KeyboardInterrupt:
        abort()


# ─── CRUD de Workspaces Salvos ───────────────────────────────────
def load_workspaces(config: dict) -> list[dict]:
    return config.get("saved_workspaces", [])


def save_workspace_entry(config: dict, entry: dict) -> None:
    ws_list = config.setdefault("saved_workspaces", [])
    ws_list = [w for w in ws_list if w.get("alias") != entry["alias"]]
    ws_list.append(entry)
    config["saved_workspaces"] = ws_list
    save_config(config)


def delete_workspace_entry(config: dict, alias: str) -> None:
    config["saved_workspaces"] = [
        w for w in config.get("saved_workspaces", [])
        if w.get("alias") != alias
    ]
    save_config(config)


def workspace_crud_screen(config: dict, draw_header_fn) -> dict | None:
    ws_list = load_workspaces(config)

    while True:
        draw_header_fn("Workspaces Salvos")

        if not ws_list:
            print(f"\n  {C.DIM}Nenhum workspace salvo ainda.{C.RESET}\n")
            opts = ["+ Novo Workspace (configurar manualmente)", "Sair"]
            idx  = interactive_menu(opts, "Workspaces", "Início",
                                    draw_header_fn=draw_header_fn)
            if idx == 0:
                return None
            abort()

        labels = [
            f"{w['alias'].ljust(16)}  │  {w.get('route', '')}"
            for w in ws_list
        ]
        labels += ["+ Novo Workspace", "⊘  Remover Workspace", "Sair"]

        idx = interactive_menu(
            labels,
            "Selecione um Workspace",
            "Início",
            footer_hint="ENTER  conectar    Q  sair",
            draw_header_fn=draw_header_fn,
        )

        n = len(ws_list)

        if idx < n:
            return ws_list[idx]
        elif idx == n:
            return None
        elif idx == n + 1:
            rm_labels = [w["alias"] for w in ws_list] + ["← Cancelar"]
            rm_idx    = interactive_menu(rm_labels, "Remover — qual workspace?", "Início",
                                         draw_header_fn=draw_header_fn)
            if rm_idx < len(ws_list):
                chosen_alias = ws_list[rm_idx]["alias"]
                delete_workspace_entry(config, chosen_alias)
                config["saved_workspaces"] = [
                    w for w in config.get("saved_workspaces", [])
                    if w["alias"] != chosen_alias
                ]
                ws_list = load_workspaces(config)
                print(f"\n  {C.SUCCESS}✔  Workspace '{chosen_alias}' removido.{C.RESET}")
                time.sleep(0.8)
        else:
            abort()