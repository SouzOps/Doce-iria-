# Calculateria — TCC (Flask + SQLite)

Controle de vendas e gastos + calculadora de preços para doceiras.

- **Aba Pessoal:** vendas e gastos só da sua conta.
- **Aba Equipe:** crie uma equipe, convide pessoas pelo e-mail de cadastro delas (elas precisam aceitar),
  registrem vendas e gastos em conjunto e veja o total da equipe, o resumo por pessoa e o histórico
  com o nome de quem registrou cada item. Cada pessoa só apaga o que ela mesma registrou.
  Cada usuário pode estar em uma equipe por vez.

## Rodar no computador
Precisa do Python 3.8 ou mais novo.

    pip install -r requirements.txt
    python app.py

Abra http://localhost:5000 → **Entrar** → aba **Criar conta** (ou o botão de demonstração).

## Como o projeto está organizado
    app.py              servidor Flask: páginas, login, cadastro e API
    database.py         banco SQLite (usuarios, equipes, convites, transacoes), criado e atualizado sozinho
    logica_calculos.py  regras de cálculo (lucro, %, totais, markup)
    web/                páginas (HTML), estilos (CSS), scripts (JS: calculadora.js e equipe.js) e imagens
    Procfile            comando de inicialização para Render/Railway
    DEPLOY.md           passo a passo para colocar no ar

O banco fica em `data/calculateria.db` (não vai para o GitHub). Para apagar tudo e recomeçar,
basta apagar a pasta `data/`.

## Variáveis de ambiente (todas opcionais)
- `SECRET_KEY` — chave que assina o login. Se não existir, é criada em `data/secret.key`.
- `CALCULATERIA_DEMO=0` — desliga o botão "Entrar sem cadastro (demonstração)".
- `CALCULATERIA_DB` — caminho do arquivo do banco, se quiser guardá-lo em outro lugar.
