"""
vault.py — Armazenamento seguro de senhas em arquivo de texto plano.

Formato do arquivo: uma entrada por linha, "chave=valor".
O arquivo recebe chmod 600 após cada escrita.

BUG FIX: garante que o arquivo seja criado com owner 1000:1000
para que o usuário `tunnel` possa lê-lo em execuções futuras.
"""
import os
from src.config import PASSWORDS_FILE


def _fix_ownership(path: str) -> None:
    """Garante owner 1000:1000 (usuário tunnel dentro do container)."""
    try:
        os.chown(path, 1000, 1000)
    except (PermissionError, OSError):
        pass


def _load() -> dict[str, str]:
    result: dict[str, str] = {}
    if not os.path.exists(PASSWORDS_FILE):
        return result
    try:
        with open(PASSWORDS_FILE, "r") as f:
            for line in f:
                line = line.rstrip("\n")
                if "=" in line:
                    k, v = line.split("=", 1)
                    result[k] = v
    except OSError:
        pass
    return result


def _save(data: dict[str, str]) -> None:
    tmp = PASSWORDS_FILE + ".tmp"
    try:
        with open(tmp, "w") as f:
            for k, v in data.items():
                f.write(f"{k}={v}\n")
        os.replace(tmp, PASSWORDS_FILE)
        os.chmod(PASSWORDS_FILE, 0o600)
        # BUG FIX: garante que o usuário tunnel possa ler o arquivo
        _fix_ownership(PASSWORDS_FILE)
    except OSError as e:
        import sys
        print(f"\n  ⚠  Não foi possível salvar senhas: {e}\n", file=sys.stderr)


def save_secret(key: str, value: str) -> None:
    data = _load()
    data[key] = value
    _save(data)


def get_secret(key: str) -> str | None:
    return _load().get(key)


def delete_secret(key: str) -> None:
    data = _load()
    if key in data:
        del data[key]
        _save(data)


# ─── Helpers de domínio ──────────────────────────────────────────
def vault_key_for_jump(jump: dict) -> str:
    return f"jump:{jump['user']}@{jump['host']}"