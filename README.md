# 🚀 SSH DEV TUNNEL (Precifica)

Utilitário de linha de comando para automação de túneis SSH reversos. Acesse servidores internos através de Jump Hosts de forma segura, com integração nativa para Cursor e VS Code.

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

---

## 🔄 Fluxo de Trabalho

**1. Menu Interativo:** Selecione seu Jump Host e o Servidor de Destino (IP Interno).

**2. Senha Única:** Insira a senha uma vez; ela será usada para sincronizar a chave `.pem` e abrir o túnel.

**3. Abrir no Editor:** O script gerará o comando de abertura do Workspace. Copie e cole no terminal:

```bash
cursor "/Users/seu-user/caminho/projeto.code-workspace"
```

**4. Conectar SSH FS:** No editor: `Ctrl+Shift+P` → `SSH FS: Add as Workspace folder` → Selecione o alias criado.

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
