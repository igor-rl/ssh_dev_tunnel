#!/usr/bin/env python3
import json, os, sys, subprocess, socket, time, getpass, tty, termios, urllib.request

# ─── Metadados ──────────────────────────────────────────────────
__author__  = "Igor Lage"
__company__ = "Precifica"
__version__ = "1.1.0"  # Incrementado para refletir a nova funcionalidade
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

# ─── Configurações de Caminho ───────────────────────────────────
BASE_DIR = os.path.expanduser("~/.dev_tunnel") 
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

def check_for_updates():
    """Verifica se existe uma versão mais recente no GitHub."""
    try:
        print(f"{Colors.DIM}🔍 Verificando atualizações...{Colors.ENDC}", end="\r")
        with urllib.request.urlopen(REPO_URL, timeout=3) as response:
            content = response.read().decode('utf-8')
            for line in content.split('\n'):
                if '__version__' in line and '=' in line:
                    remote_version = line.split('=')[1].strip().replace('"', '').replace("'", "")
                    if remote_version > __version__:
                        print(f"{Colors.WARN}✨ Nova versão disponível: {remote_version} (Atual: {__version__}){Colors.ENDC}")
                        choice = input(f"  Deseja atualizar agora? [Y/n]: ").strip().lower()
                        if choice in ('', 'y', 'yes'):
                            print(f"{Colors.ACCENT}🚀 Atualizando...{Colors.ENDC}")
                            subprocess.run(INSTALL_CMD.split(), check=True)
                            print(f"{Colors.SUCCESS}✅ Atualizado com sucesso! Reinicie o tunnel.{Colors.ENDC}")
                            sys.exit(0)
                    break
    except Exception:
        pass # Silencioso se estiver sem internet ou erro de timeout
    print(" " * 40, end="\r") # Limpa a linha do "Verificando..."

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
    print(f"{Colors.HEADER}{'─' * 65}{Colors.ENDC}")
    print(f"  {Colors.BOLD}{__company__.upper()}{Colors.ENDC} │ {Colors.ACCENT}SSH DEV TUNNEL{Colors.ENDC} {Colors.DIM}v{__version__}{Colors.ENDC}")
    
    if server:
        print(f"  {Colors.DIM}SESSÃO: {Colors.BOLD}{server['alias'].upper()}{Colors.ENDC}")
        print(f"  {Colors.DIM}ROTA:   {Colors.INFO}{breadcrumb} {Colors.DIM}→{Colors.ENDC} {server['user']}@{server['host']}")
    elif breadcrumb:
        print(f"  {Colors.DIM}PATH:   {Colors.INFO}{breadcrumb}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'─' * 65}{Colors.ENDC}")

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

# ─── Core ───────────────────────────────────────────────────────

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0

def open_tunnel(jump, server):
    if is_port_in_use(TUNNEL_PORT): return "existing"
    print(f"\n  {Colors.WARN}🔒 Senha para {jump['user']}@{jump['host']}:{Colors.ENDC}")
    pw = getpass.getpass("  > ")
    cmd = ["sshpass", "-p", pw, "ssh", "-N", "-L", f"0.0.0.0:{TUNNEL_PORT}:{server['host']}:22", f"{jump['user']}@{jump['host']}", "-o", "StrictHostKeyChecking=no"]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(10):
        if is_port_in_use(TUNNEL_PORT): return proc
        time.sleep(1)
    return None

def main():
    check_for_updates() # Verifica update antes de começar

    if not os.path.exists(CONFIG_FILE):
        config = {"jump_hosts": [], "servers": []}
    else:
        with open(CONFIG_FILE, "r") as f: config = json.load(f)
    
    # 1. Origem
    j_opts = [f"{j['user']}@{j['host']}" for j in config["jump_hosts"]] + ["+ Novo Jump Host"]
    idx = interactive_menu(j_opts, "Origem (Jump Host)")
    
    if idx == len(j_opts) - 1:
        draw_static_header("Setup")
        entry = input(f"\n  User@Host: ").strip()
        if "@" not in entry: return
        u, h = entry.split("@"); jump = {"host": h, "user": u}
        config["jump_hosts"].append(jump)
        with open(CONFIG_FILE, "w") as f: json.dump(config, f)
    else: jump = config["jump_hosts"][idx]

    # PEM
    if not os.path.exists(LOCAL_PEM_PATH):
        draw_static_header(f"{jump['user']}@{jump['host']}")
        print(f"\n  {Colors.INFO}Sincronizando chave PEM...{Colors.ENDC}")
        pw = getpass.getpass(f"  Senha SCP: ")
        subprocess.run(["sshpass", "-p", pw, "scp", "-o", "StrictHostKeyChecking=no", f"{jump['user']}@{jump['host']}:~/.ssh/{PEM_FILENAME}", LOCAL_PEM_PATH])
        if os.path.exists(LOCAL_PEM_PATH): os.chmod(LOCAL_PEM_PATH, 0o600)

    # 2. Destino
    j_str = f"{jump['user']}@{jump['host']}"
    svs = sorted(config["servers"], key=lambda x: x['alias'].lower())
    s_opts = [f"{s['alias'].ljust(15)} │ {s['host']}" for s in svs] + ["+ Novo Servidor"]
    idx = interactive_menu(s_opts, "Destino (Servidor Interno)", breadcrumb=j_str)
    
    if idx == len(s_opts) - 1:
        server = {"alias": input(f"\n  Alias: "), "host": input(f"  IP Interno: "), "user": "root", "root": input(f"  Path Remoto: ")}
        config["servers"].append(server)
        with open(CONFIG_FILE, "w") as f: json.dump(config, f)
    else: server = svs[idx]

    # 3. Túnel
    draw_static_header(breadcrumb=j_str, server=server)
    print(f"\n  {Colors.ACCENT}Conectando...{Colors.ENDC}")
    tunnel = open_tunnel(jump, server)
    if not tunnel: sys.exit(1)

    # 4. Workspace
    ws_dir = os.path.join(WS_ROOT, server['alias'])
    if not os.path.exists(ws_dir): os.makedirs(ws_dir, mode=0o755)
    ws_file_name = f"{server['alias']}.code-workspace"
    ws_path = os.path.join(ws_dir, ws_file_name)
    
    ws_data = {"folders": [], "settings": {"sshfs.configs": [{
        "name": server['alias'], "host": "127.0.0.1", "port": TUNNEL_PORT, 
        "username": server["user"], "privateKeyPath": LOCAL_PEM_PATH, "root": server["root"]
    }]}}
    with open(ws_path, "w") as f: json.dump(ws_data, f, indent=4)

    # 5. Final
    draw_static_header(breadcrumb=j_str, server=server)
    print(f"\n  {Colors.SUCCESS}● TÚNEL ATIVO [Localhost:{TUNNEL_PORT}]{Colors.ENDC}")
    print(f"\n  {Colors.BOLD}1. ACESSAR PASTA{Colors.ENDC}\n     cd {ws_dir}")
    print(f"\n  {Colors.BOLD}2. ABRIR NO EDITOR (DIRETO){Colors.ENDC}")
    print(f"     {Colors.ACCENT}cursor {ws_file_name}{Colors.ENDC}  {Colors.DIM}(Cursor){Colors.ENDC}")
    print(f"     {Colors.ACCENT}code {ws_file_name}{Colors.ENDC}    {Colors.DIM}(VS Code){Colors.ENDC}")
    print(f"\n  {Colors.BOLD}3. CONECTAR NO SSH FS{Colors.ENDC}\n     Ctrl+Shift+P → SSH FS: Connect → {server['alias']}")
    print(f"\n{Colors.HEADER}{'─' * 65}{Colors.ENDC}")
    
    try:
        input(f"  {Colors.WARN}Pressione [ENTER] para encerrar...{Colors.ENDC}")
    finally:
        if isinstance(tunnel, subprocess.Popen): tunnel.terminate()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)