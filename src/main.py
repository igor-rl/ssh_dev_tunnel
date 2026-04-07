#!/usr/bin/env python3

import json, os, sys, subprocess, socket, time, getpass, tty, termios
import urllib.request

# ─── Proteção contra sudo ───────────────────────────────────────
if os.geteuid() == 0:
    print("\n❌ Não execute este comando com sudo.\nExecute como usuário normal.\n")
    sys.exit(1)

# ─── Keyring ────────────────────────────────────────────────────
try:
    import keyring
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "keyring"], check=True)
    import keyring

# ─── Metadados ──────────────────────────────────────────────────
__author__  = "Igor Lage"
__company__ = "Precifica"
__version__ = "3.6.5"
IMAGE       = "ghcr.io/igor-rl/ssh_dev_tunnel:latest"

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
W   = 65
DIV = f"{C.DIVIDER}{'─' * W}{C.RESET}"

# ─── Detecção de Ambiente ───────────────────────────────────────
IS_DOCKER   = os.path.exists('/.dockerenv') or os.environ.get('HOST_PROJECT_PATH') is not None

# IMPORTANTE: Se estiver no Docker, BASE_DIR aponta para o volume montado.
# Caso contrário, aponta para a home local.
BASE_DIR    = "/home/tunnel/.dev_tunnel" if IS_DOCKER else os.path.expanduser("~/.dev_tunnel")
DATA_DIR    = os.path.join(BASE_DIR, ".data")
CONFIG_FILE = os.path.join(DATA_DIR, "servers.json")
WS_ROOT     = os.path.join(BASE_DIR, "workspaces")
LOCAL_SSH   = os.path.join(DATA_DIR, ".ssh")
TUNNEL_PORT = 2222

for d in [DATA_DIR, LOCAL_SSH, WS_ROOT]:
    if not os.path.exists(d):
        os.makedirs(d, mode=0o700, exist_ok=True)

# ─── Check for Updates ───────────────────────────────────────────
def check_for_updates():
    """Verifica a última tag lançada no repositório GitHub"""
    try:
        repo = "igor-rl/ssh_dev_tunnel"
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        
        with urllib.request.urlopen(url, timeout=2) as response:
            data = json.loads(response.read().decode())
            latest_version = data['tag_name'].replace('v', '')
            
            if latest_version != __version__:
                print(f"\n  {C.WARN}🔔 Nova versão disponível: {C.BOLD}{latest_version}{C.RESET}")
                print(f"  {C.DIM}Execute o pull da imagem ou baixe o novo script.{C.RESET}\n")
                print(DIV)
                time.sleep(1)
    except:
        pass

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
            if i == idx:
                print(f"  {C.ACCENT}▶  {C.BOLD}{opt}{C.RESET}")
            else:
                print(f"     {C.DIM}{opt}{C.RESET}")
        print(f"\n{DIV}")
        if footer_hint:
            print(f"  {C.DIM}{footer_hint}{C.RESET}")
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

# ─── Password Management ────────────────────────────────────────

def get_saved_password(user, host):
    try:
        return keyring.get_password(KEYRING_SERVICE, f"{user}@{host}")
    except Exception:
        return None

def save_password(user, host, password):
    try:
        keyring.set_password(KEYRING_SERVICE, f"{user}@{host}", password)
        return True
    except Exception as e:
        warn(f"Não foi possível salvar no keyring: {e}")
        return False

def delete_saved_password(user, host):
    try:
        keyring.delete_password(KEYRING_SERVICE, f"{user}@{host}")
    except Exception:
        pass

def get_jump_password(jump):
    user, host = jump['user'], jump['host']
    saved = get_saved_password(user, host)

    if saved:
        ok(f"Senha recuperada do keyring para {user}@{host}")
        return saved

    draw_header(f"{user}@{host}")
    pw = getpass.getpass(f"\n  {C.WARN}Senha {user}@{host}:{C.RESET}  ")

    print(f"\n  {C.BOLD}Salvar senha no keyring do sistema?{C.RESET}")
    print(f"  {C.DIM}(Gnome Keyring / macOS Keychain — acesso protegido pelo OS){C.RESET}\n")
    print(f"  {C.ACCENT}▶  S  Sim, salvar com segurança{C.RESET}")
    print(f"     N  Não, usar só agora{C.RESET}")
    print(f"\n{DIV}")

    ch = getch()
    if ch.lower() == 's':
        if save_password(user, host, pw):
            ok("Senha salva no keyring.")
        time.sleep(1)

    return pw

# ─── PEM Key Management ─────────────────────────────────────────

def list_remote_pem_keys(jump, password):
    cmd = [
        "sshpass", "-p", password,
        "ssh", "-o", "StrictHostKeyChecking=no",
        f"{jump['user']}@{jump['host']}",
        "ls ~/.ssh/*.pem ~/.ssh/*.ppk 2>/dev/null | xargs -I{} basename {}"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]

def sync_pem_key(jump, password, pem_filename):
    local_path = os.path.join(LOCAL_SSH, pem_filename)
    res = subprocess.run([
        "sshpass", "-p", password, "scp",
        "-o", "StrictHostKeyChecking=no",
        f"{jump['user']}@{jump['host']}:~/.ssh/{pem_filename}",
        local_path
    ])
    if res.returncode == 0:
        os.chmod(local_path, 0o600)
        return local_path
    return None

def choose_pem_for_server(jump, password, server, config, breadcrumb):
    server_key = f"{server['user']}@{server['host']}"
    saved_pem  = config.get("pem_by_server", {}).get(server_key)
    local_saved = os.path.join(LOCAL_SSH, saved_pem) if saved_pem else None

    if saved_pem and local_saved and os.path.exists(local_saved):
        ok(f"Usando chave salva para este destino: {saved_pem}")
        return local_saved, saved_pem

    draw_header(breadcrumb, server=server)
    step("⟳", "Buscando chaves disponíveis no jump host...", C.ACCENT)

    remote_keys = list_remote_pem_keys(jump, password)
    if not remote_keys:
        err("Nenhuma chave .pem ou .ppk encontrada em ~/.ssh/ do jump host.")
        sys.exit(1)

    display_opts = []
    for k in remote_keys:
        synced = f"  {C.DIM}[sincronizada]{C.RESET}" if os.path.exists(os.path.join(LOCAL_SSH, k)) else ""
        display_opts.append(f"{k}{synced}")

    idx = interactive_menu(display_opts, f"Escolha a chave para {server['alias']}", 
                           breadcrumb=breadcrumb,
                           footer_hint="As chaves listadas estão no seu Jump Host")

    chosen     = remote_keys[idx]
    local_path = os.path.join(LOCAL_SSH, chosen)

    if not os.path.exists(local_path):
        step("⟳", f"Sincronizando {chosen}...", C.ACCENT)
        if not sync_pem_key(jump, password, chosen):
            err("Falha no SCP ao sincronizar a chave.")
            sys.exit(1)
        ok(f"Chave {chosen} sincronizada.")
    else:
        ok(f"Chave {chosen} já disponível localmente.")

    if "pem_by_server" not in config:
        config["pem_by_server"] = {}
    config["pem_by_server"][server_key] = chosen
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

    return local_path, chosen

# ─── Main ───────────────────────────────────────────────────────

def main():
    check_for_updates()
    
    config = {"jump_hosts": [], "servers": [], "pem_by_server": {}}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            try:
                config = {**config, **json.load(f)}
            except: pass

    # 1. Selecionar Jump Host
    j_opts = [f"{j['user']}@{j['host']}" for j in config["jump_hosts"]] + ["+ Novo Jump Host"]
    idx = interactive_menu(j_opts, "1. Origem — Jump Host")

    if idx == len(j_opts) - 1:
        draw_header("Novo Jump Host")
        entry = input(f"\n  {C.LABEL}User@Host:{C.RESET}  ").strip()
        if "@" not in entry: return
        u, h = entry.split("@", 1)
        jump = {"host": h, "user": u}
        config["jump_hosts"].append(jump)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
    else:
        jump = config["jump_hosts"][idx]

    j_str = f"{jump['user']}@{jump['host']}"
    session_pw = get_jump_password(jump)

    # 2. Selecionar Servidor Interno
    svs = sorted(config["servers"], key=lambda x: x["alias"].lower())
    s_opts = [f"{s['alias'].ljust(14)}  {C.DIVIDER}│{C.RESET}  {s['user']}@{s['host']}" for s in svs] + ["+ Novo Servidor"]
    idx = interactive_menu(s_opts, "2. Destino — Servidor Interno", breadcrumb=j_str)

    if idx == len(s_opts) - 1:
        draw_header("Novo Servidor")
        alias = input(f"\n  {C.LABEL}Alias (ex: Homolog):{C.RESET}  ").strip()
        entry = input(f"  {C.LABEL}User@IP Interno:{C.RESET}    ").strip()
        if "@" not in entry: return
        u, h = entry.split("@", 1)
        remote_path = input(f"  {C.LABEL}Path Remoto:{C.RESET}        ").strip()
        server = {"alias": alias, "host": h, "user": u, "root": remote_path}
        config["servers"].append(server)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
    else:
        server = svs[idx]

    # 3. Selecionar Chave PEM
    local_pem, pem_filename = choose_pem_for_server(jump, session_pw, server, config, j_str)

    # 4. Abrir Túnel
    draw_header(breadcrumb=j_str, server=server)
    step("⟳", "Abrindo túnel SSH...")
    
    if is_port_open(TUNNEL_PORT):
        tunnel = "existing"
    else:
        cmd = [
            "sshpass", "-p", session_pw, "ssh", "-N", "-L",
            f"0.0.0.0:{TUNNEL_PORT}:{server['host']}:22",
            f"{jump['user']}@{jump['host']}",
            "-o", "StrictHostKeyChecking=no"
        ]
        tunnel = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        connected = False
        for _ in range(15):
            if is_port_open(TUNNEL_PORT):
                connected = True
                break
            time.sleep(1)
        
        if not connected:
            if not isinstance(tunnel, str): tunnel.terminate()
            err("Não foi possível abrir o túnel.")
            print(f"\n  {C.BOLD}Apagar senha salva no keyring?{C.RESET}  {C.DIM}[S/N]{C.RESET}  ", end="", flush=True)
            if getch().lower() == 's':
                delete_saved_password(jump['user'], jump['host'])
            sys.exit(1)

    # 5. Gerar Workspace
    # HOST_PROJECT_PATH deve ser o diretório base do projeto no seu WSL
    host_base = os.environ.get("HOST_PROJECT_PATH", ".")
    
    # Se estiver no Docker, precisamos converter o path interno /home/tunnel/... 
    # para o path externo do Host para que o VS Code consiga ler a chave.
    if IS_DOCKER:
        # A chave está em /home/tunnel/.dev_tunnel/.data/.ssh/...
        # O Host vê isso em HOST_PROJECT_PATH/.dev_tunnel/.data/.ssh/...
        pem_path = local_pem.replace("/home/tunnel", host_base)
    else:
        pem_path = local_pem

    ws_dir = os.path.join(WS_ROOT, server["alias"])
    os.makedirs(ws_dir, mode=0o755, exist_ok=True)
    ws_path = os.path.join(ws_dir, f"{server['alias']}.code-workspace")
    
    ws_data = {
        "folders": [], 
        "settings": {
            "sshfs.configs": [{
                "name": server["alias"], 
                "host": "127.0.0.1", 
                "port": TUNNEL_PORT,
                "username": server["user"], 
                "privateKeyPath": pem_path, 
                "root": server["root"]
            }]
        }
    }
    with open(ws_path, "w") as f:
        json.dump(ws_data, f, indent=4)

    # Converte o path do workspace para o display final
    display_path = os.path.abspath(ws_path).replace("/home/tunnel", host_base) if IS_DOCKER else os.path.abspath(ws_path)

    # 6. Output Final
    draw_header(breadcrumb=j_str, server=server)
    print(f"\n  {C.SUCCESS}{C.BOLD}● TÚNEL ATIVO{C.RESET}  {C.DIM}localhost:{TUNNEL_PORT}{C.RESET}")
    print(f"  {C.DIM}Chave vinculada:{C.RESET}  {C.ACCENT}{pem_filename}{C.RESET}\n")
    print(DIV)

    print(f"\n  {C.BOLD}{C.INFO}1. ABRIR NO EDITOR{C.RESET}\n")
    print(f"  {C.LABEL}Cursor{C.RESET}   {C.ACCENT}cursor \"{display_path}\"{C.RESET}")
    print(f"  {C.LABEL}VS Code{C.RESET}  {C.ACCENT}code   \"{display_path}\"{C.RESET}")

    print(f"\n{DIV}\n")
    print(f"  {C.BOLD}{C.INFO}2. CONECTAR SSH FS{C.RESET}\n")
    print(f"  {C.DIM}Ctrl+Shift+P  →  SSH FS: Add as Workspace folder  →  {C.RESET}{C.ACCENT}{server['alias']}{C.RESET}")

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