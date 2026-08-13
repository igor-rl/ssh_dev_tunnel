"""
terminal.py — Abre um shell SSH interativo direto no servidor remoto.

Substitui o antigo `cmd_tunnel`: reaproveita o mesmo registro de servidores,
senhas e túnel já usados pelos recursos IDE/IA. Ao sair do shell (exit ou
Ctrl+D), o túnel é encerrado automaticamente pelo chamador.
"""
import subprocess
from src.ui import C, DIV


def open_shell(server: dict, local_pem: str, tunnel_port: int,
                breadcrumb: str, draw_header_fn) -> None:
    draw_header_fn(breadcrumb, server)
    print(f"\n  {C.SUCCESS}{C.BOLD}● TERMINAL{C.RESET}  {C.DIM}localhost:{tunnel_port}{C.RESET}\n")
    print(DIV())
    print(f"\n  {C.DIM}Digite 'exit' ou Ctrl+D para sair e encerrar o túnel.{C.RESET}\n")
    print(DIV())
    print()

    cmd = [
        "ssh", "-p", str(tunnel_port),
        "-o", "HostKeyAlgorithms=+ssh-rsa", "-o", "PubkeyAcceptedKeyTypes=+ssh-rsa",
        "-o", "StrictHostKeyChecking=no",
        "-i", local_pem,
        f"{server['user']}@127.0.0.1",
    ]
    subprocess.run(cmd)
