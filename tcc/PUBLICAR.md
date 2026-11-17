# Como colocar a Calculateria no ar (PythonAnywhere, grátis)

Site final: https://SEUUSUARIO.pythonanywhere.com

## 1. Criar a conta
1. Entre em https://www.pythonanywhere.com e clique em **Pricing & signup → Create a Beginner account** (grátis).
2. Escolha o nome de usuário com cuidado: ele vira o endereço do site.

## 2. Enviar o projeto
1. No seu computador, compacte a pasta `tcc` em um .zip (ou use o tcc.zip que recebeu).
2. No PythonAnywhere: aba **Files** → **Upload a file** → envie o zip para `/home/SEUUSUARIO/`.
3. Aba **Consoles** → **Bash** e rode:

       unzip tcc.zip
       cd tcc
       pip install --user -r requirements.txt

## 3. Cadastrar seu usuário
Ainda no console Bash:

       cd ~/tcc/backend
       python3 adicionar_usuario.py adicionar

Se der erro de DNS/rede ao validar o e-mail (a conta grátis limita a internet),
use: `python3 adicionar_usuario.py adicionar --sem-dns`

## 4. Criar o site
1. Aba **Web** → **Add a new web app** → **Next** → **Manual configuration** → escolha o mesmo Python do console (`python3 --version`).
2. Na página do site, procure **WSGI configuration file** e clique no link.
3. Apague tudo e cole (troque SEUUSUARIO):

       import os, sys
       os.environ['CALCULATERIA_HTTPS'] = '1'
       caminho = '/home/SEUUSUARIO/tcc/backend'
       if caminho not in sys.path:
           sys.path.insert(0, caminho)
       from main import app as application

4. **Save**, volte à aba **Web** e clique no botão verde **Reload**.
5. Abra https://SEUUSUARIO.pythonanywhere.com e entre com o e-mail e a senha.

## 5. Atenção (conta grátis)
- O site **expira** se você não renovar: entre no PythonAnywhere e clique no botão de
  estender na aba **Web** (o site avisa por e-mail antes). Faça isso antes da banca!
- Os dados ficam em `~/tcc/backend/data/calculateria.db` e **não** se perdem ao recarregar.
- Para atualizar o site depois de mudar arquivos: envie os novos e clique em **Reload**.
