# Calculateria — TCC (Flask + SQLite)

## 1) Instalar (só uma vez)
Instale o Python 3.8+ (python.org — marque "Add Python to PATH"). Na pasta `tcc`:

    pip install -r requirements.txt

## 2) Cadastrar um usuário (por fora do site)
    cd backend
    python adicionar_usuario.py adicionar

Ele pede o e-mail e a senha (mín. 8 caracteres). O e-mail precisa ser real:
o programa confere o formato e se o domínio existe e recebe e-mails (precisa de internet).

Outros comandos:

    python adicionar_usuario.py listar
    python adicionar_usuario.py remover --email fulano@gmail.com

## 3) Rodar o site
    cd backend
    python main.py

Abra http://localhost:5000 → "Entrar" → e-mail e senha cadastrados.

## Estrutura
backend/  main.py (servidor + login) · database.py (SQLite) · schema.sql (tabelas)
          adicionar_usuario.py · logica_calculos.py
web/      index.html · pages/ · css/ · js/ · img/
