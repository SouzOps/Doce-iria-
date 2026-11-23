# Como colocar a Calculateria no ar

## Por que PythonAnywhere?
O projeto usa **Python (Flask) + um banco SQLite em arquivo**. Isso exige uma hospedagem que:
1. rode Python (GitHub Pages, Netlify e Vercel **não** servem: só hospedam páginas estáticas); e
2. **guarde arquivos** entre reinícios (o SQLite é um arquivo).

O PythonAnywhere (plano grátis "Beginner") atende aos dois e não pede cartão de crédito.
O Render grátis roda Flask, mas apaga o disco quando o site reinicia ou "dorme" — ver "Plano B" no fim.

Endereço final: `https://SEUUSUARIO.pythonanywhere.com`

---

## Passo a passo (PythonAnywhere)

### 1. Criar a conta
1. Acesse https://www.pythonanywhere.com → **Pricing & signup** → **Create a Beginner account**.
2. Escolha o nome de usuário com cuidado: ele vira o endereço do site.

### 2. Enviar o projeto
1. No seu computador, use o arquivo **calculateria.zip** (com `app.py` solto dentro, sem pasta extra).
2. No PythonAnywhere: aba **Files** → **Upload a file** → envie o zip para `/home/SEUUSUARIO/`.
3. Aba **Consoles** → **Bash** e rode (troque nada, só copie):

       cd ~
       unzip -o calculateria.zip -d calculateria
       ls calculateria

   Deve listar `app.py`, `database.py`, `web`, etc.

4. Teste se o Flask já está instalado (normalmente está):

       python3 -c "import flask; print(flask.__version__)"

   Se aparecer `ModuleNotFoundError`, rode: `pip install --user flask`

### 3. Criar o site
1. Aba **Web** → **Add a new web app** → **Next**.
2. Escolha **Manual configuration** → escolha o **Python mais novo da lista** (3.10 ou superior) → **Next**.
3. Na página do site, em **Code**, clique no link do **WSGI configuration file**
   (algo como `/var/www/seuusuario_pythonanywhere_com_wsgi.py`).
4. **Apague tudo** e cole isto (troque `SEUUSUARIO` pelo seu usuário, respeitando maiúsculas/minúsculas):

       import sys
       caminho = '/home/SEUUSUARIO/calculateria'
       if caminho not in sys.path:
           sys.path.insert(0, caminho)
       from app import app as application

5. Clique em **Save** (canto superior direito).
6. Volte à aba **Web**, role até **Security** e ative **Force HTTPS** (importante para o login funcionar).
7. Clique no botão verde **Reload SEUUSUARIO.pythonanywhere.com**.

### 4. Testar
1. Abra `https://SEUUSUARIO.pythonanywhere.com`.
2. Clique em **Entrar na minha conta** → aba **Criar conta** → cadastre e-mail e senha (mín. 6 caracteres).
3. Registre uma venda e um gasto. Saia e entre de novo para confirmar que os dados ficaram salvos.

### 5. Antes da banca
- **Renovação:** no plano grátis o site é desativado se você não confirmar que ainda quer mantê-lo.
  Na aba **Web**, clique no botão **Run until 3 months from today** (ou equivalente). Faça isso
  uma semana antes da apresentação e coloque um lembrete no calendário.
- **Cadastre-se antes** e deixe uma conta pronta, ou use o botão **Entrar sem cadastro (demonstração)**
  da tela de login (a conta demo é compartilhada: qualquer pessoa que clicar vê os mesmos dados).
- Para **desligar** o botão de demonstração depois da banca, no WSGI file adicione, antes do `from app import`:

       import os
       os.environ['CALCULATERIA_DEMO'] = '0'

### 6. Atualizar o site depois
- Envie os arquivos alterados pela aba **Files** (na pasta `calculateria`) ou suba um novo zip e rode
  o `unzip -o` de novo (os dados em `data/` **não** são apagados e o banco se atualiza sozinho,
  inclusive para ganhar as tabelas da Equipe). Depois clique em **Reload**.

---

## Se algo der errado
Primeiro olhe o **Error log** (link na aba **Web**, seção *Log files*): a última linha diz o erro.

| Sintoma | Causa provável | Solução |
|---|---|---|
| Aparece "Hello from Flask!" ou página padrão | WSGI file não foi trocado/salvo | Refaça o passo 3.4 e 3.5, depois **Reload** |
| `ModuleNotFoundError: No module named 'app'` | Caminho errado no WSGI | Confira `/home/SEUUSUARIO/calculateria` (usuário igual ao do site) e que `app.py` está dentro dessa pasta |
| `ModuleNotFoundError: flask` | Flask não instalado | `pip install --user flask` e **Reload** |
| Entra, mas volta para a tela de login | Acessou por `http://` | Ative **Force HTTPS** e use `https://` |
| "Internal Server Error" | Erro no código ou permissão | Leia o Error log; se falar de `data/`, rode `mkdir -p ~/calculateria/data` no Bash |
| Esqueci a senha | Não há recuperação | Crie outra conta, ou apague `~/calculateria/data/calculateria.db` no Bash para zerar tudo |

---

## Plano B: Render (grátis, mas **perde os dados**)
Use só se o PythonAnywhere não funcionar. No plano grátis do Render o disco é apagado sempre que o
serviço reinicia, faz novo deploy ou fica 15 min sem acesso: **contas e vendas cadastradas somem**
(o botão de demonstração continua funcionando, porque recria a conta demo). A primeira visita depois
de ficar parado leva cerca de 1 minuto.

1. Crie um repositório no GitHub e envie **o conteúdo do zip na raiz** do repositório
   (`app.py`, `requirements.txt` e `Procfile` precisam ficar na primeira tela do repositório, não numa subpasta).
2. Em https://render.com → **New** → **Web Service** → conecte o repositório.
3. Configure:
   - **Language/Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --workers 1 --threads 4`
   - **Instance Type:** Free
4. Em **Environment**, adicione `SECRET_KEY` com um texto longo e aleatório (ex.: 40 letras e números quaisquer).
5. **Create Web Service**, espere o deploy terminar e abra o link `https://nome.onrender.com`.
