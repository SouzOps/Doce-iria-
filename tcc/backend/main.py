# main.py — Servidor Flask / API REST do projeto
# Expõe as funções do logica_calculos.py como endpoints HTTP e
# guarda vendas, gastos e histórico de cálculos no banco SQLite (database.py).

from flask import Flask, request, jsonify, send_from_directory, session, redirect
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import timedelta
import os, sys, time, secrets

sys.path.insert(0, os.path.dirname(__file__))

from logica_calculos import (
    calcular_lucro_unidade,
    calcular_percentual_lucro,
    calcular_vendas_totais,
    calcular_preco_venda_markup,
)
import database as db

app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(__file__), '..', 'web'),
    static_url_path=''
)

# Cria o banco e as tabelas na primeira execução
db.init_db()
db.fazer_backup()   # cópia de segurança do dia

# ─── Sessão / segurança ───────────────────────────────────────────────────────
# A chave que assina o cookie de login é gerada uma vez e guardada em data/secret.key
# (assim quem já entrou continua logado se o servidor reiniciar).
def _carregar_chave_secreta():
    caminho = os.path.join(os.path.dirname(db.DB_PATH), 'secret.key')
    if not os.path.exists(caminho):
        with open(caminho, 'w') as f:
            f.write(secrets.token_hex(32))
    with open(caminho) as f:
        return f.read().strip()

app.secret_key = _carregar_chave_secreta()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,      # JavaScript não consegue ler o cookie
    SESSION_COOKIE_SAMESITE='Lax',     # protege contra requisições vindas de outros sites
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)

# Quando o site está no ar (HTTPS), o arquivo WSGI define CALCULATERIA_HTTPS=1:
# o cookie de login passa a ser enviado só por HTTPS e o IP real do visitante é lido do proxy.
if os.environ.get('CALCULATERIA_HTTPS') == '1':
    app.config['SESSION_COOKIE_SECURE'] = True
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

API_PUBLICAS = {'/api/login', '/api/logout', '/api/me'}
PAGINAS_PROTEGIDAS = {'/calculadora', '/pages/main.html', '/pages/calculadora.html'}


@app.before_request
def exigir_login():
    """Barra quem não está logado: API responde 401, páginas redirecionam ao login."""
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
    # Impede que o botão "voltar" mostre uma página protegida depois do logout
    if request.path in PAGINAS_PROTEGIDAS or request.path.startswith('/api/'):
        resp.headers['Cache-Control'] = 'no-store'
    return resp

# ─── Login / Logout ───────────────────────────────────────────────────────────

MAX_TENTATIVAS = 5        # erros seguidos permitidos
BLOQUEIO_SEGUNDOS = 60    # tempo de espera depois de errar demais
_tentativas = {}          # ip -> {'erros': n, 'bloqueado_ate': timestamp}
_HASH_FALSO = generate_password_hash('senha-falsa')  # evita revelar se o e-mail existe


@app.route('/api/login', methods=['POST'])
def api_login():
    ip = request.remote_addr
    info = _tentativas.get(ip, {'erros': 0, 'bloqueado_ate': 0})
    restante = int(info['bloqueado_ate'] - time.time())
    if restante > 0:
        return jsonify({'sucesso': False,
                        'erro': f'Muitas tentativas. Aguarde {restante}s e tente de novo.'}), 429

    data = request.get_json(silent=True) or {}
    email = str(data.get('email') or '').strip().lower()
    senha = str(data.get('senha') or '')

    usuario = db.buscar_usuario_por_email(email)
    hash_ = usuario['senha_hash'] if usuario else _HASH_FALSO
    senha_ok = check_password_hash(hash_, senha)

    if not (usuario and senha_ok):
        info['erros'] += 1
        if info['erros'] >= MAX_TENTATIVAS:
            info = {'erros': 0, 'bloqueado_ate': time.time() + BLOQUEIO_SEGUNDOS}
        _tentativas[ip] = info
        return jsonify({'sucesso': False, 'erro': 'E-mail ou senha incorretos.'}), 401

    _tentativas.pop(ip, None)
    session.clear()
    session.permanent = True
    session['usuario_id'] = usuario['id']
    session['email'] = usuario['email']
    return jsonify({'sucesso': True, 'email': usuario['email']})


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'sucesso': True})


@app.route('/api/me', methods=['GET'])
def api_me():
    if 'usuario_id' in session:
        return jsonify({'logado': True, 'email': session.get('email')})
    return jsonify({'logado': False})

# ─── Páginas ──────────────────────────────────────────────────────────────────

@app.route('/')
def pagina_principal():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/calculadora')
def pagina_calculadora():
    return send_from_directory(app.static_folder, 'pages/calculadora.html')

# ─── Calculadora (logica_calculos.py) ─────────────────────────────────────────

@app.route('/api/lucro-unidade', methods=['POST'])
def api_lucro_unidade():
    data = request.get_json(silent=True) or {}
    try:
        custo = float(data['custo'])
        pv = float(data['preco_venda'])
        lucro = calcular_lucro_unidade(custo, pv)
        db.registrar_calculo('lucro_unidade', round(lucro, 2), custo, preco_venda=pv)
        return jsonify({'sucesso': True, 'lucro': round(lucro, 2)})
    except (KeyError, TypeError):
        return jsonify({'sucesso': False, 'erro': 'Campos obrigatorios: custo, preco_venda'}), 400
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 422

@app.route('/api/percentual-lucro', methods=['POST'])
def api_percentual_lucro():
    data = request.get_json(silent=True) or {}
    try:
        custo = float(data['custo'])
        pv = float(data['preco_venda'])
        pct = calcular_percentual_lucro(custo, pv)
        db.registrar_calculo('percentual_lucro', round(pct, 2), custo, preco_venda=pv)
        return jsonify({'sucesso': True, 'percentual': round(pct, 2)})
    except (KeyError, TypeError):
        return jsonify({'sucesso': False, 'erro': 'Campos obrigatorios: custo, preco_venda'}), 400
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 422

@app.route('/api/vendas-totais', methods=['POST'])
def api_vendas_totais():
    data = request.get_json(silent=True) or {}
    try:
        custo = float(data['custo'])
        pv = float(data['preco_venda'])
        qtd = float(data['quantidade'])
        res = calcular_vendas_totais(custo, pv, qtd)
        db.registrar_calculo('vendas_totais', round(res['lucro_total'], 2), custo,
                             preco_venda=pv, quantidade=qtd)
        return jsonify({'sucesso': True,
            'receita_total':    round(res['receita_total'],    2),
            'custo_total':      round(res['custo_total'],      2),
            'lucro_total':      round(res['lucro_total'],      2),
            'percentual_lucro': round(res['percentual_lucro'], 2)})
    except (KeyError, TypeError):
        return jsonify({'sucesso': False, 'erro': 'Campos obrigatorios: custo, preco_venda, quantidade'}), 400
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 422

@app.route('/api/markup', methods=['POST'])
def api_markup():
    data = request.get_json(silent=True) or {}
    try:
        custo = float(data['custo'])
        mk = float(data['markup_percent'])
        pv = calcular_preco_venda_markup(custo, mk)
        db.registrar_calculo('markup', round(pv, 2), custo, markup=mk)
        return jsonify({'sucesso': True, 'preco_venda': round(pv, 2)})
    except (KeyError, TypeError):
        return jsonify({'sucesso': False, 'erro': 'Campos obrigatorios: custo, markup_percent'}), 400
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 422

@app.route('/api/calculos', methods=['GET'])
def api_listar_calculos():
    """Histórico dos últimos cálculos feitos na calculadora."""
    return jsonify(db.listar_calculos())

# ─── Vendas / Gastos (main.html) ──────────────────────────────────────────────

def _registrar(tipo, chave_total):
    data = request.get_json(silent=True) or {}
    try:
        valor = float(data['valor'])
        if valor <= 0:
            raise ValueError('Valor deve ser maior que zero.')
        db.adicionar_transacao(tipo, valor, data.get('descricao'))
        return jsonify({'sucesso': True, chave_total: db.total_por_tipo(tipo)})
    except (KeyError, TypeError):
        return jsonify({'sucesso': False, 'erro': 'Campo obrigatorio: valor'}), 400
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 422

@app.route('/api/venda', methods=['POST'])
def api_adicionar_venda():
    return _registrar('venda', 'total_vendas')

@app.route('/api/gasto', methods=['POST'])
def api_adicionar_gasto():
    return _registrar('gasto', 'total_gastos')

@app.route('/api/resumo', methods=['GET'])
def api_resumo():
    tv = db.total_por_tipo('venda')
    tg = db.total_por_tipo('gasto')
    historico = [
        {'id': t['id'], 'tipo': t['tipo'].capitalize(),
         'valor': t['valor'], 'criado_em': t['criado_em']}
        for t in db.listar_transacoes()
    ]
    return jsonify({'total_vendas': tv, 'total_gastos': tg,
                    'lucro': round(tv - tg, 2), 'historico': historico})

@app.route('/api/transacao/<int:id_>', methods=['DELETE'])
def api_remover_transacao(id_):
    if db.remover_transacao(id_):
        return jsonify({'sucesso': True})
    return jsonify({'sucesso': False, 'erro': 'Registro nao encontrado.'}), 404

@app.route('/api/resetar', methods=['POST'])
def api_resetar():
    db.apagar_transacoes()
    return jsonify({'sucesso': True, 'mensagem': 'Dados resetados.'})

if __name__ == '__main__':
    print("Servidor: http://localhost:5000")
    app.run(debug=True, port=5000)
