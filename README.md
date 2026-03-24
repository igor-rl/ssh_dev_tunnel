🚀 SSH DEV TUNNEL (Precifica)
Utilitário de linha de comando para automação de túneis SSH reversos. Acesse servidores internos da Precifica através de Jump Hosts de forma transparente, com integração nativa para Cursor e VS Code.

⚡ Instalação Única (Recomendado)
Configure a ferramenta globalmente no seu Mac ou Windows com apenas um comando. O instalador detectará automaticamente se você possui Docker ou prefere a Instalação Local:

Bash
curl -fsSL https://raw.githubusercontent.com/igor-rl/ssh_dev_tunnel/main/install.sh | bash
Após a instalação: Reinicie o terminal ou rode source ~/.zshrc (Mac) / source ~/.bashrc (Windows).

🚀 Como Usar
Agora que o comando está global, você não precisa mais baixar scripts em cada pasta. Basta digitar:

Bash
tunnel
🔄 Fluxo de Trabalho

Menu Interativo: Selecione seu Jump Host e o Servidor de Destino (suporte a user@ip).

Senha Única: Insira a senha uma vez para sincronizar a PEM e abrir o túnel.

Abrir no Editor: O script gerará o comando de abertura. Copie e cole no terminal:

Bash
cursor "/Users/seu-user/.../projeto.code-workspace"
Conectar SSH FS: No editor: Ctrl+Shift+P → SSH FS: Add as Workspace folder → Selecione o servidor.

📋 Pré-requisitos
O instalador oferecerá as opções baseadas no que você tem disponível:

Via Docker (Melhor Experiência): Requer apenas o Docker Desktop rodando. Não polui seu sistema com dependências.

Via Python (Local): Requer Python 3.10+ e sshpass instalado manualmente.

📁 Onde ficam meus dados?
Para garantir que seus servidores cadastrados não sumam em atualizações:

Método	Localização dos Dados (Host)
Docker	~/.dev_tunnel_config/
Local	~/.dev_tunnel/.data/
🛠️ Solução de Problemas
Porta 2222 ocupada: O túnel usa a porta 2222. Verifique se não há outra instância rodando com docker ps.

Comando 'tunnel' não encontrado: Certifique-se de ter reiniciado o terminal após rodar o install.sh.

<div align="center">

<p align="center">
<img src="https://img.shields.io/static/v1?label=IRL&message=FULL%20STACK%20DEVOPS&color=2d2d2d&style=for-the-badge&logo=GitHub">
</p>

</div>