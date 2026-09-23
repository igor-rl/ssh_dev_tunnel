"""
workspace.py — Geração de .code-workspace e gerenciamento de entradas salvas.

FIXES:
- Cursor/VSCode: usa "remoteUser": "root" no SSH FS config para resolver permissão
  ao criar arquivos via interface do editor (NoPermissions FileSystemError).
- Editor: como a ferramenta roda direto na máquina do usuário (sem container),
  abre o workspace automaticamente via `cursor`/`code` quando encontrado no PATH;
  cai para instrução manual só se nenhum dos dois estiver disponível.
- Senha: salva automaticamente, sem perguntar ao usuário.
"""
import json, os, shutil, subprocess, time
from src.config import WS_ROOT, CONFIG_FILE, normalize_root, save_config
from src.ui import C, DIV, draw_header, interactive_menu, safe_input, ask_yes_no, abort
from src.vault import get_secret, save_secret, delete_secret, vault_key_for_jump
from src.explore import EXPLORE_ROOT


# ─── Geração do arquivo .code-workspace ──────────────────────────
def write_workspace(ws_file: str, server: dict, local_pem: str, tunnel_port: int) -> None:
    key_path_for_json = os.path.abspath(local_pem)
    server_root = normalize_root(server.get("root", "/"))

    ws_data = {
        "folders": [
            {
                "name": f"SSH FS - {server['alias']}",
                "uri":  f"ssh://{server['alias']}/"
            }
        ],
        "settings": {
            "sshfs.configs": [{
                "name":           server["alias"],
                "host":           "127.0.0.1",
                "port":           tunnel_port,
                "username":       server["user"],
                "privateKeyPath": key_path_for_json,
                "root":           server_root,
                # FIX: conecta como root para ter permissão de criar/editar
                # arquivos via interface do Cursor/VSCode sem erro NoPermissions.
                "sudo":           True,
                "remoteUser":     "root",
                "algorithms": {
                    "serverHostKey": ["ssh-rsa", "ssh-dss", "ecdsa-sha2-nistp256", "ssh-ed25519"],
                    "pubkey":        ["ssh-rsa", "ecdsa-sha2-nistp256", "ssh-ed25519"]
                }
            }],
            # FIX: arquivos remotos estão em ISO-8859-1 (Latin-1); sem isso o
            # editor tenta ler como UTF-8 e acentos/caracteres especiais
            # aparecem corrompidos (ex: "pre�o" em vez de "preço").
            "files.encoding":          "iso88591",
            "files.autoGuessEncoding": False,
        }
    }

    with open(ws_file, "w") as f:
        json.dump(ws_data, f, indent=4)


def workspace_path_for(server: dict) -> tuple[str, str]:
    """Retorna (ws_file, display_path) — ambos o mesmo caminho absoluto local."""
    ws_dir  = os.path.join(WS_ROOT, server["alias"])
    os.makedirs(ws_dir, mode=0o755, exist_ok=True)
    ws_file      = os.path.join(ws_dir, f"{server['alias']}.code-workspace")
    display_path = os.path.abspath(ws_file)
    return ws_file, display_path


# ─── Instrução para abrir editor ─────────────────────────────────
def show_editor_instructions(display_path: str, breadcrumb: str,
                              draw_header_fn, editor_pref: str | None = None,
                              menu_fn=None) -> None:
    """
    Abre o workspace automaticamente no editor certo:
    - editor_pref='cursor'/'vscode' força esse editor (via --cursor/--vscode);
    - com só um editor instalado, usa esse;
    - com os dois instalados e sem preferência, pergunta (se menu_fn dado);
    - sem nenhum editor no PATH, mostra o comando para rodar manualmente.
    """
    draw_header_fn(breadcrumb)
    print(f"\n  {C.BOLD}{C.INFO}ABRIR WORKSPACE NO EDITOR{C.RESET}\n")
    print(f"  {C.LABEL}Caminho do workspace:{C.RESET}")
    print(f"  {C.ACCENT}{display_path}{C.RESET}\n")
    print(f"{DIV()}")

    cursor_bin = shutil.which("cursor")
    code_bin   = shutil.which("code")
    available  = [k for k, b in (("cursor", cursor_bin), ("vscode", code_bin)) if b]

    chosen_key = None
    if editor_pref in available:
        chosen_key = editor_pref
    elif len(available) == 1:
        chosen_key = available[0]
    elif len(available) > 1 and menu_fn:
        labels = {"cursor": "Cursor", "vscode": "VS Code"}
        idx = menu_fn([labels[k] for k in available], "Qual editor abrir?", breadcrumb)
        chosen_key = available[idx]
    elif available:
        chosen_key = available[0]

    if chosen_key == "cursor":
        # Cursor tem modos ambíguos: "editor" força IDE em vez do agent/chat;
        # "--classic" desativa o dashboard "glass" novo (Cursor 2.0) que abre
        # em vez do editor clássico direto.
        name, args = "Cursor", [cursor_bin, "editor", "--classic", display_path]
    elif chosen_key == "vscode":
        name, args = "VS Code", [code_bin, display_path]
    else:
        name, args = None, None

    if args:
        try:
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"  {C.SUCCESS}✔  Abrindo no {name}...{C.RESET}\n")
        except OSError:
            manual = " ".join(args[:-1] + [f'"{display_path}"'])
            print(f"  {C.WARN}⚠  Não consegui abrir automaticamente. Rode manualmente:{C.RESET}\n")
            print(f"  {C.ACCENT}{manual}{C.RESET}\n")
    else:
        print(f"  {C.DIM}Nenhum editor (cursor/code) encontrado no PATH. Rode manualmente:{C.RESET}\n")
        print(f"  {C.LABEL}Cursor :{C.RESET}  {C.ACCENT}cursor editor --classic \"{display_path}\"{C.RESET}")
        print(f"  {C.LABEL}VS Code:{C.RESET}  {C.ACCENT}code                    \"{display_path}\"{C.RESET}\n")

    print(f"{DIV()}")
    print(f"  {C.DIM}Túnel já está ativo. Pressione ENTER para continuar...{C.RESET}  ", end="", flush=True)
    try:
        input()
    except KeyboardInterrupt:
        abort()


# ─── CRUD de Workspaces Salvos ───────────────────────────────────
def load_workspaces(config: dict) -> list[dict]:
    return config.get("saved_workspaces", [])


def save_workspace_entry(config: dict, entry: dict) -> None:
    ws_list = config.setdefault("saved_workspaces", [])
    ws_list = [w for w in ws_list if w.get("alias") != entry["alias"]]
    ws_list.append(entry)
    config["saved_workspaces"] = ws_list
    save_config(config)


def delete_workspace_entry(config: dict, alias: str) -> None:
    config["saved_workspaces"] = [
        w for w in config.get("saved_workspaces", [])
        if w.get("alias") != alias
    ]
    save_config(config)


# ─── Edição de Conexão Salva ─────────────────────────────────────
def _split_user_host(raw: str) -> tuple[str, str] | None:
    raw = raw.strip()
    if "@" not in raw:
        return None
    user, host = raw.split("@", 1)
    if not user or not host:
        return None
    return user, host


def _rename_local_dirs(old_alias: str, new_alias: str) -> None:
    """Move as pastas geradas (workspace do editor / contexto da IA) para o novo nome."""
    for root in (WS_ROOT, EXPLORE_ROOT):
        src_dir = os.path.join(root, old_alias)
        dst_dir = os.path.join(root, new_alias)
        if os.path.isdir(src_dir) and not os.path.exists(dst_dir):
            try:
                os.rename(src_dir, dst_dir)
            except OSError:
                pass
    # O .code-workspace é regerado com o novo nome na próxima conexão.
    stale = os.path.join(WS_ROOT, new_alias, f"{old_alias}.code-workspace")
    if os.path.exists(stale):
        try:
            os.remove(stale)
        except OSError:
            pass


def apply_connection_edit(config: dict, old_alias: str, new: dict) -> str | None:
    """
    Aplica a edição de uma conexão salva e persiste. Retorna mensagem de erro ou None.
    `new`: alias, jump_user, jump_host, user, host, root, reset_pem.
    """
    saved  = config.setdefault("saved_workspaces", [])
    ws     = next((w for w in saved if w.get("alias") == old_alias), None)
    server = next((s for s in config["servers"] if s["alias"] == old_alias), None)
    if not ws or not server:
        return "Conexão não encontrada na configuração."

    alias = new["alias"].strip()
    if not alias:
        return "O nome não pode ser vazio."
    if alias != old_alias and (
        any(s["alias"] == alias for s in config["servers"])
        or any(w.get("alias") == alias for w in saved)
    ):
        return f"Já existe uma conexão chamada '{alias}'."

    # ── Jump Host: pode ser compartilhado por outras conexões ─────
    old_jump_label = ws.get("jump_label", "")
    new_jump       = {"host": new["jump_host"], "user": new["jump_user"]}
    new_jump_label = f"{new_jump['user']}@{new_jump['host']}"

    if new_jump_label != old_jump_label:
        jumps = config.setdefault("jump_hosts", [])
        if not any(f"{j['user']}@{j['host']}" == new_jump_label for j in jumps):
            jumps.append(new_jump)

        old_jump   = next((j for j in jumps if f"{j['user']}@{j['host']}" == old_jump_label), None)
        still_used = any(w.get("jump_label") == old_jump_label for w in saved if w is not ws)
        if old_jump and not still_used:
            # Mesmo usuário (ex: só mudou o IP) → reaproveita a senha salva;
            # se estiver errada, o authenticate() pede de novo.
            old_key, new_key = vault_key_for_jump(old_jump), vault_key_for_jump(new_jump)
            pw = get_secret(old_key)
            if pw and old_jump["user"] == new_jump["user"] and not get_secret(new_key):
                save_secret(new_key, pw)
            delete_secret(old_key)
            jumps.remove(old_jump)

    # ── Servidor + chave PEM (indexada por user@host) ─────────────
    old_key = f"{server['user']}@{server['host']}"
    new_key = f"{new['user']}@{new['host']}"
    pems    = config.setdefault("pem_by_server", {})

    if new_key != old_key and old_key in pems:
        pems.setdefault(new_key, pems[old_key])
        if not any(f"{s['user']}@{s['host']}" == old_key for s in config["servers"] if s is not server):
            del pems[old_key]
    if new.get("reset_pem"):
        pems.pop(new_key, None)

    server.update({
        "alias": alias, "user": new["user"], "host": new["host"],
        "root":  normalize_root(new["root"]),
    })

    ws.update({
        "alias":        alias,
        "route":        f"{new_jump_label}  →  {new_key}",
        "jump_label":   new_jump_label,
        "server_label": new_key,
    })

    if alias != old_alias:
        _rename_local_dirs(old_alias, alias)

    save_config(config)
    return None


def edit_connection_screen(config: dict, ws: dict, draw_header_fn) -> None:
    """Edita nome, jump host, servidor, path remoto e chave PEM de uma conexão salva."""
    old_alias  = ws["alias"]
    server     = next((s for s in config["servers"] if s["alias"] == old_alias), None)
    jump_parts = _split_user_host(ws.get("jump_label", ""))
    if not server or not jump_parts:
        print(f"\n  {C.ERROR}✘  Dados da conexão incompletos — remova e crie de novo.{C.RESET}")
        time.sleep(1.5)
        return

    draft = {
        "alias":     old_alias,
        "jump_user": jump_parts[0], "jump_host": jump_parts[1],
        "user":      server["user"], "host":     server["host"],
        "root":      normalize_root(server.get("root", "/")),
        "reset_pem": False,
    }
    breadcrumb = f"Editar — {old_alias}"
    idx        = 0

    def _ask(label: str, current: str) -> str:
        draw_header_fn(breadcrumb)
        print(f"\n  {C.DIM}ENTER mantém o valor atual.{C.RESET}")
        value = safe_input(f"\n  {C.LABEL}{label}:{C.RESET}  ", prefill=current).strip()
        return value or current

    def _ask_user_host(label: str, user_k: str, host_k: str) -> None:
        raw   = _ask(label, f"{draft[user_k]}@{draft[host_k]}")
        parts = _split_user_host(raw)
        if not parts:
            print(f"\n  {C.ERROR}Formato inválido. Use user@host{C.RESET}")
            time.sleep(1.2)
            return
        draft[user_k], draft[host_k] = parts

    while True:
        pems     = config.get("pem_by_server", {})
        pem_name = (pems.get(f"{draft['user']}@{draft['host']}")
                    or pems.get(f"{server['user']}@{server['host']}"))
        pem_label = pem_name if pem_name and not draft["reset_pem"] else "(escolher na próxima conexão)"

        opts = [
            f"Nome         │  {draft['alias']}",
            f"Jump Host    │  {draft['jump_user']}@{draft['jump_host']}",
            f"Servidor     │  {draft['user']}@{draft['host']}",
            f"Path Remoto  │  {draft['root']}",
            f"Chave PEM    │  {pem_label}",
            "✔  Salvar alterações",
            "← Cancelar",
        ]
        idx = interactive_menu(opts, f"Editar conexão — {old_alias}", "Início",
                               footer_hint="ENTER  editar campo",
                               draw_header_fn=draw_header_fn, initial=idx)

        if idx == 0:
            draft["alias"] = _ask("Nome", draft["alias"])
        elif idx == 1:
            _ask_user_host("Jump Host (user@host)", "jump_user", "jump_host")
        elif idx == 2:
            _ask_user_host("Servidor (user@IP)", "user", "host")
        elif idx == 3:
            draft["root"] = normalize_root(_ask("Path Remoto", draft["root"]))
        elif idx == 4:
            draw_header_fn(breadcrumb)
            draft["reset_pem"] = ask_yes_no(
                "Escolher outra chave PEM no jump host na próxima conexão?",
                default_no=not draft["reset_pem"])
        elif idx == 5:
            err = apply_connection_edit(config, old_alias, draft)
            if err:
                print(f"\n  {C.ERROR}✘  {err}{C.RESET}")
                time.sleep(1.5)
                continue
            print(f"\n  {C.SUCCESS}✔  Conexão '{draft['alias']}' atualizada.{C.RESET}")
            time.sleep(0.8)
            return
        else:
            return


def workspace_crud_screen(config: dict, draw_header_fn) -> dict | None:
    """
    Tela inicial: lista conexões salvas (jump host + servidor), reutilizadas
    por qualquer um dos recursos (IDE/IA/Terminal).
    Retorna a conexão escolhida (dict) ou None para fluxo de nova conexão.
    """
    ws_list = load_workspaces(config)

    while True:
        draw_header_fn("Conexões Salvas")

        if not ws_list:
            print(f"\n  {C.DIM}Nenhuma conexão salva ainda.{C.RESET}\n")
            opts = ["+ Nova Conexão (configurar manualmente)", "Sair"]
            idx  = interactive_menu(opts, "Conexões", "Início",
                                    draw_header_fn=draw_header_fn)
            if idx == 0:
                return None
            abort()

        labels = [
            f"{w['alias'].ljust(16)}  │  {w.get('route', '')}"
            for w in ws_list
        ]
        labels += ["+ Nova Conexão", "✎  Editar Conexão", "⊘  Remover Conexão", "Sair"]

        idx = interactive_menu(
            labels,
            "Selecione uma Conexão",
            "Início",
            footer_hint="ENTER  conectar    Q  sair",
            draw_header_fn=draw_header_fn,
        )

        n = len(ws_list)

        if idx < n:
            return ws_list[idx]
        elif idx == n:
            return None
        elif idx == n + 1:
            ed_labels = [w["alias"] for w in ws_list] + ["← Cancelar"]
            ed_idx    = interactive_menu(ed_labels, "Editar — qual conexão?", "Início",
                                         draw_header_fn=draw_header_fn)
            if ed_idx < len(ws_list):
                edit_connection_screen(config, ws_list[ed_idx], draw_header_fn)
                ws_list = load_workspaces(config)
        elif idx == n + 2:
            rm_labels = [w["alias"] for w in ws_list] + ["← Cancelar"]
            rm_idx    = interactive_menu(rm_labels, "Remover — qual conexão?", "Início",
                                         draw_header_fn=draw_header_fn)
            if rm_idx < len(ws_list):
                chosen_alias = ws_list[rm_idx]["alias"]
                delete_workspace_entry(config, chosen_alias)
                config["saved_workspaces"] = [
                    w for w in config.get("saved_workspaces", [])
                    if w["alias"] != chosen_alias
                ]
                ws_list = load_workspaces(config)
                print(f"\n  {C.SUCCESS}✔  Conexão '{chosen_alias}' removida.{C.RESET}")
                time.sleep(0.8)
        else:
            abort()