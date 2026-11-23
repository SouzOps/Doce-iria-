# app.py — Servidor Flask da Calculateria: páginas, login, cadastro e API.
# Rodar no computador:  python app.py   →  http://localhost:5000
# No ar (Render, PythonAnywhere etc.):  gunicorn app:app  (veja DEPLOY.md)

import os
import re
import secrets
import time
from datetime import timedelta

from flask import Flask, jsonify, redirect, request, send_from_directory, session
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

import database as db
from logica_calculos import (
    calcular_lucro_unidade,
    calcular_percentual_lucro,
    calcular_preco_venda_markup,
    calcular_vendas_totais,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'web'), static_url_path='')

# Quando o arquivo é rodado com "python app.py" estamos testando no computador (http).
# Quando é importado por gunicorn / PythonAnywhere, estamos no ar (https, atrás de proxy).
EM_PRODUCAO = __name__ != '__main__'

db.iniciar()


# ─── Configuração de sessão ──────────────────────────────────────────────────

def _chave_secreta():
    """Usa a variável SECRET_KEY, se existir; senão cria uma e guarda em data/secret.key.
    (A chave precisa ser sempre a mesma, senão o login "some" a cada reinício.)"""
    chave = os.environ.get('SECRET_KEY')
    if chave:
        return chave
    caminho = os.path.join(os.path.dirname(db.DB_PATH), 'secret.key')
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    try:
        with open(caminho, 'x') as f:           # 'x' = só cria se ainda não existir
            f.write(secrets.token_hex(32))
    except FileExistsError:
        pass
    with open(caminho) as f:
        return f.read().strip()


app.secret_key = _chave_secreta()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=EM_PRODUCAO,
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),   # fica logado por 7 dias
)
if EM_PRODUCAO:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

PAGINAS_PROTEGIDAS = {'/calculadora', '/pages/main.html', '/pages/calculadora.html'}
API_PUBLICAS = {'/api/login', '/api/cadastro', '/api/demo', '/api/logout', '/api/me'}

DEMO_EMAIL = 'demo@calculateria.com'
DEMO_ATIVA = os.environ.get('CALCULATERIA_DEMO', '1') != '0'


@app.before_request
def exigir_login():
    if 'usuario_id' in session:
        return None
    caminho = request.path
    if caminho.startswith('/api/') and caminho not in API_PUBLICAS:
        return jsonify({'sucesso': False, 'erro': 'Faça login para continuar.'}), 401
    if caminho in PAGINAS_PROTEGIDAS:
        return redirect('/pages/login.html')
    return None


@app.after_request
def sem_cache(resp):
    if request.path in PAGINAS_PROTEGIDAS or request.path.startswith('/api/'):
        resp.headers['Cache-Control'] = 'no-store'
    return resp


def _uid():
    return session['usuario_id']


# ─── Login, cadastro e demonstração ──────────────────────────────────────────

MAX_TENTATIVAS = 8
BLOQUEIO_SEGUNDOS = 60
_tentativas = {}   # ip -> {'erros': n, 'ate': timestamp}
EMAIL_OK = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
SENHA_MIN = 6


def _bloqueado():
    info = _tentativas.get(request.remote_addr)
    if info and info['ate'] > time.time():
        return int(info['ate'] - time.time()) + 1
    return 0


def _registrar_erro():
    info = _tentativas.setdefault(request.remote_addr, {'erros': 0, 'ate': 0})
    info['erros'] += 1
    if info['erros'] >= MAX_TENTATIVAS:
        info.update(erros=0, ate=time.time() + BLOQUEIO_SEGUNDOS)


def _entrar(usuario):
    session.clear()
    session.permanent = True
    session['usuario_id'] = usuario['id']
    session['email'] = usuario['email']


def _credenciais():
    dados = request.get_json(silent=True) or {}
    return str(dados.get('email') or '').strip().lower(), str(dados.get('senha') or '')


@app.route('/api/login', methods=['POST'])
def api_login():
    espera = _bloqueado()
    if espera:
        return jsonify({'sucesso': False, 'erro': f'Muitas tentativas. Aguarde {espera}s.'}), 429
    email, senha = _credenciais()
    usuario = db.buscar_usuario(email)
    if not usuario or not check_password_hash(usuario['senha_hash'], senha):
        _registrar_erro()
        return jsonify({'sucesso': False, 'erro': 'E-mail ou senha incorretos.'}), 401
    _tentativas.pop(request.remote_addr, None)
    _entrar(usuario)
    return jsonify({'sucesso': True, 'email': usuario['email']})


@app.route('/api/cadastro', methods=['POST'])
def api_cadastro():
    espera = _bloqueado()
    if espera:
        return jsonify({'sucesso': False, 'erro': f'Muitas tentativas. Aguarde {espera}s.'}), 429
    email, senha = _credenciais()
    if not EMAIL_OK.match(email) or len(email) > 120:
        return jsonify({'sucesso': False, 'erro': 'Digite um e-mail válido.'}), 422
    if len(senha) < SENHA_MIN:
        return jsonify({'sucesso': False,
                        'erro': f'A senha precisa ter pelo menos {SENHA_MIN} caracteres.'}), 422
    novo_id = db.criar_usuario(email, generate_password_hash(senha))
    if novo_id is None:
        _registrar_erro()
        return jsonify({'sucesso': False, 'erro': 'Este e-mail já está cadastrado. Tente entrar.'}), 409
    _entrar({'id': novo_id, 'email': email})
    return jsonify({'sucesso': True, 'email': email})


@app.route('/api/demo', methods=['POST'])
def api_demo():
    """Entra numa conta de demonstração, sem senha (útil para a banca testar rápido).
    Para desligar: defina a variável de ambiente CALCULATERIA_DEMO=0."""
    if not DEMO_ATIVA:
        return jsonify({'sucesso': False, 'erro': 'Conta de demonstração desativada.'}), 404
    usuario = db.buscar_usuario(DEMO_EMAIL)
    if not usuario:
        # senha aleatória: ninguém consegue entrar na conta demo pelo formulário
        db.criar_usuario(DEMO_EMAIL, generate_password_hash(secrets.token_hex(16)))
        usuario = db.buscar_usuario(DEMO_EMAIL)
    _entrar(usuario)
    return jsonify({'sucesso': True, 'email': usuario['email']})


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'sucesso': True})


@app.route('/api/me')
def api_me():
    if 'usuario_id' in session:
        return jsonify({'logado': True, 'email': session.get('email')})
    return jsonify({'logado': False})


# ─── Páginas ─────────────────────────────────────────────────────────────────

@app.route('/')
def pagina_inicial():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/calculadora')
def pagina_calculadora():
    return send_from_directory(app.static_folder, 'pages/calculadora.html')


# ─── Calculadora de preços ───────────────────────────────────────────────────

def _numeros(*campos):
    dados = request.get_json(silent=True) or {}
    try:
        return [float(dados[c]) for c in campos]
    except (KeyError, TypeError, ValueError):
        raise KeyError(', '.join(campos))


def _calculo(campos, funcao):
    """Lê os campos do JSON, roda a função de logica_calculos e devolve a resposta."""
    try:
        resultado = funcao(*_numeros(*campos))
    except KeyError as e:
        return jsonify({'sucesso': False, 'erro': f'Campos obrigatórios: {e.args[0]}'}), 400
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 422
    return jsonify({'sucesso': True, **resultado})


@app.route('/api/lucro-unidade', methods=['POST'])
def api_lucro_unidade():
    return _calculo(('custo', 'preco_venda'),
                    lambda c, p: {'lucro': round(calcular_lucro_unidade(c, p), 2)})


@app.route('/api/percentual-lucro', methods=['POST'])
def api_percentual_lucro():
    return _calculo(('custo', 'preco_venda'),
                    lambda c, p: {'percentual': round(calcular_percentual_lucro(c, p), 2)})


@app.route('/api/vendas-totais', methods=['POST'])
def api_vendas_totais():
    return _calculo(('custo', 'preco_venda', 'quantidade'),
                    lambda c, p, q: {k: round(v, 2) for k, v in calcular_vendas_totais(c, p, q).items()})


@app.route('/api/markup', methods=['POST'])
def api_markup():
    return _calculo(('custo', 'markup_percent'),
                    lambda c, m: {'preco_venda': round(calcular_preco_venda_markup(c, m), 2)})


# ─── Vendas e gastos (painel) ────────────────────────────────────────────────

def _registrar(tipo):
    dados = request.get_json(silent=True) or {}
    try:
        valor = float(dados['valor'])
    except (KeyError, TypeError, ValueError):
        return jsonify({'sucesso': False, 'erro': 'Campo obrigatório: valor'}), 400
    if not 0 < valor < 1e9:
        return jsonify({'sucesso': False, 'erro': 'Digite um valor maior que zero.'}), 422
    equipe_id = None
    if dados.get('escopo') == 'equipe':            # registro compartilhado com a equipe
        equipe = db.equipe_do_usuario(_uid())
        if not equipe:
            return jsonify({'sucesso': False, 'erro': 'Você não está em uma equipe.'}), 409
        equipe_id = equipe['id']
    db.adicionar_transacao(_uid(), tipo, round(valor, 2), equipe_id)
    return jsonify({'sucesso': True})


@app.route('/api/venda', methods=['POST'])
def api_venda():
    return _registrar('venda')


@app.route('/api/gasto', methods=['POST'])
def api_gasto():
    return _registrar('gasto')


@app.route('/api/resumo')
def api_resumo():
    vendas = db.total_por_tipo(_uid(), 'venda')
    gastos = db.total_por_tipo(_uid(), 'gasto')
    historico = [{**t, 'tipo': t['tipo'].capitalize()} for t in db.listar_transacoes(_uid())]
    return jsonify({'total_vendas': vendas, 'total_gastos': gastos,
                    'lucro': round(vendas - gastos, 2), 'historico': historico})


@app.route('/api/transacao/<int:id_>', methods=['DELETE'])
def api_remover(id_):
    if db.remover_transacao(_uid(), id_):
        return jsonify({'sucesso': True})
    return jsonify({'sucesso': False, 'erro': 'Registro não encontrado.'}), 404


@app.route('/api/resetar', methods=['POST'])
def api_resetar():
    db.apagar_transacoes(_uid())
    return jsonify({'sucesso': True})


# ─── Equipe ──────────────────────────────────────────────────────────────────

MAX_CONVITES_PENDENTES = 20


def _erro(msg, codigo):
    return jsonify({'sucesso': False, 'erro': msg}), codigo


@app.route('/api/equipe')
def api_equipe():
    email = session['email']
    recebidos = [{'id': c['id'], 'equipe': c['equipe_nome'], 'de': c['de_email']}
                 for c in db.convites_para(email)]
    equipe = db.equipe_do_usuario(_uid())
    if not equipe:
        return jsonify({'equipe': None, 'meu_email': email, 'convites_recebidos': recebidos})

    pessoas = db.resumo_equipe(equipe['id'])
    for p in pessoas:
        p['lucro'] = round(p['vendas'] - p['gastos'], 2)
        p['eu'] = p['id'] == _uid()
    vendas = round(sum(p['vendas'] for p in pessoas), 2)
    gastos = round(sum(p['gastos'] for p in pessoas), 2)
    historico = [{'id': t['id'], 'tipo': t['tipo'].capitalize(), 'valor': t['valor'],
                  'criado_em': t['criado_em'], 'autor': t['autor'],
                  'meu': t['usuario_id'] == _uid()}
                 for t in db.listar_transacoes_equipe(equipe['id'])]
    return jsonify({
        'equipe': equipe, 'meu_email': email,
        'totais': {'vendas': vendas, 'gastos': gastos, 'lucro': round(vendas - gastos, 2)},
        'membros': [{k: p[k] for k in ('email', 'vendas', 'gastos', 'lucro', 'ativo', 'eu')} for p in pessoas],
        'historico': historico,
        'convites_enviados': [{'id': c['id'], 'email': c['para_email']}
                              for c in db.convites_da_equipe(equipe['id'])],
        'convites_recebidos': recebidos,
    })


@app.route('/api/equipe', methods=['POST'])
def api_criar_equipe():
    if db.equipe_do_usuario(_uid()):
        return _erro('Você já faz parte de uma equipe.', 409)
    nome = str((request.get_json(silent=True) or {}).get('nome') or '').strip()
    if not 1 <= len(nome) <= 40:
        return _erro('Dê um nome de até 40 caracteres para a equipe.', 422)
    db.criar_equipe(_uid(), nome)
    return jsonify({'sucesso': True})


@app.route('/api/equipe/convidar', methods=['POST'])
def api_convidar():
    equipe = db.equipe_do_usuario(_uid())
    if not equipe:
        return _erro('Você não está em uma equipe.', 409)
    email = str((request.get_json(silent=True) or {}).get('email') or '').strip().lower()
    if not EMAIL_OK.match(email) or len(email) > 120:
        return _erro('Digite um e-mail válido.', 422)
    if email == session['email']:
        return _erro('Você já faz parte da equipe.', 422)
    alvo = db.buscar_usuario(email)
    if alvo and alvo.get('equipe_id') == equipe['id']:
        return _erro('Essa pessoa já está na equipe.', 409)
    if len(db.convites_da_equipe(equipe['id'])) >= MAX_CONVITES_PENDENTES:
        return _erro('Há convites demais pendentes. Cancele alguns antes de convidar.', 422)
    if db.criar_convite(equipe['id'], _uid(), email) is None:
        return _erro('Já existe um convite pendente para esse e-mail.', 409)
    return jsonify({'sucesso': True})


@app.route('/api/equipe/convites/<int:id_>/aceitar', methods=['POST'])
def api_aceitar_convite(id_):
    convite = db.buscar_convite(id_)
    if not convite or convite['para_email'] != session['email']:
        return _erro('Convite não encontrado.', 404)
    if db.equipe_do_usuario(_uid()):
        return _erro('Você já faz parte de uma equipe. Saia dela antes de aceitar outro convite.', 409)
    db.aceitar_convite(_uid(), convite)
    return jsonify({'sucesso': True})


@app.route('/api/equipe/convites/<int:id_>', methods=['DELETE'])
def api_remover_convite(id_):
    """Serve para recusar (quem recebeu) e para cancelar (quem está na equipe que convidou)."""
    convite = db.buscar_convite(id_)
    equipe = db.equipe_do_usuario(_uid())
    permitido = convite and (convite['para_email'] == session['email']
                             or (equipe and convite['equipe_id'] == equipe['id']))
    if not permitido:
        return _erro('Convite não encontrado.', 404)
    db.remover_convite(id_)
    return jsonify({'sucesso': True})


@app.route('/api/equipe/sair', methods=['POST'])
def api_sair_equipe():
    equipe = db.equipe_do_usuario(_uid())
    if not equipe:
        return _erro('Você não está em uma equipe.', 409)
    db.sair_da_equipe(_uid(), equipe['id'])
    return jsonify({'sucesso': True})


if __name__ == '__main__':
    print('Servidor: http://localhost:5000')
    app.run(debug=True, port=int(os.environ.get('PORT', 5000)))
