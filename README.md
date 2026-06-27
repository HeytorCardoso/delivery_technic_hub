# Enterprise Hub

Plataforma premium para gerenciamento de entregas e links para empresas clientes.

## Tecnologias
- **Backend:** Python, Flask, SQLAlchemy
- **Banco de Dados:** SQLite
- **Autenticação:** Argon2id
- **Frontend:** Tailwind CSS, Animate On Screen (AOS), FontAwesome 6

## Como Rodar
1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Execute o servidor:
   ```bash
   python app.py
   ```
3. Acesse o painel admin:
   - **Login:** admin
   - **Senha:** admin123
   *(Recomenda-se trocar a senha após o primeiro acesso)*

## Funcionalidades
- **Admin:**
  - Adicionar novas empresas com logins exclusivos.
  - Criar estrutura de pastas para cada empresa.
  - Adicionar links externos (OneDrive, SharePoint, etc) dentro das pastas.
  - Visualizar o hub exatamente como o cliente verá.
- **Empresa (Cliente):**
  - Login seguro.
  - Acesso centralizado a todos os links de projetos e documentos.
  - Interface intuitiva em estilo de navegação de arquivos.
