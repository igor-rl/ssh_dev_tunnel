# 🚀 SSH DEV TUNNEL (Precifica)

Utilitário de linha de comando para automação de túneis SSH reversos. Acesse servidores internos através de Jump Hosts de forma segura, com integração nativa para Cursor e VS Code.

---

## ⚡ Instalação Única (Recomendado)

Configure a ferramenta globalmente no seu Mac ou Windows com apenas um comando. O instalador detectará automaticamente se você possui Docker ou prefere a Instalação Local:

```bash
curl -fsSL https://raw.githubusercontent.com/igor-rl/ssh_dev_tunnel/main/install.sh | bash
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

## 📋 Métodos de Instalação

O instalador inteligente oferecerá as opções baseadas no seu ambiente:

- **Opção 1 — Via Docker (Melhor Experiência):** Requer apenas o Docker Desktop rodando. É a opção mais limpa, pois isola todas as dependências (como `sshpass`) dentro de um container.
- **Opção 2 — Via Python (Local):** Requer Python 3.10+ e `sshpass` instalado manualmente no seu sistema operacional.

---

## 📁 Persistência de Dados

Seus servidores cadastrados e chaves PEM são mantidos localmente para persistirem entre atualizações:

| Método de Uso | Localização dos Dados (Host) |
|---------------|------------------------------|
| Docker        | `~/.dev_tunnel_config/`      |
| Local         | `~/.dev_tunnel/.data/`       |

---

## 🗑️ Desinstalação

Caso precise remover os atalhos e configurações do seu sistema:

```bash
curl -fsSL https://raw.githubusercontent.com/igor-rl/ssh_dev_tunnel/main/uninstall.sh | bash
```

---

## 🛠️ Solução de Problemas

- **Porta 2222 ocupada:** O túnel utiliza a porta `2222`. Certifique-se de que não há outra instância rodando (`docker ps`).
- **Comando 'tunnel' não encontrado:** Verifique se você reiniciou o terminal após a instalação para carregar o novo `alias`.

<br/>

---

<div align="center">

<p align="center">
<img src="https://img.shields.io/static/v1?label=IRL&message=FULL%20STACK%20DEVOPS&color=2d2d2d&style=for-the-badge&logo=GitHub">
</p>

[![GitHub](https://img.shields.io/badge/GitHub-Igor_Lage-blue?style=social&logo=github)](https://github.com/igor-rl) 
![Static Badge](https://img.shields.io/badge/24--03--2026-black)

</div>
