"""
config.py — Caminhos, diretórios e carregamento/salvamento do JSON de configuração.
"""
import json, os

# ─── Metadados ──────────────────────────────────────────────────
__author__  = "Igor Lage"
__company__ = "Precifica"
__version__ = "3.9.2"

# ─── Estrutura de Diretórios ─────────────────────────────────────
BASE_DIR       = os.path.expanduser("~/.dev_tunnel")
DATA_DIR       = os.path.join(BASE_DIR, ".data")
CONFIG_FILE    = os.path.join(DATA_DIR, "servers.json")
WS_ROOT        = os.path.join(BASE_DIR, "workspaces")
LOCAL_SSH      = os.path.join(DATA_DIR, ".ssh")
PASSWORDS_FILE = os.path.join(DATA_DIR, ".passwords")

for _d in [BASE_DIR, DATA_DIR, LOCAL_SSH, WS_ROOT]:
    os.makedirs(_d, mode=0o755, exist_ok=True)


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
