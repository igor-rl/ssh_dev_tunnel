"""
tunnel.py — Operações SSH: teste de conexão, cópia de PEM, túnel reverso.
"""
import os, socket, subprocess, time
from src.config import LOCAL_SSH, CONFIG_FILE, save_config


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


def is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _fix_ownership(path: str) -> None:
    try:
        os.chown(path, 1000, 1000)
    except (PermissionError, OSError):
        pass


# ─── Teste de autenticação SSH ───────────────────────────────────
def test_ssh(jump: dict, password: str) -> bool:
    cmd = [
        "sshpass", "-p", password,
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=8",
        f"{jump['user']}@{jump['host']}",
        "echo OK"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0 and "OK" in result.stdout


# ─── Gerenciamento de PEM ────────────────────────────────────────
def choose_pem_for_server(jump: dict, password: str, server: dict,
                           config: dict, menu_fn) -> tuple[str, str]:
    """
    Retorna (local_path, filename) do PEM para o servidor.
    Reutiliza PEM já salvo ou guia o usuário para escolher um no jump host.
    """
    server_key = f"{server['user']}@{server['host']}"
    saved_pem  = config.get("pem_by_server", {}).get(server_key)
    local_path = os.path.join(LOCAL_SSH, saved_pem) if saved_pem else None

    if saved_pem and local_path and os.path.exists(local_path):
        _fix_ownership(local_path)
        os.chmod(local_path, 0o600)
        return local_path, saved_pem

    print(f"\n  \033[38;5;75m⟳  Buscando chaves no jump host...\033[0m")
    cmd = [
        "sshpass", "-p", password,
        "ssh", "-o", "StrictHostKeyChecking=no",
        f"{jump['user']}@{jump['host']}",
        "ls ~/.ssh/*.pem ~/.ssh/*.ppk 2>/dev/null | xargs -I{} basename {}"
    ]
    remote_keys = subprocess.run(cmd, capture_output=True, text=True).stdout.splitlines()

    if not remote_keys:
        print(f"  \033[38;5;196m✘ Nenhuma chave encontrada no Jump Host.\033[0m")
        import sys; sys.exit(1)

    idx     = menu_fn(remote_keys, f"Chave para {server['alias']}", jump["host"])
    chosen  = remote_keys[idx]
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
    save_config(config)
    return local_dest, chosen


# ─── Túnel SSH ───────────────────────────────────────────────────
def start_tunnel(jump: dict, password: str, server: dict, port: int) -> subprocess.Popen | str:
    """
    Abre o túnel SSH reverso se a porta ainda não estiver em uso.
    Retorna o processo Popen ou a string 'existing' se já havia túnel.
    """
    if is_port_open(port):
        return "existing"

    cmd = [
        "sshpass", "-p", password,
        "ssh", "-N",
        "-L", f"0.0.0.0:{port}:{server['host']}:22",
        f"{jump['user']}@{jump['host']}",
        "-o", "StrictHostKeyChecking=no"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    return proc