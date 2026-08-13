"""
vault.py — Armazenamento de senhas em duas camadas de segurança.

1) OS Keyring (macOS Keychain / Windows Credential Manager / Linux Secret
   Service) — usado quando disponível. É a opção mais segura: a senha nunca
   toca o disco em texto legível pela aplicação.
2) Fallback — arquivo local criptografado (Fernet/AES-128) quando não há
   backend de keyring disponível no sistema (ex: Linux sem Secret Service).
   A chave de criptografia fica em arquivo separado (".passwords.key"),
   chmod 600, fora do arquivo de dados.

Migração automática: se o arquivo de senhas ainda estiver no formato legado
(texto plano "chave=valor"), ele é lido, criptografado e regravado na
primeira leitura — sem exigir que o usuário refaça login.

Senha continua sendo salva automaticamente após autenticação bem-sucedida,
sem perguntar ao usuário — decisão de UX mantida, só a estratégia de
armazenamento mudou.
"""
import os
from src.config import PASSWORDS_FILE

SERVICE_NAME = "ssh-dev-tunnel"
KEY_FILE     = PASSWORDS_FILE + ".key"


# ─── Backend 1: OS Keyring ────────────────────────────────────────
def _keyring_backend():
    """Retorna o módulo `keyring` se houver um backend real disponível, senão None."""
    try:
        import keyring
        from keyring.backends.fail import Keyring as FailKeyring
        if isinstance(keyring.get_keyring(), FailKeyring):
            return None
        return keyring
    except Exception:
        return None


# ─── Backend 2: arquivo local criptografado (fallback) ────────────
def _get_or_create_key() -> bytes:
    from cryptography.fernet import Fernet
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    os.chmod(KEY_FILE, 0o600)
    return key


def _fernet():
    from cryptography.fernet import Fernet
    return Fernet(_get_or_create_key())


def _parse_lines(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            result[k] = v
    return result


def _load_encrypted() -> dict[str, str]:
    if not os.path.exists(PASSWORDS_FILE):
        return {}
    try:
        with open(PASSWORDS_FILE, "rb") as fh:
            raw = fh.read()
    except OSError:
        return {}
    if not raw:
        return {}

    from cryptography.fernet import InvalidToken
    try:
        decrypted = _fernet().decrypt(raw).decode("utf-8")
        return _parse_lines(decrypted)
    except InvalidToken:
        # Arquivo legado em texto plano — migra para o formato criptografado.
        try:
            legacy = _parse_lines(raw.decode("utf-8"))
        except UnicodeDecodeError:
            return {}
        if legacy:
            _save_encrypted(legacy)
        return legacy


def _save_encrypted(data: dict[str, str]) -> None:
    plain     = "\n".join(f"{k}={v}" for k, v in data.items())
    encrypted = _fernet().encrypt(plain.encode("utf-8"))
    tmp = PASSWORDS_FILE + ".tmp"
    try:
        with open(tmp, "wb") as f:
            f.write(encrypted)
        os.replace(tmp, PASSWORDS_FILE)
        os.chmod(PASSWORDS_FILE, 0o600)
    except OSError as e:
        import sys
        print(f"\n  ⚠  Não foi possível salvar senhas: {e}\n", file=sys.stderr)


# ─── API pública ───────────────────────────────────────────────────
def save_secret(key: str, value: str) -> None:
    kr = _keyring_backend()
    if kr:
        kr.set_password(SERVICE_NAME, key, value)
        return
    data = _load_encrypted()
    data[key] = value
    _save_encrypted(data)


def get_secret(key: str) -> str | None:
    kr = _keyring_backend()
    if kr:
        return kr.get_password(SERVICE_NAME, key)
    return _load_encrypted().get(key)


def delete_secret(key: str) -> None:
    kr = _keyring_backend()
    if kr:
        try:
            kr.delete_password(SERVICE_NAME, key)
        except Exception:
            pass
        return
    data = _load_encrypted()
    if key in data:
        del data[key]
        _save_encrypted(data)


# ─── Helpers de domínio ──────────────────────────────────────────
def vault_key_for_jump(jump: dict) -> str:
    return f"jump:{jump['user']}@{jump['host']}"
