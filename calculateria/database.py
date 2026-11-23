# database.py — Banco de dados da Calculateria (SQLite, um único arquivo).
# Tabelas: usuarios, equipes, convites e transacoes. São criadas sozinhas na primeira execução
# (e atualizadas sozinhas se você já tinha um banco da versão anterior).
# O arquivo fica em data/calculateria.db (ou no caminho da variável CALCULATERIA_DB).
#
# Como funciona a equipe:
#   - cada usuário pode estar em NO MÁXIMO UMA equipe (usuarios.equipe_id);
#   - uma transação com equipe_id vazio é PESSOAL; com equipe_id preenchido é da EQUIPE
#     (usuario_id guarda quem registrou);
#   - convites ficam pendentes até a pessoa aceitar (e-mail convidado, mesmo sem conta ainda).

import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('CALCULATERIA_DB') or os.path.join(BASE_DIR, 'data', 'calculateria.db')

SCHEMA = """
CREATE TABLE IF NOT EXISTS equipes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT NOT NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS usuarios (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    email      TEXT NOT NULL UNIQUE,          -- sempre em minúsculas
    senha_hash TEXT NOT NULL,                 -- a senha nunca é guardada em texto puro
    equipe_id  INTEGER REFERENCES equipes(id) ON DELETE SET NULL,
    criado_em  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS transacoes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    equipe_id  INTEGER REFERENCES equipes(id) ON DELETE CASCADE,   -- vazio = pessoal
    tipo       TEXT NOT NULL CHECK (tipo IN ('venda', 'gasto')),
    valor      REAL NOT NULL CHECK (valor > 0),
    criado_em  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS convites (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    equipe_id     INTEGER NOT NULL REFERENCES equipes(id) ON DELETE CASCADE,
    de_usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    para_email    TEXT NOT NULL,
    criado_em     TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (equipe_id, para_email)
);
"""


def _conectar():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def _executar(sql, params=(), um=False, todos=False, escrever=False):
    """Abre a conexão, roda um comando e fecha. Evita repetir try/finally em todo lugar."""
    conn = _conectar()
    try:
        cur = conn.execute(sql, params)
        if escrever:
            conn.commit()
            return cur
        if um:
            row = cur.fetchone()
            return dict(row) if row else None
        if todos:
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def iniciar():
    """Cria as tabelas e atualiza bancos antigos (que ainda não tinham equipes)."""
    conn = _conectar()
    try:
        conn.executescript(SCHEMA)
        for tabela, comando in (
            ('usuarios',   'ALTER TABLE usuarios ADD COLUMN equipe_id INTEGER REFERENCES equipes(id) ON DELETE SET NULL'),
            ('transacoes', 'ALTER TABLE transacoes ADD COLUMN equipe_id INTEGER REFERENCES equipes(id) ON DELETE CASCADE'),
        ):
            colunas = {r['name'] for r in conn.execute(f'PRAGMA table_info({tabela})')}
            if 'equipe_id' not in colunas:
                conn.execute(comando)
        conn.executescript("""
            CREATE INDEX IF NOT EXISTS idx_transacoes_usuario ON transacoes (usuario_id);
            CREATE INDEX IF NOT EXISTS idx_transacoes_equipe  ON transacoes (equipe_id);
        """)
        conn.commit()
    finally:
        conn.close()


# ─── Usuários ────────────────────────────────────────────────────────────────

def criar_usuario(email, senha_hash):
    """Devolve o id criado, ou None se o e-mail já existir."""
    try:
        return _executar('INSERT INTO usuarios (email, senha_hash) VALUES (?, ?)',
                         (email, senha_hash), escrever=True).lastrowid
    except sqlite3.IntegrityError:
        return None


def buscar_usuario(email):
    return _executar('SELECT * FROM usuarios WHERE email = ?', (email,), um=True)


# ─── Vendas e gastos PESSOAIS (equipe_id vazio) ──────────────────────────────

def adicionar_transacao(usuario_id, tipo, valor, equipe_id=None):
    """Sem equipe_id = registro pessoal. Com equipe_id = registro da equipe."""
    _executar('INSERT INTO transacoes (usuario_id, equipe_id, tipo, valor) VALUES (?, ?, ?, ?)',
              (usuario_id, equipe_id, tipo, valor), escrever=True)


def listar_transacoes(usuario_id):
    return _executar('SELECT id, tipo, valor, criado_em FROM transacoes '
                     'WHERE usuario_id = ? AND equipe_id IS NULL ORDER BY id',
                     (usuario_id,), todos=True)


def total_por_tipo(usuario_id, tipo):
    row = _executar('SELECT COALESCE(SUM(valor), 0) AS total FROM transacoes '
                    'WHERE usuario_id = ? AND equipe_id IS NULL AND tipo = ?',
                    (usuario_id, tipo), um=True)
    return round(row['total'], 2)


def remover_transacao(usuario_id, id_):
    """Só o autor consegue apagar um registro (pessoal ou da equipe)."""
    cur = _executar('DELETE FROM transacoes WHERE id = ? AND usuario_id = ?',
                    (id_, usuario_id), escrever=True)
    return cur.rowcount > 0


def apagar_transacoes(usuario_id):
    """Limpa só os registros PESSOAIS; os da equipe não são tocados."""
    _executar('DELETE FROM transacoes WHERE usuario_id = ? AND equipe_id IS NULL',
              (usuario_id,), escrever=True)


# ─── Equipes ─────────────────────────────────────────────────────────────────

def equipe_do_usuario(usuario_id):
    return _executar('SELECT e.id, e.nome FROM equipes e JOIN usuarios u ON u.equipe_id = e.id '
                     'WHERE u.id = ?', (usuario_id,), um=True)


def criar_equipe(usuario_id, nome):
    conn = _conectar()
    try:
        equipe_id = conn.execute('INSERT INTO equipes (nome) VALUES (?)', (nome,)).lastrowid
        conn.execute('UPDATE usuarios SET equipe_id = ? WHERE id = ?', (equipe_id, usuario_id))
        conn.commit()
        return equipe_id
    finally:
        conn.close()


def sair_da_equipe(usuario_id, equipe_id):
    """Tira o usuário da equipe. Se ninguém sobrar, a equipe (e seus registros) é apagada."""
    conn = _conectar()
    try:
        conn.execute('UPDATE usuarios SET equipe_id = NULL WHERE id = ?', (usuario_id,))
        restam = conn.execute('SELECT COUNT(*) FROM usuarios WHERE equipe_id = ?',
                              (equipe_id,)).fetchone()[0]
        if restam == 0:
            conn.execute('DELETE FROM equipes WHERE id = ?', (equipe_id,))
        conn.commit()
    finally:
        conn.close()


def resumo_equipe(equipe_id):
    """Uma linha por pessoa: vendas e gastos que ela registrou na equipe.
    Quem já saiu da equipe continua aparecendo (ativo=False) porque os registros ficam."""
    membros = _executar('SELECT id, email FROM usuarios WHERE equipe_id = ? ORDER BY id',
                        (equipe_id,), todos=True)
    somas = _executar(
        "SELECT u.id, u.email, "
        "COALESCE(SUM(CASE WHEN t.tipo = 'venda' THEN t.valor END), 0) AS vendas, "
        "COALESCE(SUM(CASE WHEN t.tipo = 'gasto' THEN t.valor END), 0) AS gastos "
        "FROM transacoes t JOIN usuarios u ON u.id = t.usuario_id "
        "WHERE t.equipe_id = ? GROUP BY u.id", (equipe_id,), todos=True)
    pessoas = {m['id']: {'id': m['id'], 'email': m['email'], 'ativo': True,
                         'vendas': 0.0, 'gastos': 0.0} for m in membros}
    for s in somas:
        p = pessoas.setdefault(s['id'], {'id': s['id'], 'email': s['email'], 'ativo': False})
        p['vendas'], p['gastos'] = round(s['vendas'], 2), round(s['gastos'], 2)
    return list(pessoas.values())


def listar_transacoes_equipe(equipe_id, limite=500):
    """Registros da equipe, do mais novo para o mais antigo, com o e-mail de quem registrou."""
    return _executar('SELECT t.id, t.tipo, t.valor, t.criado_em, t.usuario_id, u.email AS autor '
                     'FROM transacoes t JOIN usuarios u ON u.id = t.usuario_id '
                     'WHERE t.equipe_id = ? ORDER BY t.id DESC LIMIT ?',
                     (equipe_id, limite), todos=True)


# ─── Convites ────────────────────────────────────────────────────────────────

def criar_convite(equipe_id, de_usuario_id, para_email):
    """Devolve o id, ou None se já existe convite pendente para esse e-mail nessa equipe."""
    try:
        return _executar('INSERT INTO convites (equipe_id, de_usuario_id, para_email) VALUES (?, ?, ?)',
                         (equipe_id, de_usuario_id, para_email), escrever=True).lastrowid
    except sqlite3.IntegrityError:
        return None


def convites_da_equipe(equipe_id):
    return _executar('SELECT id, para_email FROM convites WHERE equipe_id = ? ORDER BY id',
                     (equipe_id,), todos=True)


def convites_para(email):
    return _executar('SELECT c.id, e.nome AS equipe_nome, u.email AS de_email '
                     'FROM convites c JOIN equipes e ON e.id = c.equipe_id '
                     'JOIN usuarios u ON u.id = c.de_usuario_id '
                     'WHERE c.para_email = ? ORDER BY c.id', (email,), todos=True)


def buscar_convite(convite_id):
    return _executar('SELECT * FROM convites WHERE id = ?', (convite_id,), um=True)


def remover_convite(convite_id):
    _executar('DELETE FROM convites WHERE id = ?', (convite_id,), escrever=True)


def aceitar_convite(usuario_id, convite):
    conn = _conectar()
    try:
        conn.execute('UPDATE usuarios SET equipe_id = ? WHERE id = ?', (convite['equipe_id'], usuario_id))
        conn.execute('DELETE FROM convites WHERE equipe_id = ? AND para_email = ?',
                     (convite['equipe_id'], convite['para_email']))
        conn.commit()
    finally:
        conn.close()
