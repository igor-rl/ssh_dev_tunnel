#!/usr/bin/env python3
import json, os, sys, subprocess, socket, time, getpass, tty, termios

# ─── Proteção contra sudo ───────────────────────────────────────
if os.geteuid() == 0:
    print("\n❌ Não execute este comando com sudo.\nExecute como usuário normal.\n")
    sys.exit(1)

# ─── Metadados ──────────────────────────────────────────────────
__author__  = "Igor Lage"
__company__ = "Precifica"
__version__ = "3.5.1"
IMAGE       = "ghcr.io/igor-rl/ssh_dev_tunnel:latest"

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
PEM_FILE    = "precifica-NV-service.pem"
LOCAL_PEM   = os.path.join(LOCAL_SSH, PEM_FILE)
TUNNEL_PORT = 2222

for d in [DATA_DIR, LOCAL_SSH, WS_ROOT]:
    if not os.path.exists(d):
        os.makedirs(d, mode=0o700)

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

def step(icon, text, color=C.ACCENT):
    print(f"\n  {color}{icon}  {C.BOLD}{text}{C.RESET}")

def ok(text):
    print(f"  {C.SUCCESS}✔  {text}{C.RESET}")

def err(text):
    print(f"  {C.ERROR}✘  {text}{C.RESET}")

def warn(text):
    print(f"  {C.WARN}⚠  {text}{C.RESET}")

def draw_header(breadcrumb="", server=None):
    os.system("clear")
    mode  = "DOCKER" if IS_DOCKER else "LOCAL"
    print(DIV)
    print(f"  {C.BOLD}{C.INFO}{__company__.upper()}{C.RESET}  {C.DIVIDER}│{C.RESET}  {C.ACCENT}{C.BOLD}SSH DEV TUNNEL{C.RESET}  {C.DIM}v{__version__}  [{mode}]{C.RESET}")
    print(DIV)
    if server:
        print(tag("SESSÃO",  server['alias'].upper(), C.ACCENT))
        print(tag("ROTA",    f"{breadcrumb}  {C.DIM}→{C.RESET}  {C.INFO}{server['user']}@{server['host']}"))
        print(DIV)
    elif breadcrumb:
        print(tag("PATH", breadcrumb))
        print(DIV)

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0

def open_tunnel(jump, server, cached_pw=None):
    if is_port_open(TUNNEL_PORT):
        return "existing"
    pw = cached_pw or getpass.getpass(f"\n  {C.WARN}Senha {jump['user']}@{jump['host']}:{C.RESET}  ")
    cmd = [
        "sshpass", "-p", pw, "ssh", "-N", "-L",
        f"0.0.0.0:{TUNNEL_PORT}:{server['host']}:22",
        f"{jump['user']}@{jump['host']}",
        "-o", "StrictHostKeyChecking=no"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(15):
        if is_port_open(TUNNEL_PORT):
            return proc
        time.sleep(1)
    return None

def interactive_menu(options, title, breadcrumb=""):
    idx = 0
    while True:
        draw_header(breadcrumb)
        print(f"\n  {C.BOLD}{C.INFO}{title.upper()}{C.RESET}\n")
        for i, opt in enumerate(options):
            if i == idx:
                print(f"  {C.ACCENT}▶  {C.BOLD}{opt}{C.RESET}")
            else:
                print(f"     {C.DIM}{opt}{C.RESET}")
        print(f"\n{DIV}")
        print(f"  {C.DIM}↑ ↓  navegar    ENTER  selecionar    Q  sair{C.RESET}")

        ch = getch()
        if ch == '\x1b':
            getch()
            arrow = getch()
            if arrow == 'A': idx = (idx - 1) % len(options)
            elif arrow == 'B': idx = (idx + 1) % len(options)
        elif ch in ('\r', '\n'):
            return idx
        elif ch.lower() == 'q':
            sys.exit(0)

# ─── Main ───────────────────────────────────────────────────────

def main():
    config = {"jump_hosts": [], "servers": []}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            config = json.load(f)

    j_opts = [f"{j['user']}@{j['host']}" for j in config["jump_hosts"]] + ["+ Novo Jump Host"]
    idx = interactive_menu(j_opts, "Origem — Jump Host")

    if idx == len(j_opts) - 1:
        draw_header("Novo Jump Host")
        entry = input(f"\n  {C.LABEL}User@Host:{C.RESET}  ").strip()
        if "@" not in entry: return
        u, h = entry.split("@", 1)
        jump = {"host": h, "user": u}
        config["jump_hosts"].append(jump)
        with open(CONFIG_FILE, "w") as f: json.dump(config, f)
    else:
        jump = config["jump_hosts"][idx]

    session_pw = None
    if not os.path.exists(LOCAL_PEM):
        draw_header(f"{jump['user']}@{jump['host']}")
        step("⟳", "Sincronizando chave PEM...", C.ACCENT)
        session_pw = getpass.getpass(f"  {C.LABEL}Senha Jump ({jump['user']}):{C.RESET}  ")
        res = subprocess.run([
            "sshpass", "-p", session_pw, "scp",
            "-o", "StrictHostKeyChecking=no",
            f"{jump['user']}@{jump['host']}:~/.ssh/{PEM_FILE}",
            LOCAL_PEM
        ])
        if res.returncode == 0:
            os.chmod(LOCAL_PEM, 0o600)
            ok("Chave PEM sincronizada.")
        else:
            err("Falha no SCP. Verifique a senha ou a VPN.")
            sys.exit(1)

    j_str = f"{jump['user']}@{jump['host']}"
    svs   = sorted(config["servers"], key=lambda x: x["alias"].lower())
    s_opts = [f"{s['alias'].ljust(14)}  {C.DIVIDER}│{C.RESET}  {s['user']}@{s['host']}" for s in svs] + ["+ Novo Servidor"]
    idx   = interactive_menu(s_opts, "Destino — Servidor Interno", breadcrumb=j_str)

    if idx == len(s_opts) - 1:
        draw_header("Novo Servidor")
        alias       = input(f"\n  {C.LABEL}Alias (ex: Homolog):{C.RESET}  ").strip()
        entry       = input(f"  {C.LABEL}User@IP Interno:{C.RESET}    ").strip()
        if "@" not in entry: return
        u, h        = entry.split("@", 1)
        remote_path = input(f"  {C.LABEL}Path Remoto:{C.RESET}        ").strip()
        server = {"alias": alias, "host": h, "user": u, "root": remote_path}
        config["servers"].append(server)
        with open(CONFIG_FILE, "w") as f: json.dump(config, f)
    else:
        server = svs[idx]

    draw_header(breadcrumb=j_str, server=server)
    step("⟳", "Abrindo túnel SSH...")
    tunnel = open_tunnel(jump, server, cached_pw=session_pw)

    if not tunnel:
        err("Não foi possível abrir o túnel. Verifique a VPN e a senha.")
        sys.exit(1)

    host_base    = os.environ.get("HOST_PROJECT_PATH", ".")
    pem_path     = LOCAL_PEM.replace("/app", host_base) if IS_DOCKER else LOCAL_PEM
    ws_dir       = os.path.join(WS_ROOT, server["alias"])
    os.makedirs(ws_dir, mode=0o755, exist_ok=True)
    ws_path      = os.path.join(ws_dir, f"{server['alias']}.code-workspace")
    ws_data      = {"folders": [], "settings": {"sshfs.configs": [{
        "name": server["alias"], "host": "127.0.0.1", "port": TUNNEL_PORT,
        "username": server["user"], "privateKeyPath": pem_path, "root": server["root"]
    }]}}
    with open(ws_path, "w") as f:
        json.dump(ws_data, f, indent=4)

    display_path = os.path.abspath(ws_path).replace("/app", host_base) if IS_DOCKER else os.path.abspath(ws_path)

    draw_header(breadcrumb=j_str, server=server)
    print(f"\n  {C.SUCCESS}{C.BOLD}● TÚNEL ATIVO{C.RESET}  {C.DIM}localhost:{TUNNEL_PORT}{C.RESET}\n")
    print(DIV)

    print(f"\n  {C.BOLD}{C.INFO}1. ABRIR NO EDITOR{C.RESET}  {C.DIM}(copie e cole no terminal){C.RESET}\n")
    print(f"  {C.LABEL}Cursor{C.RESET}   {C.ACCENT}cursor \"{display_path}\"{C.RESET}")
    print(f"  {C.LABEL}VS Code{C.RESET}  {C.ACCENT}code   \"{display_path}\"{C.RESET}")

    print(f"\n{DIV}\n")
    print(f"  {C.BOLD}{C.INFO}2. CONECTAR SSH FS{C.RESET}\n")
    print(f"  {C.DIM}Instale a extensão antes de continuar:{C.RESET}")
    print(f"  {C.ACCENT}code --install-extension Kelvin.vscode-sshfs{C.RESET}")
    print(f"\n  {C.DIM}Ctrl+Shift+P  →  SSH FS: Add as Workspace folder  →  {C.RESET}{C.ACCENT}{server['alias']}{C.RESET}")

    print(f"\n{DIV}")
    try:
        input(f"\n  {C.WARN}Pressione ENTER para encerrar o túnel...{C.RESET}  ")
    finally:
        if isinstance(tunnel, subprocess.Popen):
            tunnel.terminate()
        print(f"\n  {C.DIM}Sessão encerrada.{C.RESET}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        sys.exit(0)
