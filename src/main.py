#!/usr/bin/env python3
import json, os, sys, subprocess, socket, time, getpass, tty, termios

# ─── Metadados ──────────────────────────────────────────────────
__author__  = "Igor Lage"
__company__ = "Precifica"
__version__ = "1.0"

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
# Alterado para bater com o novo nome do projeto ~/.dev_tunnel
BASE_DIR = os.path.expanduser("~/.dev_tunnel") 
DATA_DIR = os.path.join(BASE_DIR, ".data")
CONFIG_FILE = os.path.join(DATA_DIR, "servers.json")
WS_ROOT = os.path.join(BASE_DIR, "workspaces")
LOCAL_SSH_DIR = os.path.join(DATA_DIR, ".ssh")
PEM_FILENAME = "precifica-NV-service.pem"
LOCAL_PEM_PATH = os.path.join(LOCAL_SSH_DIR, PEM_FILENAME)
TUNNEL_PORT = 2222
HOST_BASE = os.environ.get("HOST_PROJECT_PATH", BASE_DIR)

for d in [DATA_DIR, LOCAL_SSH_DIR, WS_ROOT]:
    if not os.path.exists(d): os.makedirs(d, mode=0o700)

# ─── UI Helpers ─────────────────────────────────────────────────

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
    print(f"  {Colors.DIM}Dev: {__author__}{Colors.ENDC}")
    
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
            char = getch()
            if char == '[': # Adicionado check do bracket para evitar bugs em alguns terminais
                char = getch()
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
    if not os.path.exists(CONFIG_FILE):
        config = {"jump_hosts": [], "servers": []}
    else:
        with open(CONFIG_FILE, "r") as f: config = json.load(f)
    
    # 1. Jump
    j_opts = [f"{j['user']}@{j['host']}" for j in config["jump_hosts"]] + ["+ Novo Jump Host"]
    idx = interactive_menu(j_opts, "Origem (Jump)")
    if idx == len(j_opts) - 1:
        draw_static_header("Setup")
        entry = input(f"\n  User@Host: ").strip()
        if "@" not in entry:
            print(f"{Colors.RED}Erro: Use o formato user@host{Colors.ENDC}")
            time.sleep(2)
            return
        u, h = entry.split("@")
        jump = {"host": h, "user": u}
        config["jump_hosts"].append(jump)
        with open(CONFIG_FILE, "w") as f: json.dump(config, f)
    else: jump = config["jump_hosts"][idx]

    # PEM
    if not os.path.exists(LOCAL_PEM_PATH):
        draw_static_header(f"{jump['user']}@{jump['host']}")
        print(f"\n  {Colors.INFO}Sincronizando chave PEM via SCP...{Colors.ENDC}")
        pw = getpass.getpass(f"  Senha SCP: ")
        
        # Executa o SCP
        result = subprocess.run([
            "sshpass", "-p", pw, 
            "scp", "-o", "StrictHostKeyChecking=no",
            f"{jump['user']}@{jump['host']}:~/.ssh/{PEM_FILENAME}", 
            LOCAL_PEM_PATH
        ])

        # VERIFICAÇÃO: Só tenta o chmod se o arquivo realmente existir agora
        if result.returncode == 0 and os.path.exists(LOCAL_PEM_PATH):
            os.chmod(LOCAL_PEM_PATH, 0o600)
            print(f"  {Colors.SUCCESS}✔ Chave sincronizada com sucesso.{Colors.ENDC}")
            time.sleep(1)
        else:
            print(f"\n  {Colors.ERROR}❌ Erro ao baixar a chave PEM.{Colors.ENDC}")
            print(f"  Certifique-se que o arquivo existe em: {jump['user']}@{jump['host']}:~/.ssh/{PEM_FILENAME}")
            # Remove o arquivo parcial se o scp falhou no meio do caminho
            if os.path.exists(LOCAL_PEM_PATH): os.remove(LOCAL_PEM_PATH)
            input(f"\n  Pressione [ENTER] para sair...")
            return

    # 2. Destino
    j_str = f"{jump['user']}@{jump['host']}"
    svs = sorted(config["servers"], key=lambda x: x['alias'].lower())
    s_opts = [f"{s['alias'].ljust(12)} │ {s['host']}" for s in svs] + ["+ Novo Servidor"]
    idx = interactive_menu(s_opts, "Destino", breadcrumb=j_str)
    
    if idx == len(s_opts) - 1:
        server = {
            "alias": input(f"\n  Alias: "), "host": input(f"  IP Interno: "),
            "user": "root", "root": input(f"  Path Remoto: ")
        }
        config["servers"].append(server)
        with open(CONFIG_FILE, "w") as f: json.dump(config, f)
    else: server = svs[idx]

    # 3. Tunnel
    draw_static_header(breadcrumb=j_str, server=server)
    print(f"\n  {Colors.ACCENT}Conectando...{Colors.ENDC}")
    tunnel = open_tunnel(jump, server)
    if not tunnel: sys.exit(1)

    # Workspace
    ws_dir = os.path.join(WS_ROOT, server['alias'])
    if not os.path.exists(ws_dir): os.makedirs(ws_dir)
    ws_path = os.path.join(ws_dir, "project.code-workspace")
    
    ws_data = {"folders": [], "settings": {"sshfs.configs": [{
        "name": server['alias'], "host": "127.0.0.1", "port": TUNNEL_PORT, 
        "username": server["user"], "privateKeyPath": LOCAL_PEM_PATH, "root": server["root"]
    }]}}
    with open(ws_path, "w") as f: json.dump(ws_data, f, indent=4)

    # Final
    draw_static_header(breadcrumb=j_str, server=server)
    print(f"\n  {Colors.SUCCESS}● TÚNEL ATIVO{Colors.ENDC}")
    print(f"\n  {Colors.BOLD}1. IR PARA PASTA{Colors.ENDC}\n     cd {ws_dir}")
    print(f"\n  {Colors.BOLD}2. ABRIR EDITOR{Colors.ENDC}\n     code .")
    print(f"\n  {Colors.BOLD}3. CONECTAR{Colors.ENDC}\n     SSH FS: Connect -> {server['alias']}")
    print(f"\n{Colors.HEADER}{'─' * 65}{Colors.ENDC}")
    
    try:
        input(f"  {Colors.WARN}Pressione [ENTER] para encerrar...{Colors.ENDC}")
    finally:
        if isinstance(tunnel, subprocess.Popen): tunnel.terminate()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {Colors.WARN}Sessão encerrada pelo usuário.{Colors.ENDC}\n")
        sys.exit(0)