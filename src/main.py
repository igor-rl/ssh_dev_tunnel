#!/usr/bin/env python3

import json, os, sys, subprocess, socket, time, getpass, tty, termios
import urllib.request

# ─── Proteção contra sudo ───────────────────────────────────────
if os.geteuid() == 0:
    print("\n❌ Não execute este comando com sudo.\nExecute como usuário normal.\n")
    sys.exit(1)

# ─── Keyring Setup ──────────────────────────────────────────────
try:
    import keyring
    from keyring.backends.chroot import ChrootBackend
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "keyring"], check=True)
    import keyring

# ─── Metadados ──────────────────────────────────────────────────
__author__  = "Igor Lage"
__company__ = "Precifica"
__version__ = "3.6.8"
KEYRING_SERVICE = "precifica-dev-tunnel"

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

# ─── Detecção de Ambiente ───────────────────────────────────────
IS_DOCKER   = os.path.exists('/.dockerenv') or os.environ.get('HOST_PROJECT_PATH') is not None
BASE_DIR    = "/app/.dev_tunnel" if IS_DOCKER else os.path.expanduser("~/.dev_tunnel")
DATA_DIR    = os.path.join(BASE_DIR, ".data")
CONFIG_FILE = os.path.join(DATA_DIR, "servers.json")
WS_ROOT     = os.path.join(BASE_DIR, "workspaces")
LOCAL_SSH   = os.path.join(DATA_DIR, ".ssh")
TUNNEL_PORT = 2222

for d in [DATA_DIR, LOCAL_SSH, WS_ROOT]:
    if not os.path.exists(d):
        os.makedirs(d, mode=0o700, exist_ok=True)

# ─── Configuração de Backend Keyring para Docker ────────────────
if IS_DOCKER:
    # No Docker, usamos um backend de arquivo local dentro da pasta persistente
    from keyring.backends.file import PlaintextKeyring
    kr = PlaintextKeyring()
    kr.file_path = os.path.join(DATA_DIR, "keyring.cfg")
    keyring.set_keyring(kr)

# ─── Helpers ────────────────────────────────────────────────────

def getch():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

def tag(label, value, color=C.INFO):
    return f"  {C.LABEL}{label:<8}{C.RESET}  {color}{value}{C.RESET}"

def draw_header(breadcrumb="", server=None):
    os.system("clear")
    mode = "DOCKER" if IS_DOCKER else "LOCAL"
    print(DIV)
    print(f"  {C.BOLD}{C.INFO}{__company__.upper()}{C.RESET}  {C.DIVIDER}│{C.RESET}  {C.ACCENT}{C.BOLD}SSH DEV TUNNEL{C.RESET}  {C.DIM}v{__version__}  [{mode}]{C.RESET}")
    print(DIV)
    if server:
        print(tag("SESSÃO",  server.get('alias', 'NOVO').upper(), C.ACCENT))
        print(tag("ROTA",    f"{breadcrumb}  {C.DIM}→{C.RESET}  {C.INFO}{server['user']}@{server['host']}"))
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
            else: print(f"     {C.DIM}{opt}{C.RESET}")
        print(f"\n{DIV}")
        if footer_hint: print(f"  {C.DIM}{footer_hint}{C.RESET}")
        print(f"  {C.DIM}↑ ↓  navegar    ENTER  selecionar    Q  sair{C.RESET}")
        ch = getch()
        if ch == '\x1b':
            getch(); arrow = getch()
            if arrow == 'A': idx = (idx - 1) % len(options)
            elif arrow == 'B': idx = (idx + 1) % len(options)
        elif ch in ('\r', '\n'): return idx
        elif ch.lower() == 'q': sys.exit(0)

# ─── Password & PEM Management ──────────────────────────────────

def get_jump_password(jump):
    user, host = jump['user'], jump['host']
    try:
        saved = keyring.get_password(KEYRING_SERVICE, f"{user}@{host}")
    except:
        saved = None
        
    if saved:
        print(f"  {C.SUCCESS}✔  Senha recuperada para {user}@{host}{C.RESET}")
        return saved
    
    draw_header(f"{user}@{host}")
    pw = getpass.getpass(f"\n  {C.WARN}Senha {user}@{host}:{C.RESET}  ")
    print(f"\n  {C.BOLD}Salvar senha?{C.RESET} {C.DIM}(será salva em {DATA_DIR if IS_DOCKER else 'OS Keyring'}){C.RESET}")
    print(f"  {C.ACCENT}▶  S  Sim / N  Não{C.RESET}")
    
    if getch().lower() == 's':
        keyring.set_password(KEYRING_SERVICE, f"{user}@{host}", pw)
        print(f"  {C.SUCCESS}✔  Senha salva.{C.RESET}")
    return pw

def choose_pem_for_server(jump, password, server, config, breadcrumb):
    server_key = f"{server['user']}@{server['host']}"
    saved_pem  = config.get("pem_by_server", {}).get(server_key)
    local_path = os.path.join(LOCAL_SSH, saved_pem) if saved_pem else None

    if saved_pem and os.path.exists(local_path):
        return local_path, saved_pem

    print(f"\n  {C.ACCENT}⟳  Buscando chaves no jump host...{C.RESET}")
    cmd = ["sshpass", "-p", password, "ssh", "-o", "StrictHostKeyChecking=no", 
           f"{jump['user']}@{jump['host']}", "ls ~/.ssh/*.pem ~/.ssh/*.ppk 2>/dev/null | xargs -I{} basename {}"]
    remote_keys = subprocess.run(cmd, capture_output=True, text=True).stdout.splitlines()
    
    if not remote_keys:
        print(f"  {C.ERROR}✘ Nenhuma chave encontrada em ~/.ssh/ no Jump Host.{C.RESET}")
        sys.exit(1)

    idx = interactive_menu(remote_keys, f"Chave para {server['alias']}", breadcrumb)
    chosen = remote_keys[idx]
    local_dest = os.path.join(LOCAL_SSH, chosen)
    
    subprocess.run(["sshpass", "-p", password, "scp", "-o", "StrictHostKeyChecking=no",
                    f"{jump['user']}@{jump['host']}:~/.ssh/{chosen}", local_dest])
    os.chmod(local_dest, 0o600)
    
    config.setdefault("pem_by_server", {})[server_key] = chosen
    with open(CONFIG_FILE, "w") as f: json.dump(config, f, indent=4)
    return local_dest, chosen

# ─── Main ───────────────────────────────────────────────────────

def main():
    config = {"jump_hosts": [], "servers": [], "pem_by_server": {}}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            try: config.update(json.load(f))
            except: pass

    j_opts = [f"{j['user']}@{j['host']}" for j in config["jump_hosts"]] + ["+ Novo Jump Host"]
    idx = interactive_menu(j_opts, "1. Origem — Jump Host")
    
    if idx == len(j_opts) - 1:
        draw_header("Novo Jump Host")
        entry = input(f"\n  {C.LABEL}User@Host:{C.RESET}  ").strip()
        u, h = entry.split("@")
        jump = {"host": h, "user": u}
        config["jump_hosts"].append(jump)
        with open(CONFIG_FILE, "w") as f: json.dump(config, f)
    else: 
        jump = config["jump_hosts"][idx]
    
    session_pw = get_jump_password(jump)

    svs = sorted(config["servers"], key=lambda x: x["alias"].lower())
    s_opts = [f"{s['alias'].ljust(14)}  │  {s['user']}@{s['host']}" for s in svs] + ["+ Novo Servidor"]
    idx = interactive_menu(s_opts, "2. Destino — Servidor Interno", f"{jump['user']}@{jump['host']}")
    
    if idx == len(s_opts) - 1:
        draw_header("Novo Servidor")
        alias = input(f"\n  {C.LABEL}Alias:{C.RESET}  ").strip()
        u, h = input(f"  {C.LABEL}User@IP:{C.RESET}  ").strip().split("@")
        path = input(f"  {C.LABEL}Path Remoto:{C.RESET}  ").strip()
        server = {"alias": alias, "host": h, "user": u, "root": path}
        config["servers"].append(server)
        with open(CONFIG_FILE, "w") as f: json.dump(config, f)
    else: 
        server = svs[idx]

    local_pem, pem_name = choose_pem_for_server(jump, session_pw, server, config, jump['host'])
    
    if not is_port_open(TUNNEL_PORT):
        cmd = ["sshpass", "-p", session_pw, "ssh", "-N", "-L", f"0.0.0.0:{TUNNEL_PORT}:{server['host']}:22", 
               f"{jump['user']}@{jump['host']}", "-o", "StrictHostKeyChecking=no"]
        tunnel = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
    else:
        tunnel = "existing"

    host_base = os.environ.get("HOST_PROJECT_PATH", ".")
    pem_path_for_vs = local_pem.replace("/app", host_base) if IS_DOCKER else local_pem
    
    ws_dir = os.path.join(WS_ROOT, server["alias"])
    os.makedirs(ws_dir, mode=0o755, exist_ok=True)
    ws_file = os.path.join(ws_dir, f"{server['alias']}.code-workspace")
    
    ws_data = {"folders": [], "settings": {"sshfs.configs": [{
        "name": server["alias"], "host": "127.0.0.1", "port": TUNNEL_PORT,
        "username": server["user"], "privateKeyPath": pem_path_for_vs, "root": server["root"]
    }]}}
    
    with open(ws_file, "w") as f: json.dump(ws_data, f, indent=4)
    display_path = os.path.abspath(ws_file).replace("/app", host_base) if IS_DOCKER else os.path.abspath(ws_file)

    draw_header(f"{jump['user']}@{jump['host']}", server)
    print(f"\n  {C.SUCCESS}{C.BOLD}● TÚNEL ATIVO{C.RESET}  {C.DIM}localhost:{TUNNEL_PORT}{C.RESET}\n")
    print(DIV)
    print(f"\n  {C.BOLD}{C.INFO}1. ABRIR NO EDITOR{C.RESET}\n")
    print(f"  {C.LABEL}Cursor{C.RESET}   {C.ACCENT}cursor \"{display_path}\"{C.RESET}")
    print(f"  {C.LABEL}VS Code{C.RESET}  {C.ACCENT}code   \"{display_path}\"{C.RESET}")
    print(f"\n{DIV}")
    
    try: 
        input(f"\n  {C.WARN}Pressione ENTER para encerrar...{C.RESET}")
    finally:
        if isinstance(tunnel, subprocess.Popen): tunnel.terminate()

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: sys.exit(0)