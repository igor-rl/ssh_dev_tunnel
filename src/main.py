#!/usr/bin/env python3
import json, os, sys, subprocess, socket, time, getpass, tty, termios, urllib.request

# ─── Metadados ──────────────────────────────────────────────────
__author__  = "Igor Lage"
__company__ = "Precifica"
__version__ = "3.4.2" 
REPO_URL    = "https://raw.githubusercontent.com/igor-rl/ssh_dev_tunnel/main/src/main.py"
INSTALL_CMD = "pip3 install --upgrade git+https://github.com/igor-rl/ssh_dev_tunnel.git"

# ─── Configurações de Cores ─────────────────────────────────────
class Colors:
    HEADER  = '\033[38;5;244m' 
    ACCENT  = '\033[38;5;75m'  
    SUCCESS = '\033[38;5;114m' 
    INFO    = '\033[38;5;250m' 
    WARN    = '\033[38;5;178m' 
    ERROR   = '\033[38;5;196m' 
    ENDC    = '\033[0m'
    BOLD    = '\033[1m'
    DIM     = '\033[2m'

# ─── Detecção de Ambiente e Caminhos ───────────────────────────
IS_DOCKER = os.path.exists('/.dockerenv') or os.environ.get('HOST_PROJECT_PATH') is not None
BASE_DIR = os.path.expanduser("~/.dev_tunnel") if not IS_DOCKER else "/app/.dev_tunnel"

DATA_DIR = os.path.join(BASE_DIR, ".data")
CONFIG_FILE = os.path.join(DATA_DIR, "servers.json")
WS_ROOT = os.path.join(BASE_DIR, "workspaces")
LOCAL_SSH_DIR = os.path.join(DATA_DIR, ".ssh")
PEM_FILENAME = "precifica-NV-service.pem"
LOCAL_PEM_PATH = os.path.join(LOCAL_SSH_DIR, PEM_FILENAME)
TUNNEL_PORT = 2222

for d in [DATA_DIR, LOCAL_SSH_DIR, WS_ROOT]:
    if not os.path.exists(d): os.makedirs(d, mode=0o700)

# ─── Helpers de Sistema ────────────────────────────────────────

def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def draw_static_header(breadcrumb="", server=None):
    os.system("clear")
    mode = f"{Colors.DIM}[DOCKER]{Colors.ENDC}" if IS_DOCKER else f"{Colors.DIM}[LOCAL]{Colors.ENDC}"
    print(f"{Colors.HEADER}{'─' * 65}{Colors.ENDC}")
    print(f"  {Colors.BOLD}{__company__.upper()}{Colors.ENDC} │ {Colors.ACCENT}SSH DEV TUNNEL{Colors.ENDC} {Colors.DIM}v{__version__}{Colors.ENDC} {mode}")
    if server:
        print(f"  {Colors.DIM}SESSÃO: {Colors.BOLD}{server['alias'].upper()}{Colors.ENDC}")
        print(f"  {Colors.DIM}ROTA:   {Colors.INFO}{breadcrumb} {Colors.DIM}→{Colors.ENDC} {server['user']}@{server['host']}")
    elif breadcrumb:
        print(f"  {Colors.DIM}PATH:   {Colors.INFO}{breadcrumb}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'─' * 65}{Colors.ENDC}")

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0

def open_tunnel(jump, server, cached_pw=None):
    if is_port_in_use(TUNNEL_PORT): return "existing"
    
    if cached_pw:
        pw = cached_pw
    else:
        print(f"\n  {Colors.WARN}🔒 Senha para {jump['user']}@{jump['host']}:{Colors.ENDC}")
        pw = getpass.getpass("  > ")
    
    cmd = ["sshpass", "-p", pw, "ssh", "-N", "-L", f"0.0.0.0:{TUNNEL_PORT}:{server['host']}:22", f"{jump['user']}@{jump['host']}", "-o", "StrictHostKeyChecking=no"]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    for _ in range(15):
        if is_port_in_use(TUNNEL_PORT): return proc
        time.sleep(1)
    return None

def interactive_menu(options, title, breadcrumb=""):
    selected_index = 0
    while True:
        draw_static_header(breadcrumb)
        print(f"\n  {Colors.BOLD}{title.upper()}{Colors.ENDC}\n")
        for i, option in enumerate(options):
            if i == selected_index:
                print(f"  {Colors.ACCENT}▶ {Colors.BOLD}{option}{Colors.ENDC}")
            else:
                print(f"    {Colors.DIM}{option}{Colors.ENDC}")
        print(f"\n  {Colors.DIM}↑↓ Navegar | ENTER Selecionar | Q Sair{Colors.ENDC}")
        
        char = getch()
        if char == '\x1b':
            char = getch(); char = getch()
            if char == 'A': selected_index = (selected_index - 1) % len(options)
            elif char == 'B': selected_index = (selected_index + 1) % len(options)
        elif char in ('\r', '\n'): return selected_index
        elif char.lower() == 'q': sys.exit(0)

def main():
    # Carrega config
    if not os.path.exists(CONFIG_FILE):
        config = {"jump_hosts": [], "servers": []}
    else:
        with open(CONFIG_FILE, "r") as f: config = json.load(f)
    
    # Menu Jump Host
    j_opts = [f"{j['user']}@{j['host']}" for j in config["jump_hosts"]] + ["+ Novo Jump Host"]
    idx = interactive_menu(j_opts, "Origem (Jump Host)")
    
    if idx == len(j_opts) - 1:
        draw_static_header("Setup Jump")
        entry = input(f"\n  User@Host: ").strip()
        if "@" not in entry: return
        u, h = entry.split("@"); jump = {"host": h, "user": u}
        config["jump_hosts"].append(jump)
        with open(CONFIG_FILE, "w") as f: json.dump(config, f)
    else: jump = config["jump_hosts"][idx]

    # Lógica de Senha e PEM
    session_pw = None
    if not os.path.exists(LOCAL_PEM_PATH):
        draw_static_header(f"{jump['user']}@{jump['host']}")
        print(f"\n  {Colors.INFO}Sincronizando chave PEM...{Colors.ENDC}")
        session_pw = getpass.getpass(f"  Senha Jump ({jump['user']}): ")
        res = subprocess.run(["sshpass", "-p", session_pw, "scp", "-o", "StrictHostKeyChecking=no", f"{jump['user']}@{jump['host']}:~/.ssh/{PEM_FILENAME}", LOCAL_PEM_PATH])
        if res.returncode == 0:
            os.chmod(LOCAL_PEM_PATH, 0o600)
        else:
            print(f"{Colors.ERROR}Falha no SCP. Verifique a senha.{Colors.ENDC}")
            sys.exit(1)

    # Menu Servidor Destino
    j_str = f"{jump['user']}@{jump['host']}"
    svs = sorted(config["servers"], key=lambda x: x['alias'].lower())
    s_opts = [f"{s['alias'].ljust(15)} │ {s['user']}@{s['host']}" for s in svs] + ["+ Novo Servidor"]
    idx = interactive_menu(s_opts, "Destino (Servidor Interno)", breadcrumb=j_str)
    
    if idx == len(s_opts) - 1:
        draw_static_header("Setup Servidor")
        alias = input(f"\n  Alias (Ex: Homolog): ").strip()
        entry = input(f"  User@IP Interno: ").strip()
        if "@" not in entry: return
        u, h = entry.split("@")
        remote_path = input(f"  Path Remoto (Ex: /var/www): ").strip()
        server = {"alias": alias, "host": h, "user": u, "root": remote_path}
        config["servers"].append(server)
        with open(CONFIG_FILE, "w") as f: json.dump(config, f)
    else: server = svs[idx]

    # Conexão
    draw_static_header(breadcrumb=j_str, server=server)
    print(f"\n  {Colors.ACCENT}Conectando...{Colors.ENDC}")
    tunnel = open_tunnel(jump, server, cached_pw=session_pw)
    
    if not tunnel: 
        print(f"{Colors.ERROR}Falha ao conectar. Verifique VPN/Senha.{Colors.ENDC}")
        sys.exit(1)

    # Geração de Caminhos
    host_base = os.environ.get('HOST_PROJECT_PATH', '.')
    vscode_pem_path = LOCAL_PEM_PATH.replace('/app', host_base) if IS_DOCKER else LOCAL_PEM_PATH

    ws_dir = os.path.join(WS_ROOT, server['alias'])
    if not os.path.exists(ws_dir): os.makedirs(ws_dir, mode=0o755)
    ws_path = os.path.join(ws_dir, f"{server['alias']}.code-workspace")
    
    ws_data = {"folders": [], "settings": {"sshfs.configs": [{
        "name": server['alias'], 
        "host": "127.0.0.1", 
        "port": TUNNEL_PORT, 
        "username": server["user"], 
        "privateKeyPath": vscode_pem_path, 
        "root": server["root"]
    }]}}
    with open(ws_path, "w") as f: json.dump(ws_data, f, indent=4)

    # UI Final
    draw_static_header(breadcrumb=j_str, server=server)
    print(f"\n  {Colors.SUCCESS}● TÚNEL ATIVO [Localhost:{TUNNEL_PORT}]{Colors.ENDC}")
    
    display_ws_path = os.path.abspath(ws_path).replace('/app', host_base) if IS_DOCKER else os.path.abspath(ws_path)

    print(f"\n  {Colors.BOLD}1. ABRIR NO EDITOR (COPIE E COLE NO MAC){Colors.ENDC}")
    print(f"     {Colors.ACCENT}cursor \"{display_ws_path}\"{Colors.ENDC}")

    print(f"\n  {Colors.BOLD}2. CONECTAR NO SSH FS{Colors.ENDC}")
    print(f"     Ctrl+Shift+P → SSH FS: Add as Workspace folder → {server['alias']}")

    print(f"\n{Colors.HEADER}{'─' * 65}{Colors.ENDC}")
    try:
        input(f"  {Colors.WARN}O túnel será fechado ao pressionar [ENTER]...{Colors.ENDC}")
    finally:
        if isinstance(tunnel, subprocess.Popen): 
            tunnel.terminate()
            print(f"\n  {Colors.INFO}Sessão encerrada.{Colors.ENDC}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)