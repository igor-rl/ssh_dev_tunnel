"""
config.py — Caminhos, diretórios e carregamento/salvamento do JSON de configuração.
"""
import json, os

# ─── Metadados ──────────────────────────────────────────────────
__author__  = "Igor Lage"
__company__ = "Precifica"
__version__ = "3.7.7"

# ─── Estrutura de Diretórios ─────────────────────────────────────
# HOST_PROJECT_PATH é injetado pelo docker run (ex: $HOME do host).
# O Python concatena "/.dev_tunnel" para compor o caminho no host.
HOST_PROJECT_PATH = os.environ.get("HOST_PROJECT_PATH", "") + "/.dev_tunnel"

_CANDIDATE_A = "/home/tunnel/.dev_tunnel"
_CANDIDATE_B = "/app/.dev_tunnel"

BASE_DIR = _CANDIDATE_A if os.path.exists(_CANDIDATE_A) else _CANDIDATE_B

DATA_DIR       = os.path.join(BASE_DIR, ".data")
CONFIG_FILE    = os.path.join(DATA_DIR, "servers.json")
WS_ROOT        = os.path.join(BASE_DIR, "workspaces")
LOCAL_SSH      = os.path.join(DATA_DIR, ".ssh")
PASSWORDS_FILE = os.path.join(DATA_DIR, ".passwords")

for _d in [BASE_DIR, DATA_DIR, LOCAL_SSH, WS_ROOT]:
    os.makedirs(_d, mode=0o755, exist_ok=True)


# ─── Conversor de caminhos ───────────────────────────────────────
def to_host_path(container_path: str) -> str:
    """Converte caminho interno do container para caminho no host."""
    if not HOST_PROJECT_PATH:
        return container_path
    abs_internal = os.path.abspath(container_path)
    if abs_internal.startswith(BASE_DIR):
        rel = os.path.relpath(abs_internal, BASE_DIR)
        return os.path.join(HOST_PROJECT_PATH, rel).replace("\\", "/")
    return container_path


def to_wsl_path(internal_path: str) -> str:
    """Alias de to_host_path para uso em exibição de workspace."""
    abs_internal = os.path.abspath(internal_path)
    if HOST_PROJECT_PATH and abs_internal.startswith(BASE_DIR):
        rel = os.path.relpath(abs_internal, BASE_DIR)
        return os.path.join(HOST_PROJECT_PATH, rel)
    return abs_internal


def normalize_root(root: str) -> str:
    if not root:
        return "/"
    root = root.strip()
    if not root.startswith("/"):
        root = "/" + root
    return root


# ─── Carregamento / Persistência de Configuração ─────────────────
_EMPTY_CONFIG: dict = {
    "jump_hosts":       [],
    "servers":          [],
    "pem_by_server":    {},
    "saved_workspaces": [],
}


def load_config() -> dict:
    config = dict(_EMPTY_CONFIG)
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            try:
                config.update(json.load(f))
            except json.JSONDecodeError:
                pass
    return config


def save_config(config: dict) -> None:
    tmp = CONFIG_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(config, f, indent=4)
    os.replace(tmp, CONFIG_FILE)