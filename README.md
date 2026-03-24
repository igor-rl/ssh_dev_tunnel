# 🚀 SSH DEV TUNNEL

[![Version](https://img.shields.io/badge/version-1.0-blue.svg)](https://github.com/igor-rl/ssh_dev_tunnel)
[![Python](https://img.shields.io/badge/python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Company](https://img.shields.io/badge/company-Precifica-purple.svg)](https://www.precifica.com.br)

Utilitário de linha de comando para automação de túneis SSH reversos e gerenciamento de workspaces de desenvolvimento. Ideal para desenvolvedores que precisam acessar servidores internos da **Precifica** através de Jump Hosts de forma ágil.

---

## 📥 Instalação (Via Curl)

Para instalar ou atualizar a ferramenta globalmente no seu sistema, execute:

```bash
curl -sSL https://raw.githubusercontent.com/igor-rl/ssh_dev_tunnel/main/install.sh | bash
```

---

## 📋 Pré-requisitos

Antes de instalar, certifique-se de ter as dependências do sistema:

- **Python 3.10+** instalado e configurado no PATH
- **sshpass** necessário para automação de senhas:
  - macOS: `brew install sshpass`
  - Linux (Ubuntu/Debian): `sudo apt-get install sshpass`

---

## 🚀 Como Utilizar

Após a instalação, o comando `tunnel` estará disponível globalmente.

**1. Inicie a ferramenta:**

```bash
tunnel
```

**2. Siga o menu interativo:**
- Selecione o Jump Host de origem
- Escolha o Servidor de Destino (IP Interno)
- O túnel será estabelecido na porta `2222`

**3. Abra o Workspace:**

O script indicará o caminho da pasta:

```bash
cd ~/.dev_tunnel/workspaces/nome-do-servidor
```

Abra com seu editor:

```bash
code .
# ou
cursor .
```

**4. Conecte via SSH FS:**

No editor: `Ctrl+Shift+P` → `SSH FS: Connect` → Selecione o alias do servidor

---

## 📁 Estrutura de Arquivos Local

A ferramenta centraliza tudo na sua pasta de usuário para não poluir o sistema:

| Caminho | Descrição |
|--------|-----------|
| `~/.dev_tunnel/.data/servers.json` | Configurações dos servidores |
| `~/.dev_tunnel/.data/.ssh/` | Chaves PEM |
| `~/.dev_tunnel/workspaces/` | Workspaces gerados |

---

## 🛠️ Manutenção e Logs

Se encontrar problemas com a chave PEM ou conexões persistentes:

- **Resetar uma chave:** remova o arquivo em `~/.dev_tunnel/.data/.ssh/` e execute o `tunnel` novamente
- **Editar servidores manualmente:** altere o arquivo `~/.dev_tunnel/.data/servers.json`

---

## 👤 Autor

**Igor Lage** — [igor-rl](https://github.com/igor-rl)  
Organização: Precifica

---

*© 2026 Precifica — Uso Interno.*