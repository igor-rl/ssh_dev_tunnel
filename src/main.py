#!/usr/bin/env python3

import json, os, sys, subprocess, socket, time, getpass, tty, termios, base64, argparse, readline

# ─── Metadados ──────────────────────────────────────────────────
__author__  = "Igor Lage"
__company__ = "Precifica"
__version__ = "3.7"

# ─── Configuração de Argumentos (CLI) ───────────────────────────
parser = argparse.ArgumentParser(description="SSH Dev Tunnel")
parser.add_argument('--port', '-p', type=int, default=2222,
                    help='Porta local preferencial para o túnel (Padrão: 2222). '
                         'Se ocupada, incrementa automaticamente.')
args = parser.parse_args()

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

# ─── Constantes de Layout ───────────────────────────────────────
W = 65
DIV = f"{C.DIVIDER}{'─' * W}{C.RESET}"

# ─── Estrutura de Diretórios ─────────────────────────────────────
HOST_PROJECT_PATH = os.environ.get("HOST_PROJECT_PATH", "") + "/.dev_tunnel"

_CANDIDATE_A = "/home/tunnel/.dev_tunnel"
_CANDIDATE_B = "/app/.dev_tunnel"

if os.path.exists(_CANDIDATE_A):
    BASE_DIR     = _CANDIDATE_A
    _HOST_PREFIX = "/home/tunnel"
else:
    BASE_DIR     = _CANDIDATE_B
    _HOST_PREFIX = "/app"

DATA_DIR    = os.path.join(BASE_DIR, ".data")
CONFIG_FILE = os.path.join(DATA_DIR, "servers.json")
VAULT_FILE  = os.path.join(DATA_DIR, ".vault")
WS_ROOT     = os.path.join(BASE_DIR, "workspaces")
LOCAL_SSH   = os.path.join(DATA_DIR, ".ssh")

for d in [BASE_DIR, DATA_DIR, LOCAL_SSH, WS_ROOT]:
    os.makedirs(d, mode=0o755, exist_ok=True)

# ─── Converte caminho interno → caminho real no host ────────────
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

def to_display_path(internal_path: str) -> str:
    if internal_path.startswith(BASE_DIR):
        return internal_path.replace(BASE_DIR, "~/.dev_tunnel")
    return internal_path

# ─── Porta: escolhe a primeira livre a partir da preferencial ───
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

# ─── Simple Vault (Base64) ──────────────────────────────────────
def _load_vault() -> dict:
    if not os.path.exists(VAULT_FILE):
        return {}
    try:
        # FIX PROBLEMA 2: garante que o vault seja legível pelo usuário atual
        # mesmo que tenha sido criado originalmente como root
        _fix_ownership(VAULT_FILE)
        with open(VAULT_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def _save_vault(vault: dict) -> None:
    os.makedirs(os.path.dirname(VAULT_FILE), mode=0o700, exist_ok=True)
    tmp = VAULT_FILE + ".tmp"
    with open(tmp, 'w') as f:
        json.dump(vault, f)
    os.replace(tmp, VAULT_FILE)
    os.chmod(VAULT_FILE, 0o600)
    # FIX PROBLEMA 2: garante ownership correto após salvar
    _fix_ownership(VAULT_FILE)

def _fix_ownership(path: str) -> None:
    """Corrige o ownership de um arquivo para uid/gid 1000 (usuário tunnel).
    Opera silenciosamente — falha é esperada quando já rodamos como uid 1000."""
    try:
        os.chown(path, 1000, 1000)
    except (PermissionError, OSError):
        pass

def save_secret(key: str, value: str) -> None:
    vault = _load_vault()
    vault[key] = base64.b64encode(value.encode()).decode()
    _save_vault(vault)

def get_secret(key: str) -> str | None:
    vault = _load_vault()
    encoded = vault.get(key)
    if encoded is None:
        return None
    try:
        return base64.b64decode(encoded.encode()).decode()
    except Exception:
        return None

def delete_secret(key: str) -> None:
    vault = _load_vault()
    if key in vault:
        del vault[key]
        _save_vault(vault)

# ─── Saída limpa ────────────────────────────────────────────────
def abort(msg="Cancelado."):
    print(f"\n\n  {C.DIM}{msg}{C.RESET}\n")
    sys.exit(0)

def safe_input(prompt: str, prefill: str = "") -> str:
    """input() com suporte completo a navegação pelo teclado (setas, Home, End,
    Backspace, Delete) via GNU readline. Ctrl+C aborta normalmente."""
    # readline só funciona quando stdin é um tty real
    if not sys.stdin.isatty():
        try:
            return input(prompt)
        except KeyboardInterrupt:
            abort()

    # prefill permite pre-popular o campo (útil para edição futura)
    if prefill:
        readline.set_startup_hook(lambda: readline.insert_text(prefill))
    try:
        return input(prompt)
    except KeyboardInterrupt:
        abort()
    finally:
        readline.set_startup_hook()

def safe_getpass(prompt: str) -> str:
    """getpass com suporte a setas esquerda/direita, Home, End, Backspace e
    Delete. Os caracteres digitados NÃO são exibidos (modo senha).
    Ctrl+C aborta. Ctrl+U limpa o campo."""
    fd  = sys.stdin.fileno()
    old = termios.tcgetattr(fd)

    # Coloca o terminal em modo raw para capturar cada tecla individualmente
    tty.setraw(fd)

    buf: list[str] = []   # caracteres da senha
    pos: int       = 0    # posição do cursor dentro de buf

    sys.stdout.write(prompt)
    sys.stdout.flush()

    def _redraw() -> None:
        """Redesenha o campo inteiro (asteriscos) e reposiciona o cursor."""
        masked = "*" * len(buf)
        # move para o início do campo, apaga até o fim, reimprime
        sys.stdout.write(f"\r{prompt}{masked}\033[K")
        # recua o cursor até a posição correta
        if pos < len(buf):
            sys.stdout.write(f"\033[{len(buf) - pos}D")
        sys.stdout.flush()

    try:
        while True:
            ch = os.read(fd, 1)

            # ── Ctrl+C ──────────────────────────────────────────
            if ch == b'\x03':
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
                sys.stdout.write("\n")
                abort()

            # ── Enter ───────────────────────────────────────────
            elif ch in (b'\r', b'\n'):
                break

            # ── Ctrl+U — limpa o campo ──────────────────────────
            elif ch == b'\x15':
                buf.clear()
                pos = 0
                _redraw()

            # ── Backspace ───────────────────────────────────────
            elif ch in (b'\x7f', b'\x08'):
                if pos > 0:
                    buf.pop(pos - 1)
                    pos -= 1
                    _redraw()

            # ── Sequências de escape (setas, Home, End, Delete) ─
            elif ch == b'\x1b':
                seq = os.read(fd, 1)
                if seq == b'[':
                    seq2 = os.read(fd, 1)

                    # seta esquerda
                    if seq2 == b'D':
                        if pos > 0:
                            pos -= 1
                            sys.stdout.write("\033[1D")
                            sys.stdout.flush()

                    # seta direita
                    elif seq2 == b'C':
                        if pos < len(buf):
                            pos += 1
                            sys.stdout.write("\033[1C")
                            sys.stdout.flush()

                    # Home  (^[[H  ou  ^[[1~)
                    elif seq2 in (b'H', b'1'):
                        if seq2 == b'1':
                            os.read(fd, 1)   # consome o '~'
                        if pos > 0:
                            sys.stdout.write(f"\033[{pos}D")
                            sys.stdout.flush()
                        pos = 0

                    # End   (^[[F  ou  ^[[4~)
                    elif seq2 in (b'F', b'4'):
                        if seq2 == b'4':
                            os.read(fd, 1)   # consome o '~'
                        if pos < len(buf):
                            sys.stdout.write(f"\033[{len(buf) - pos}C")
                            sys.stdout.flush()
                        pos = len(buf)

                    # Delete  (^[[3~)
                    elif seq2 == b'3':
                        os.read(fd, 1)       # consome o '~'
                        if pos < len(buf):
                            buf.pop(pos)
                            _redraw()

                    # setas cima/baixo — ignoradas no getpass
                    elif seq2 in (b'A', b'B'):
                        pass

            # ── Caractere imprimível ─────────────────────────────
            elif ch >= b' ':
                char = ch.decode("utf-8", errors="replace")
                buf.insert(pos, char)
                pos += 1
                _redraw()

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write("\n")
        sys.stdout.flush()

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
    mode = "DOCKER" if HOST_PROJECT_PATH else "LOCAL"
    print(DIV)
    print(f"  {C.BOLD}{C.INFO}{__company__.upper()}{C.RESET}  {C.DIVIDER}│{C.RESET}  "
          f"{C.ACCENT}{C.BOLD}SSH DEV TUNNEL{C.RESET}  {C.DIM}v{__version__}  [{mode}]{C.RESET}")
    print(DIV)
    if server:
        print(tag("SESSÃO",  server.get('alias', 'NOVO').upper(), C.ACCENT))
        print(tag("ROTA",    f"{breadcrumb}  {C.DIM}→{C.RESET}  {C.INFO}{server['user']}@{server['host']}"))
        print(tag("PORTA",   f"localhost:{TUNNEL_PORT}", C.WARN))
        print(DIV)
    elif breadcrumb:
        print(tag("PATH", breadcrumb))
        print(DIV)

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
        print(f"\n{DIV}")
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
def choose_pem_for_server(jump, password, server, config, breadcrumb):
    server_key = f"{server['user']}@{server['host']}"
    saved_pem  = config.get("pem_by_server", {}).get(server_key)
    local_path = os.path.join(LOCAL_SSH, saved_pem) if saved_pem else None

    if saved_pem and os.path.exists(local_path):
        # FIX PROBLEMA 1: corrige ownership mesmo para PEMs já existentes
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

    # FIX PROBLEMA 1: corrige ownership do PEM recém-baixado e do diretório .ssh
    # O scp pode ter criado o arquivo como root se o processo ainda tiver UID 0
    _fix_ownership(local_dest)
    _fix_ownership(LOCAL_SSH)

    config.setdefault("pem_by_server", {})[server_key] = chosen
    with open(CONFIG_FILE, "w") as f: json.dump(config, f, indent=4)
    return local_dest, chosen

# ─── Gerenciamento de Senha ─────────────────────────────────────
def get_jump_password(jump: dict, breadcrumb: str) -> str:
    vault_key = f"jump:{jump['user']}@{jump['host']}"
    saved_pw  = get_secret(vault_key)

    if saved_pw:
        draw_header(breadcrumb)
        print(f"\n  {C.SUCCESS}✔  Usando senha salva para {C.ACCENT}{jump['user']}@{jump['host']}{C.RESET}")
        print(f"  {C.DIM}(vault: {VAULT_FILE}){C.RESET}\n")
        time.sleep(0.8)
        return saved_pw

    draw_header(breadcrumb)
    pw = safe_getpass(f"\n  {C.WARN}Senha {jump['user']}@{jump['host']}:{C.RESET}  ")

    if not pw:
        abort("Senha não pode ser vazia.")

    if ask_yes_no("Salvar senha no vault local? (arquivo .vault)"):
        save_secret(vault_key, pw)
        print(f"  {C.SUCCESS}✔  Senha salva em {C.DIM}{VAULT_FILE}{C.RESET}")
        time.sleep(0.6)
    else:
        print(f"  {C.DIM}Senha não salva.{C.RESET}")
        time.sleep(0.4)

    return pw

def clear_jump_password(jump: dict) -> None:
    vault_key = f"jump:{jump['user']}@{jump['host']}"
    delete_secret(vault_key)

# ─── Normaliza root path ─────────────────────────────────────────
def normalize_root(root: str) -> str:
    """FIX PROBLEMA 3: garante que o root path comece com '/'
    para o SSH FS não interpretar como relativo ao home do usuário."""
    if not root:
        return "/"
    root = root.strip()
    if not root.startswith("/"):
        root = "/" + root
    return root

# ─── Main ───────────────────────────────────────────────────────
def main():
    config = {"jump_hosts": [], "servers": [], "pem_by_server": {}}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            try: config.update(json.load(f))
            except: pass

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
        with open(CONFIG_FILE, "w") as f: json.dump(config, f)
    else:
        jump = config["jump_hosts"][idx]

    # 2. Gerenciamento de Senha — com retry automático se falhar
    jump_breadcrumb = f"{jump['user']}@{jump['host']}"
    session_pw = get_jump_password(jump, jump_breadcrumb)

    # Valida a senha tentando um comando simples no jump host
    draw_header(jump_breadcrumb)
    print(f"\n  {C.ACCENT}⟳  Verificando conexão com {jump_breadcrumb}...{C.RESET}", flush=True)
    test_cmd = [
        "sshpass", "-p", session_pw,
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=8",
        f"{jump['user']}@{jump['host']}",
        "echo OK"
    ]
    test = subprocess.run(test_cmd, capture_output=True, text=True)

    if test.returncode != 0 or "OK" not in test.stdout:
        print(f"\n  {C.ERROR}✘  Falha na autenticação. Senha incorreta ou host inacessível.{C.RESET}")
        print(f"  {C.DIM}Removendo senha do vault...{C.RESET}\n")
        clear_jump_password(jump)
        time.sleep(1)
        session_pw = get_jump_password(jump, jump_breadcrumb)
        test_cmd2 = [
            "sshpass", "-p", session_pw,
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=8",
            f"{jump['user']}@{jump['host']}",
            "echo OK"
        ]
        test2 = subprocess.run(test_cmd2, capture_output=True, text=True)
        if test2.returncode != 0 or "OK" not in test2.stdout:
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
        # FIX PROBLEMA 3: normaliza na hora de salvar
        server = {"alias": alias, "host": h, "user": u, "root": normalize_root(path)}
        config["servers"].append(server)
        with open(CONFIG_FILE, "w") as f: json.dump(config, f)
    else:
        server = svs[idx]

    # 4. PEM e Túnel
    local_pem, pem_name = choose_pem_for_server(jump, session_pw, server, config, jump['host'])

    tunnel = "existing"
    if not is_port_open(TUNNEL_PORT):
        cmd = [
            "sshpass", "-p", session_pw,
            "ssh", "-N",
            "-L", f"0.0.0.0:{TUNNEL_PORT}:{server['host']}:22",
            f"{jump['user']}@{jump['host']}",
            "-o", "StrictHostKeyChecking=no"
        ]
        tunnel = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)

    # 5. Geração do Workspace
    ws_dir  = os.path.join(WS_ROOT, server["alias"])
    os.makedirs(ws_dir, mode=0o755, exist_ok=True)
    ws_file = os.path.join(ws_dir, f"{server['alias']}.code-workspace")

    key_path_for_json = to_host_path(local_pem)

    # FIX PROBLEMA 3: normaliza o root também na hora de gerar o workspace,
    # cobrindo servidores cadastrados antes da correção (sem barra inicial)
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
                "root":           server_root,          # FIX: sempre com '/' inicial
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
        os.chown(ws_dir, 1000, 1000)
    except PermissionError:
        pass

    display_path = to_wsl_path(ws_file)

    draw_header(jump_breadcrumb, server)
    print(f"\n  {C.SUCCESS}{C.BOLD}● TÚNEL ATIVO{C.RESET}  {C.DIM}localhost:{TUNNEL_PORT}{C.RESET}\n")
    print(DIV)
    print(f"\n  {C.BOLD}{C.INFO}1. ABRIR NO EDITOR{C.RESET}\n")
    print(f"  {C.LABEL}Cursor{C.RESET}   {C.ACCENT}cursor \"{display_path}\"{C.RESET}")
    print(f"  {C.LABEL}VS Code{C.RESET}  {C.ACCENT}code   \"{display_path}\"{C.RESET}")
    print(f"\n  {C.WARN}⚠ Certifique-se de ter a extensão 'SSH FS' instalada.{C.RESET}")
    print(f"\n{DIV}")

    try:
        safe_input(f"\n  {C.WARN}Pressione ENTER para encerrar...{C.RESET}")
    finally:
        if isinstance(tunnel, subprocess.Popen):
            tunnel.terminate()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {C.DIM}Cancelado.{C.RESET}\n")
        sys.exit(0)