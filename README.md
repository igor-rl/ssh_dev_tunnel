# 🚀 SSH DEV TUNNEL (Precifica)

Utilitário de linha de comando para automação de túneis SSH reversos. Acesse servidores internos através de Jump Hosts de forma segura, com três formas de trabalhar sobre a mesma conexão: **IDE** (Cursor/VS Code), **IA** (Claude Code/Gemini, somente leitura) e **Terminal** (shell SSH direto).

---

## 🏁 Get Start

Crie uma pasta dedicada para seus projetos de túnel:
```bash
mkdir -p ~/projects/ssh && cd ~/projects/ssh
```

---

## ⚡ Instalação Única (Recomendado)

Configure a ferramenta globalmente no seu Mac ou Windows (WSL/Git Bash) com apenas um comando. Requer **Python 3.10+** e **sshpass** instalados:

```bash
curl -fsSL https://raw.githubusercontent.com/igor-rl/ssh_dev_tunnel/main/install.sh -o install.sh && bash install.sh && rm install.sh
```

Após a instalação, reinicie o terminal ou rode:

```bash
source ~/.zshrc   # Mac
source ~/.bashrc  # Windows
```

---

## 🚀 Como Usar

Com a instalação concluída, o comando `tunnel` estará disponível globalmente em qualquer pasta de projeto.

```bash
tunnel
```

Sem flags, o primeiro menu pergunta **qual recurso usar**: IDE, IA ou Terminal. Depois disso, escolha uma conexão salva ou configure uma nova (Jump Host + Servidor) — o fluxo de autenticação, chave `.pem` e túnel é o mesmo para os três.

Você também pode pular direto pro recurso desejado via flag:

```bash
tunnel --cursor            # abre no Cursor
tunnel --vscode            # abre no VS Code
tunnel --ia                # abre IA (detecta/pergunta Claude Code ou Gemini)
tunnel --ia claude         # abre direto no Claude Code
tunnel --ia gemini         # abre direto no Gemini CLI
tunnel --terminal          # abre um shell SSH direto no servidor
tunnel --port 2223         # porta local customizada (funciona com qualquer recurso acima)
```

---

## 🔄 Fluxo de Trabalho

**1. Recurso:** Escolha IDE, IA ou Terminal (ou pule direto com a flag correspondente).

**2. Conexão:** Selecione uma conexão salva, ou configure Jump Host + Servidor de Destino (IP Interno) na primeira vez.

**3. Senha Única:** Insira a senha uma vez; ela é salva com segurança (Keychain do sistema, ou arquivo criptografado como fallback) e reaproveitada nas próximas conexões — sincroniza a chave `.pem` e abre o túnel automaticamente.

**4a. Modo IDE:** o Cursor ou VS Code abre sozinho, já conectado ao servidor via SSH FS. Se os dois estiverem instalados e nenhuma flag (`--cursor`/`--vscode`) for passada, o app pergunta qual usar.

**4b. Modo IA:** abre o Claude Code ou Gemini CLI numa sessão configurada para leitura remota (via SSH, sem mount) — a IA investiga, explica bugs e sugere código; você aplica as mudanças manualmente no editor. Também dá pra rodar `tunnel-explore` em outro terminal para reaproveitar uma conexão que já esteja aberta em modo IDE.

**4c. Modo Terminal:** abre um shell SSH interativo direto no servidor, pra você rodar comandos você mesmo. Ao sair (`exit` ou Ctrl+D), o túnel fecha automaticamente.

---

## 📋 Pré-requisitos

- **Python 3.10+**
- **sshpass** (`brew install hudochenkov/sshpass/sshpass` no macOS, `apt install sshpass` no Linux, WSL no Windows)
- Recomendado: **pipx** (`brew install pipx` / `apt install pipx`) — o instalador usa automaticamente se disponível, para manter as dependências isoladas.

---

## 📁 Persistência de Dados

Seus servidores cadastrados, chaves PEM e senhas salvas ficam em:

```
~/.dev_tunnel/.data/
```

Persistem entre atualizações e reinstalações.

---

## 🗑️ Desinstalação

Caso precise remover os atalhos e configurações do seu sistema:

```bash
curl -fsSL https://raw.githubusercontent.com/igor-rl/ssh_dev_tunnel/main/uninstall.sh -o uninstall.sh && bash uninstall.sh && rm uninstall.sh
```

---

## 🛠️ Solução de Problemas

- **Porta 2222 ocupada:** o `tunnel` detecta automaticamente e usa a próxima porta livre.
- **Comando 'tunnel' não encontrado:** reinicie o terminal após a instalação; se persistir, confirme que o diretório de binários do `pipx`/`pip --user` está no seu `PATH`.

<br/>

---

<div align="center">

<p align="center">
<img src="https://img.shields.io/static/v1?label=IRL&message=FULL%20STACK%20DEVOPS&color=2d2d2d&style=for-the-badge&logo=GitHub">
</p>

[![GitHub](https://img.shields.io/badge/GitHub-Igor_Lage-blue?style=social&logo=github)](https://github.com/igor-rl) 
![Static Badge](https://img.shields.io/badge/24--03--2026-black)

</div>
