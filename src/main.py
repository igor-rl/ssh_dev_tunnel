#!/usr/bin/env python3

import json, os, sys, subprocess, socket, time, tty, termios, argparse, readline, shutil

# ─── Metadados ──────────────────────────────────────────────────
__author__  = "Igor Lage"
__company__ = "Precifica"
__version__ = "3.7.4"

# ─── Configuração de Argumentos (CLI) ───────────────────────────
parser = argparse.ArgumentParser(description="SSH Dev Tunnel")
parser.add_argument('--port', '-p', type=int, default=2222,
                    help='Porta local preferencial para o túnel (Padrão: 2222).')
args = parser.parse_args()
7
# ─── Paleta de Cores ────────────────────────────────────────────
class C:
    DIVIDER = '\033[38;5;238m'
    LABEL   = '\033[38;5;244m'
    ACCENT  = '\033[38;5;75m'
    SUCCESS = '\033[38;5;114m'
    INFO    = '\033[38;5;252m'
    WARN    = '\033[38;5;178m'
    ERROR   = '\033[38;5;196m'
    DIM     = '\033[38;5;240m'
    RESET   = '\033[0m'
    BOLD    = '\033[1m'

# ─── Layout adaptativo ──────────────────────────────────────────
def _term_width() -> int:
    try:
        return min(shutil.get_terminal_size((72, 24)).columns, 80)
    except Exception:
        return 72

def _div() -> str:
    w = _term_width() - 2
    return f"{C.DIVIDER}{'─' * w}{C.RESET}"

def DIV() -> str:
    return _div()

# ─── Estrutura de Diretórios ─────────────────────────────────────
HOST_PROJECT_PATH = os.environ.get("HOST_PROJECT_PATH", "") + "/.dev_tunnel"

_CANDIDATE_A = "/home/tunnel/.dev_tunnel"
_CANDIDATE_B = "/app/.dev_tunnel"

if os.path.exists(_CANDIDATE_A):
    BASE_DIR     = _CANDIDATE_A
else:
    BASE_DIR     = _CANDIDATE_B

DATA_DIR    = os.path.join(BASE_DIR, ".data")
CONFIG_FILE = os.path.join(DATA_DIR, "servers.json")
WS_ROOT     = os.path.join(BASE_DIR, "workspaces")
LOCAL_SSH   = os.path.join(DATA_DIR, ".ssh")
PASSWORDS_FILE = os.path.join(DATA_DIR, ".passwords")

for d in [BASE_DIR, DATA_DIR, LOCAL_SSH, WS_ROOT]:
    os.makedirs(d, mode=0o755, exist_ok=True)

# ─── Conversor de caminhos ───────────────────────────────────────
def to_host_path(container_path: str) -> str:
    if not HOST_PROJECT_PATH:
        return container_path
    abs_internal = os.path.abspath(container_path)
    if abs_internal.startswith(BASE_DIR):
        rel = os.path.relpath(abs_internal, BASE_DIR)
        return os.path.join(HOST_PROJECT_PATH, rel).replace("\\", "/")
    return container_path

def to_wsl_path(internal_path: str) -> str:
    abs_internal = os.path.abspath(internal_path)
    if HOST_PROJECT_PATH and abs_internal.startswith(BASE_DIR):
        rel = os.path.relpath(abs_internal, BASE_DIR)
        return os.path.join(HOST_PROJECT_PATH, rel)
    return abs_internal

# ─── Porta disponível ────────────────────────────────────────────
def find_available_port(preferred: int, max_attempts: int = 20) -> int:
    for offset in range(max_attempts):
        port = preferred + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            in_use = s.connect_ex(("127.0.0.1", port)) == 0
        if not in_use:
            return port
    raise RuntimeError(
        f"Nenhuma porta disponível entre {preferred} e {preferred + max_attempts - 1}."
    )

TUNNEL_PORT = find_available_port(args.port)
if TUNNEL_PORT != args.port:
    print(f"\n  {C.WARN}⚠  Porta {args.port} ocupada — usando {TUNNEL_PORT}{C.RESET}\n")
    time.sleep(1)

# ─── Passwords Store (arquivo texto simples) ─────────────────────
def _load_passwords() -> dict:
    result = {}
    if not os.path.exists(PASSWORDS_FILE):
        return result
    try:
        with open(PASSWORDS_FILE, "r") as f:
            for line in f:
                line = line.rstrip("\n")
                if "=" in line:
                    k, v = line.split("=", 1)
                    result[k] = v
    except OSError:
        pass
    return result

def _save_passwords(data: dict) -> None:
    tmp = PASSWORDS_FILE + ".tmp"
    try:
        with open(tmp, "w") as f:
            for k, v in data.items():
                f.write(f"{k}={v}\n")
        os.replace(tmp, PASSWORDS_FILE)
        os.chmod(PASSWORDS_FILE, 0o600)
    except OSError as e:
        print(f"\n  {C.WARN}⚠  Não foi possível salvar senhas: {e}{C.RESET}\n")

def save_secret(key: str, value: str) -> None:
    data = _load_passwords()
    data[key] = value
    _save_passwords(data)

def get_secret(key: str) -> str | None:
    return _load_passwords().get(key)

def delete_secret(key: str) -> None:
    data = _load_passwords()
    if key in data:
        del data[key]
        _save_passwords(data)

# ─── Saída limpa ────────────────────────────────────────────────
def abort(msg="Cancelado."):
    print(f"\n\n  {C.DIM}{msg}{C.RESET}\n")
    sys.exit(0)

def safe_input(prompt: str, prefill: str = "") -> str:
    if not sys.stdin.isatty():
        try:
            return input(prompt)
        except KeyboardInterrupt:
            abort()
    if prefill:
        readline.set_startup_hook(lambda: readline.insert_text(prefill))
    try:
        return input(prompt)
    except KeyboardInterrupt:
        abort()
    finally:
        readline.set_startup_hook()

def safe_getpass(prompt: str) -> str:
    fd  = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    buf: list[str] = []
    pos: int       = 0
    sys.stdout.write(prompt)
    sys.stdout.flush()
    tty.setraw(fd)

    def _redraw() -> None:
        if pos > 0:
            sys.stdout.write(f"\033[{pos}D")
        sys.stdout.write("\033[K")
        masked = "*" * len(buf)
        sys.stdout.write(masked)
        chars_after = len(buf) - pos
        if chars_after > 0:
            sys.stdout.write(f"\033[{chars_after}D")
        sys.stdout.flush()

    try:
        while True:
            ch = os.read(fd, 1)
            if ch == b'\x03':
                sys.stdout.write("\n")
                sys.stdout.flush()
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
                abort()
            elif ch in (b'\r', b'\n'):
                break
            elif ch == b'\x15':
                buf.clear(); pos = 0; _redraw()
            elif ch in (b'\x7f', b'\x08'):
                if pos > 0:
                    buf.pop(pos - 1); pos -= 1; _redraw()
            elif ch == b'\x1b':
                seq = os.read(fd, 1)
                if seq == b'[':
                    seq2 = os.read(fd, 1)
                    if seq2 == b'D':
                        if pos > 0:
                            pos -= 1
                            sys.stdout.write("\033[1D"); sys.stdout.flush()
                    elif seq2 == b'C':
                        if pos < len(buf):
                            pos += 1
                            sys.stdout.write("\033[1C"); sys.stdout.flush()
                    elif seq2 in (b'H', b'1'):
                        if seq2 == b'1': os.read(fd, 1)
                        if pos > 0:
                            sys.stdout.write(f"\033[{pos}D"); sys.stdout.flush()
                        pos = 0
                    elif seq2 in (b'F', b'4'):
                        if seq2 == b'4': os.read(fd, 1)
                        if pos < len(buf):
                            sys.stdout.write(f"\033[{len(buf) - pos}C"); sys.stdout.flush()
                        pos = len(buf)
                    elif seq2 == b'3':
                        os.read(fd, 1)
                        if pos < len(buf):
                            buf.pop(pos); _redraw()
                    elif seq2 in (b'A', b'B'):
                        pass
            elif ch >= b' ':
                char = ch.decode("utf-8", errors="replace")
                buf.insert(pos, char); pos += 1; _redraw()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write("\n"); sys.stdout.flush()
    return "".join(buf)

# ─── Helpers ────────────────────────────────────────────────────
def getch():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x03':
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
            abort()
        return ch
    except KeyboardInterrupt:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        abort()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

def _flush_stdin() -> None:
    try:
        fd = sys.stdin.fileno()
        termios.tcflush(fd, termios.TCIFLUSH)
    except Exception:
        pass

def ask_yes_no(question: str, default_no: bool = True) -> bool:
    hint = "S  Sim  /  N  Não (padrão)" if default_no else "S  Sim (padrão)  /  N  Não"
    print(f"\n  {C.BOLD}{question}{C.RESET}")
    print(f"  {C.ACCENT}▶  {hint}{C.RESET}  ", end="", flush=True)
    _flush_stdin()
    ch = getch()
    print()
    return ch.lower() == 's'

def tag(label, value, color=C.INFO):
    return f"  {C.LABEL}{label:<8}{C.RESET}  {color}{value}{C.RESET}"

def draw_header(breadcrumb="", server=None):
    os.system("clear")
    mode = "DOCKER" if os.environ.get("HOST_PROJECT_PATH") else "LOCAL"
    d = DIV()
    print(d)
    print(f"  {C.BOLD}{C.INFO}{__company__.upper()}{C.RESET}  {C.DIVIDER}│{C.RESET}  "
          f"{C.ACCENT}{C.BOLD}SSH DEV TUNNEL{C.RESET}  {C.DIM}v{__version__}  [{mode}]{C.RESET}")
    print(d)
    if server:
        print(tag("SESSÃO",  server.get('alias', 'NOVO').upper(), C.ACCENT))
        print(tag("ROTA",    f"{breadcrumb}  {C.DIM}→{C.RESET}  {C.INFO}{server['user']}@{server['host']}"))
        print(tag("PORTA",   f"localhost:{TUNNEL_PORT}", C.WARN))
        print(d)
    elif breadcrumb:
        print(tag("PATH", breadcrumb))
        print(d)

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0

def interactive_menu(options, title, breadcrumb="", footer_hint=None):
    idx = 0
    while True:
        draw_header(breadcrumb)
        print(f"\n  {C.BOLD}{C.INFO}{title.upper()}{C.RESET}\n")
        for i, opt in enumerate(options):
            if i == idx: print(f"  {C.ACCENT}▶  {C.BOLD}{opt}{C.RESET}")
            else:         print(f"     {C.DIM}{opt}{C.RESET}")
        print(f"\n{DIV()}")
        if footer_hint: print(f"  {C.DIM}{footer_hint}{C.RESET}")
        print(f"  {C.DIM}↑ ↓  navegar    ENTER  selecionar    Q  sair{C.RESET}")
        ch = getch()
        if ch == '\x1b':
            getch(); arrow = getch()
            if arrow == 'A': idx = (idx - 1) % len(options)
            elif arrow == 'B': idx = (idx + 1) % len(options)
        elif ch in ('\r', '\n'): return idx
        elif ch.lower() == 'q': abort()

# ─── PEM Management ─────────────────────────────────────────────
def _fix_ownership(path: str) -> None:
    try:
        os.chown(path, 1000, 1000)
    except (PermissionError, OSError):
        pass

def choose_pem_for_server(jump, password, server, config, breadcrumb):
    server_key = f"{server['user']}@{server['host']}"
    saved_pem  = config.get("pem_by_server", {}).get(server_key)
    local_path = os.path.join(LOCAL_SSH, saved_pem) if saved_pem else None

    if saved_pem and os.path.exists(local_path):
        _fix_ownership(local_path)
        os.chmod(local_path, 0o600)
        return local_path, saved_pem

    print(f"\n  {C.ACCENT}⟳  Buscando chaves no jump host...{C.RESET}")
    cmd = [
        "sshpass", "-p", password,
        "ssh", "-o", "StrictHostKeyChecking=no",
        f"{jump['user']}@{jump['host']}",
        "ls ~/.ssh/*.pem ~/.ssh/*.ppk 2>/dev/null | xargs -I{} basename {}"
    ]
    remote_keys = subprocess.run(cmd, capture_output=True, text=True).stdout.splitlines()

    if not remote_keys:
        print(f"  {C.ERROR}✘ Nenhuma chave encontrada no Jump Host.{C.RESET}")
        sys.exit(1)

    idx = interactive_menu(remote_keys, f"Chave para {server['alias']}", breadcrumb)
    chosen     = remote_keys[idx]
    local_dest = os.path.join(LOCAL_SSH, chosen)

    subprocess.run([
        "sshpass", "-p", password, "scp",
        "-o", "StrictHostKeyChecking=no",
        f"{jump['user']}@{jump['host']}:~/.ssh/{chosen}", local_dest
    ])
    os.chmod(local_dest, 0o600)
    _fix_ownership(local_dest)
    _fix_ownership(LOCAL_SSH)

    config.setdefault("pem_by_server", {})[server_key] = chosen
    with open(CONFIG_FILE, "w") as f: json.dump(config, f, indent=4)
    return local_dest, chosen

# ─── Senha do Jump Host ─────────────────────────────────────────
def get_jump_password(jump: dict, breadcrumb: str) -> str:
    """Retorna senha salva ou solicita ao usuário — sem reperguntar se já existe."""
    vault_key = f"jump:{jump['user']}@{jump['host']}"
    saved_pw  = get_secret(vault_key)

    if saved_pw:
        # Senha já existe em disco — usa silenciosamente, sem mostrar prompt
        return saved_pw

    draw_header(breadcrumb)
    pw = safe_getpass(f"\n  {C.WARN}Senha {jump['user']}@{jump['host']}:{C.RESET}  ")

    if not pw:
        abort("Senha não pode ser vazia.")

    if ask_yes_no("Salvar senha para próximas sessões?"):
        save_secret(vault_key, pw)
        print(f"  {C.SUCCESS}✔  Senha salva em {C.DIM}{PASSWORDS_FILE}{C.RESET}")
        time.sleep(0.5)

    return pw

def clear_jump_password(jump: dict) -> None:
    vault_key = f"jump:{jump['user']}@{jump['host']}"
    delete_secret(vault_key)

# ─── Normaliza root path ─────────────────────────────────────────
def normalize_root(root: str) -> str:
    if not root:
        return "/"
    root = root.strip()
    if not root.startswith("/"):
        root = "/" + root
    return root

# ─── Abre editor ────────────────────────────────────────────────
def open_in_editor(ws_path: str, breadcrumb: str) -> None:
    """
    Pergunta ao usuário como abrir o workspace ANTES de travar o terminal com SSH.
    Lança o editor em background (Popen) para não bloquear.
    """
    draw_header(breadcrumb)
    print(f"\n  {C.BOLD}{C.INFO}ABRIR WORKSPACE{C.RESET}\n")
    print(f"  {C.LABEL}Local:{C.RESET}  {C.DIM}{ws_path}{C.RESET}\n")
    print(f"{DIV()}")

    opts = ["Cursor", "VS Code", "Abrir manualmente depois"]
    idx  = interactive_menu(opts, "Como deseja abrir?", breadcrumb)

    if idx == 0:
        cmd = ["cursor", ws_path]
    elif idx == 1:
        cmd = ["code", ws_path]
    else:
        # Manual — só mostra o caminho, não lança nada
        draw_header(breadcrumb)
        print(f"\n  {C.WARN}Workspace salvo em:{C.RESET}")
        print(f"  {C.ACCENT}{ws_path}{C.RESET}\n")
        print(f"  {C.DIM}Abra manualmente quando quiser.{C.RESET}\n")
        time.sleep(2)
        return

    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        draw_header(breadcrumb)
        print(f"\n  {C.SUCCESS}✔  Editor iniciado.{C.RESET}  {C.DIM}({cmd[0]}){C.RESET}\n")
        time.sleep(1)
    except FileNotFoundError:
        draw_header(breadcrumb)
        print(f"\n  {C.ERROR}✘  Comando '{cmd[0]}' não encontrado no PATH.{C.RESET}")
        print(f"  {C.DIM}Workspace em: {ws_path}{C.RESET}\n")
        time.sleep(2)

# ─── CRUD de Workspaces ─────────────────────────────────────────
def load_workspaces(config: dict) -> list[dict]:
    """
    Retorna lista de workspaces salvos.
    Cada item: { alias, jump_label, server_label, jump_idx, server_idx, ws_file, port }
    """
    return config.get("saved_workspaces", [])

def save_workspace_entry(config: dict, entry: dict) -> None:
    ws_list = config.setdefault("saved_workspaces", [])
    # Evita duplicata por alias
    ws_list = [w for w in ws_list if w.get("alias") != entry["alias"]]
    ws_list.append(entry)
    config["saved_workspaces"] = ws_list
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def delete_workspace_entry(config: dict, alias: str) -> None:
    config["saved_workspaces"] = [
        w for w in config.get("saved_workspaces", [])
        if w.get("alias") != alias
    ]
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def workspace_crud_screen(config: dict) -> dict | None:
    """
    Tela inicial: lista workspaces salvos.
    Retorna o workspace escolhido (dict) ou None para fluxo manual.
    """
    ws_list = load_workspaces(config)

    while True:
        draw_header("Workspaces Salvos")

        if not ws_list:
            print(f"\n  {C.DIM}Nenhum workspace salvo ainda.{C.RESET}\n")
            opts = ["+ Novo Workspace (configurar manualmente)", "Sair"]
            idx  = interactive_menu(opts, "Workspaces", "Início")
            if idx == 0:
                return None
            abort()

        # Lista workspaces + opções de gerenciamento
        labels = [f"{w['alias'].ljust(16)}  {C.DIM}│{C.RESET}  {w.get('route', '')}" for w in ws_list]
        labels += [
            f"{C.ACCENT}+ Novo Workspace{C.RESET}",
            f"{C.ERROR}⊘  Remover Workspace{C.RESET}",
            f"{C.DIM}Sair{C.RESET}",
        ]

        idx = interactive_menu(
            [l.replace(C.DIM,'').replace(C.RESET,'').replace(C.ACCENT,'').replace(C.ERROR,'') for l in labels],
            "Selecione um Workspace",
            "Início",
            "ENTER  conectar    Q  sair"
        )

        n = len(ws_list)

        if idx < n:
            # Workspace selecionado — conecta
            return ws_list[idx]
        elif idx == n:
            # Novo workspace
            return None
        elif idx == n + 1:
            # Remover workspace
            if not ws_list:
                continue
            rm_labels = [w["alias"] for w in ws_list] + ["← Cancelar"]
            rm_idx    = interactive_menu(rm_labels, "Remover — qual workspace?", "Início")
            if rm_idx < len(ws_list):
                chosen_alias = ws_list[rm_idx]["alias"]
                delete_workspace_entry(config, chosen_alias)
                config["saved_workspaces"] = [w for w in config.get("saved_workspaces", []) if w["alias"] != chosen_alias]
                ws_list = load_workspaces(config)
                print(f"\n  {C.SUCCESS}✔  Workspace '{chosen_alias}' removido.{C.RESET}")
                time.sleep(0.8)
        else:
            abort()

# ─── Conecta workspace salvo ─────────────────────────────────────
def connect_saved_workspace(ws: dict, config: dict) -> None:
    """Reconecta usando dados salvos no workspace, sem re-perguntar tudo."""
    jump_label  = ws.get("jump_label", "")
    server_alias = ws.get("alias", "")

    # Localiza jump e server nas listas
    jump   = next((j for j in config["jump_hosts"]
                   if f"{j['user']}@{j['host']}" == jump_label), None)
    server = next((s for s in config["servers"]
                   if s["alias"] == server_alias), None)

    if not jump or not server:
        print(f"\n  {C.ERROR}✘  Dados do workspace desatualizados. Configure novamente.{C.RESET}\n")
        time.sleep(1.5)
        return

    jump_breadcrumb = f"{jump['user']}@{jump['host']}"

    # Senha — transparente se já salva
    session_pw = get_jump_password(jump, jump_breadcrumb)

    # Valida conexão
    draw_header(jump_breadcrumb, server)
    print(f"\n  {C.ACCENT}⟳  Verificando conexão com {jump_breadcrumb}...{C.RESET}", flush=True)
    ok = _test_ssh(jump, session_pw)
    if not ok:
        print(f"\n  {C.ERROR}✘  Falha na autenticação. Removendo senha salva...{C.RESET}")
        clear_jump_password(jump)
        time.sleep(1)
        session_pw = get_jump_password(jump, jump_breadcrumb)
        ok = _test_ssh(jump, session_pw)
        if not ok:
            print(f"\n  {C.ERROR}✘  Autenticação falhou novamente.{C.RESET}\n")
            sys.exit(1)

    print(f"  {C.SUCCESS}✔  Conectado a {jump_breadcrumb}{C.RESET}\n")
    time.sleep(0.4)

    # PEM
    local_pem, _ = choose_pem_for_server(jump, session_pw, server, config, jump['host'])

    # Workspace file
    ws_dir  = os.path.join(WS_ROOT, server["alias"])
    os.makedirs(ws_dir, mode=0o755, exist_ok=True)
    ws_file = os.path.join(ws_dir, f"{server['alias']}.code-workspace")
    display_path = to_wsl_path(ws_file)

    _write_workspace(ws_file, server, local_pem)

    # Abre editor ANTES do SSH travar o terminal
    open_in_editor(display_path, jump_breadcrumb)

    # Túnel SSH
    _start_tunnel_and_wait(jump, session_pw, server, local_pem, jump_breadcrumb)

def _test_ssh(jump: dict, password: str) -> bool:
    test_cmd = [
        "sshpass", "-p", password,
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=8",
        f"{jump['user']}@{jump['host']}",
        "echo OK"
    ]
    result = subprocess.run(test_cmd, capture_output=True, text=True)
    return result.returncode == 0 and "OK" in result.stdout

def _write_workspace(ws_file: str, server: dict, local_pem: str) -> None:
    """Gera o .code-workspace com permissões para editar arquivos via SSH FS."""
    key_path_for_json = to_host_path(local_pem)
    server_root = normalize_root(server.get("root", "/"))

    ws_data = {
        "folders": [
            {
                "name": f"SSH FS - {server['alias']}",
                "uri": f"ssh://{server['alias']}/"
            }
        ],
        "settings": {
            "sshfs.configs": [{
                "name":           server["alias"],
                "host":           "127.0.0.1",
                "port":           TUNNEL_PORT,
                "username":       server["user"],
                "privateKeyPath": key_path_for_json,
                "root":           server_root,
                # Permite sudo sem senha para criação/edição de arquivos
                "sudo":           True,
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

def _start_tunnel_and_wait(jump: dict, password: str, server: dict,
                            local_pem: str, jump_breadcrumb: str) -> None:
    tunnel = "existing"
    if not is_port_open(TUNNEL_PORT):
        cmd = [
            "sshpass", "-p", password,
            "ssh", "-N",
            "-L", f"0.0.0.0:{TUNNEL_PORT}:{server['host']}:22",
            f"{jump['user']}@{jump['host']}",
            "-o", "StrictHostKeyChecking=no"
        ]
        tunnel = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)

    draw_header(jump_breadcrumb, server)
    print(f"\n  {C.SUCCESS}{C.BOLD}● TÚNEL ATIVO{C.RESET}  {C.DIM}localhost:{TUNNEL_PORT}{C.RESET}\n")
    print(DIV())

    try:
        safe_input(f"\n  {C.WARN}Pressione ENTER para encerrar o túnel...{C.RESET}")
    finally:
        if isinstance(tunnel, subprocess.Popen):
            tunnel.terminate()

# ─── Main ───────────────────────────────────────────────────────
def main():
    config = {"jump_hosts": [], "servers": [], "pem_by_server": {}, "saved_workspaces": []}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            try: config.update(json.load(f))
            except: pass

    # ── Tela Inicial: CRUD de Workspaces ────────────────────────
    saved_ws = workspace_crud_screen(config)

    if saved_ws:
        # Reconecta workspace existente
        connect_saved_workspace(saved_ws, config)
        return

    # ── Fluxo manual: configurar novo workspace ──────────────────

    # 1. Seleção de Jump Host
    j_opts = [f"{j['user']}@{j['host']}" for j in config["jump_hosts"]] + ["+ Novo Jump Host"]
    idx = interactive_menu(j_opts, "1. Origem — Jump Host")

    if idx == len(j_opts) - 1:
        draw_header("Novo Jump Host")
        entry = safe_input(f"\n  {C.LABEL}User@Host:{C.RESET}  ").strip()
        if "@" not in entry:
            print(f"\n  {C.ERROR}Formato inválido. Use user@host{C.RESET}\n")
            sys.exit(1)
        u, h = entry.split("@", 1)
        jump = {"host": h, "user": u}
        config["jump_hosts"].append(jump)
        with open(CONFIG_FILE, "w") as f: json.dump(config, f, indent=4)
    else:
        jump = config["jump_hosts"][idx]

    # 2. Senha — silenciosa se já salva
    jump_breadcrumb = f"{jump['user']}@{jump['host']}"
    session_pw = get_jump_password(jump, jump_breadcrumb)

    # Valida senha
    draw_header(jump_breadcrumb)
    print(f"\n  {C.ACCENT}⟳  Verificando conexão com {jump_breadcrumb}...{C.RESET}", flush=True)
    if not _test_ssh(jump, session_pw):
        print(f"\n  {C.ERROR}✘  Falha na autenticação. Senha incorreta ou host inacessível.{C.RESET}")
        print(f"  {C.DIM}Removendo senha salva...{C.RESET}\n")
        clear_jump_password(jump)
        time.sleep(1)
        session_pw = get_jump_password(jump, jump_breadcrumb)
        if not _test_ssh(jump, session_pw):
            print(f"\n  {C.ERROR}✘  Autenticação falhou novamente. Verifique o host e a senha.{C.RESET}\n")
            sys.exit(1)

    print(f"  {C.SUCCESS}✔  Conectado a {jump_breadcrumb}{C.RESET}\n")
    time.sleep(0.5)

    # 3. Seleção de Servidor
    svs    = sorted(config["servers"], key=lambda x: x["alias"].lower())
    s_opts = [f"{s['alias'].ljust(14)}  │  {s['user']}@{s['host']}" for s in svs] + ["+ Novo Servidor"]
    idx    = interactive_menu(s_opts, "2. Destino — Servidor Interno", jump_breadcrumb)

    if idx == len(s_opts) - 1:
        draw_header("Novo Servidor")
        alias = safe_input(f"\n  {C.LABEL}Alias:{C.RESET}  ").strip()
        raw   = safe_input(f"  {C.LABEL}User@IP:{C.RESET}  ").strip()
        if "@" not in raw:
            print(f"\n  {C.ERROR}Formato inválido. Use user@ip{C.RESET}\n")
            sys.exit(1)
        u, h  = raw.split("@", 1)
        path  = safe_input(f"  {C.LABEL}Path Remoto:{C.RESET}  ").strip()
        server = {"alias": alias, "host": h, "user": u, "root": normalize_root(path)}
        config["servers"].append(server)
        with open(CONFIG_FILE, "w") as f: json.dump(config, f, indent=4)
    else:
        server = svs[idx]

    # 4. PEM
    local_pem, _ = choose_pem_for_server(jump, session_pw, server, config, jump['host'])

    # 5. Workspace file
    ws_dir  = os.path.join(WS_ROOT, server["alias"])
    os.makedirs(ws_dir, mode=0o755, exist_ok=True)
    ws_file = os.path.join(ws_dir, f"{server['alias']}.code-workspace")
    display_path = to_wsl_path(ws_file)

    _write_workspace(ws_file, server, local_pem)

    # Salva entrada de workspace para uso futuro
    ws_entry = {
        "alias":        server["alias"],
        "route":        f"{jump['user']}@{jump['host']}  →  {server['user']}@{server['host']}",
        "jump_label":   f"{jump['user']}@{jump['host']}",
        "server_label": f"{server['user']}@{server['host']}",
    }
    save_workspace_entry(config, ws_entry)

    # 6. Abre editor ANTES do SSH
    open_in_editor(display_path, jump_breadcrumb)

    # 7. Túnel SSH (bloqueia até ENTER)
    _start_tunnel_and_wait(jump, session_pw, server, local_pem, jump_breadcrumb)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {C.DIM}Cancelado.{C.RESET}\n")
        sys.exit(0)