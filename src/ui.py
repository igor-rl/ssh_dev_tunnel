"""
ui.py — Paleta de cores, layout adaptativo e menus interativos.
"""
import os, sys, tty, termios, readline, shutil

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


# ─── Layout adaptativo ──────────────────────────────────────────
def _term_width() -> int:
    try:
        return min(shutil.get_terminal_size((72, 24)).columns, 80)
    except Exception:
        return 72


def DIV() -> str:
    w = _term_width() - 2
    return f"{C.DIVIDER}{'─' * w}{C.RESET}"


def tag(label, value, color=C.INFO):
    return f"  {C.LABEL}{label:<8}{C.RESET}  {color}{value}{C.RESET}"


# ─── Header ─────────────────────────────────────────────────────
def draw_header(breadcrumb: str = "", server: dict | None = None,
                version: str = "", company: str = "", tunnel_port: int = 0) -> None:
    os.system("clear")
    mode = "DOCKER" if os.environ.get("HOST_PROJECT_PATH") else "LOCAL"
    d = DIV()
    print(d)
    print(f"  {C.BOLD}{C.INFO}{company.upper()}{C.RESET}  {C.DIVIDER}│{C.RESET}  "
          f"{C.ACCENT}{C.BOLD}SSH DEV TUNNEL{C.RESET}  {C.DIM}v{version}  [{mode}]{C.RESET}")
    print(d)
    if server:
        print(tag("SESSÃO",  server.get('alias', 'NOVO').upper(), C.ACCENT))
        print(tag("ROTA",    f"{breadcrumb}  {C.DIM}→{C.RESET}  {C.INFO}{server['user']}@{server['host']}"))
        print(tag("PORTA",   f"localhost:{tunnel_port}", C.WARN))
        print(d)
    elif breadcrumb:
        print(tag("PATH", breadcrumb))
        print(d)


# ─── Saída limpa ────────────────────────────────────────────────
def abort(msg: str = "Cancelado.") -> None:
    print(f"\n\n  {C.DIM}{msg}{C.RESET}\n")
    sys.exit(0)


def _flush_stdin() -> None:
    try:
        fd = sys.stdin.fileno()
        termios.tcflush(fd, termios.TCIFLUSH)
    except Exception:
        pass


# ─── Leitura de tecla única ─────────────────────────────────────
def getch() -> str:
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x03':
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
            abort()
        return ch
    except KeyboardInterrupt:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        abort()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


# ─── Input com prefill ──────────────────────────────────────────
def safe_input(prompt: str, prefill: str = "") -> str:
    if not sys.stdin.isatty():
        try:
            return input(prompt)
        except KeyboardInterrupt:
            abort()
    if prefill:
        readline.set_startup_hook(lambda: readline.insert_text(prefill))
    try:
        return input(prompt)
    except KeyboardInterrupt:
        abort()
    finally:
        readline.set_startup_hook()


# ─── Getpass com máscara e edição ───────────────────────────────
def safe_getpass(prompt: str) -> str:
    fd  = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    buf: list[str] = []
    pos: int       = 0
    sys.stdout.write(prompt)
    sys.stdout.flush()
    tty.setraw(fd)

    def _redraw() -> None:
        if pos > 0:
            sys.stdout.write(f"\033[{pos}D")
        sys.stdout.write("\033[K")
        masked = "*" * len(buf)
        sys.stdout.write(masked)
        chars_after = len(buf) - pos
        if chars_after > 0:
            sys.stdout.write(f"\033[{chars_after}D")
        sys.stdout.flush()

    try:
        while True:
            ch = os.read(fd, 1)
            if ch == b'\x03':
                sys.stdout.write("\n")
                sys.stdout.flush()
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
                abort()
            elif ch in (b'\r', b'\n'):
                break
            elif ch == b'\x15':
                buf.clear(); pos = 0; _redraw()
            elif ch in (b'\x7f', b'\x08'):
                if pos > 0:
                    buf.pop(pos - 1); pos -= 1; _redraw()
            elif ch == b'\x1b':
                seq = os.read(fd, 1)
                if seq == b'[':
                    seq2 = os.read(fd, 1)
                    if seq2 == b'D':
                        if pos > 0:
                            pos -= 1
                            sys.stdout.write("\033[1D"); sys.stdout.flush()
                    elif seq2 == b'C':
                        if pos < len(buf):
                            pos += 1
                            sys.stdout.write("\033[1C"); sys.stdout.flush()
                    elif seq2 in (b'H', b'1'):
                        if seq2 == b'1': os.read(fd, 1)
                        if pos > 0:
                            sys.stdout.write(f"\033[{pos}D"); sys.stdout.flush()
                        pos = 0
                    elif seq2 in (b'F', b'4'):
                        if seq2 == b'4': os.read(fd, 1)
                        if pos < len(buf):
                            sys.stdout.write(f"\033[{len(buf) - pos}C"); sys.stdout.flush()
                        pos = len(buf)
                    elif seq2 == b'3':
                        os.read(fd, 1)
                        if pos < len(buf):
                            buf.pop(pos); _redraw()
                    elif seq2 in (b'A', b'B'):
                        pass
            elif ch >= b' ':
                char = ch.decode("utf-8", errors="replace")
                buf.insert(pos, char); pos += 1; _redraw()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write("\n"); sys.stdout.flush()
    return "".join(buf)


# ─── Confirmação S/N ────────────────────────────────────────────
def ask_yes_no(question: str, default_no: bool = True) -> bool:
    hint = "S  Sim  /  N  Não (padrão)" if default_no else "S  Sim (padrão)  /  N  Não"
    print(f"\n  {C.BOLD}{question}{C.RESET}")
    print(f"  {C.ACCENT}▶  {hint}{C.RESET}  ", end="", flush=True)
    _flush_stdin()
    ch = getch()
    print()
    return ch.lower() == 's'


# ─── Menu interativo ─────────────────────────────────────────────
def interactive_menu(options: list[str], title: str,
                     breadcrumb: str = "", footer_hint: str | None = None,
                     draw_header_fn=None) -> int:
    idx = 0
    while True:
        if draw_header_fn:
            draw_header_fn(breadcrumb)
        print(f"\n  {C.BOLD}{C.INFO}{title.upper()}{C.RESET}\n")
        for i, opt in enumerate(options):
            if i == idx:
                print(f"  {C.ACCENT}▶  {C.BOLD}{opt}{C.RESET}")
            else:
                print(f"     {C.DIM}{opt}{C.RESET}")
        print(f"\n{DIV()}")
        if footer_hint:
            print(f"  {C.DIM}{footer_hint}{C.RESET}")
        print(f"  {C.DIM}↑ ↓  navegar    ENTER  selecionar    Q  sair{C.RESET}")
        ch = getch()
        if ch == '\x1b':
            getch(); arrow = getch()
            if arrow == 'A':   idx = (idx - 1) % len(options)
            elif arrow == 'B': idx = (idx + 1) % len(options)
        elif ch in ('\r', '\n'):
            return idx
        elif ch.lower() == 'q':
            abort()