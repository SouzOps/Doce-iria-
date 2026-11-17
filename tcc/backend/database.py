# database.py — Camada de acesso ao banco SQLite da Calculateria.
# Toda a conversa com o banco passa por aqui; o main.py só chama estas funções.

import os
import sqlite3
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# O banco fica em backend/data/calculateria.db. Para guardá-lo em outro lugar,
# defina a variável de ambiente CALCULATERIA_DB com o caminho do arquivo.
DB_PATH = os.environ.get('CALCULATERIA_DB') or os.path.join(BASE_DIR, 'data', 'calculateria.db')
SCHEMA_PATH = os.path.join(BASE_DIR, 'schema.sql')


def get_conn():
    """Abre uma conexão. Linhas voltam como dicionário (row['valor'])."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    """Cria o arquivo .db e as tabelas, se ainda não existirem."""
    with open(SCHEMA_PATH, encoding='utf-8') as f:
        script = f.read()
    conn = get_conn()
    try:
        conn.executescript(script)
        conn.commit()
    finally:
        conn.close()


def fazer_backup(manter=7):
    """Copia o banco para data/backups/calculateria-AAAA-MM-DD.db a cada vez que o
    servidor inicia (uma cópia por dia; guarda as últimas `manter`)."""
    if not os.path.exists(DB_PATH):
        return
    pasta = os.path.join(os.path.dirname(DB_PATH), 'backups')
    os.makedirs(pasta, exist_ok=True)
    destino = os.path.join(pasta, f'calculateria-{date.today().isoformat()}.db')
    origem, copia = get_conn(), sqlite3.connect(destino)
    try:
        origem.backup(copia)
    finally:
        copia.close()
        origem.close()
    for antigo in sorted(f for f in os.listdir(pasta) if f.endswith('.db'))[:-manter]:
        os.remove(os.path.join(pasta, antigo))


# ─── Transações (vendas e gastos) ────────────────────────────────────────────

def adicionar_transacao(tipo, valor, descricao=None):
    conn = get_conn()
    try:
        cur = conn.execute(
            'INSERT INTO transacoes (tipo, valor, descricao) VALUES (?, ?, ?)',
            (tipo, valor, descricao),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def total_por_tipo(tipo):
    conn = get_conn()
    try:
        row = conn.execute(
            'SELECT COALESCE(SUM(valor), 0) AS total FROM transacoes WHERE tipo = ?',
            (tipo,),
        ).fetchone()
        return round(row['total'], 2)
    finally:
        conn.close()


def listar_transacoes():
    """Todas as transações, da mais antiga para a mais nova."""
    conn = get_conn()
    try:
        rows = conn.execute(
            'SELECT id, tipo, valor, descricao, criado_em FROM transacoes ORDER BY id'
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def remover_transacao(id_):
    conn = get_conn()
    try:
        cur = conn.execute('DELETE FROM transacoes WHERE id = ?', (id_,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def apagar_transacoes():
    conn = get_conn()
    try:
        conn.execute('DELETE FROM transacoes')
        conn.commit()
    finally:
        conn.close()


# ─── Histórico de cálculos ───────────────────────────────────────────────────

def registrar_calculo(tipo, resultado, custo, preco_venda=None, quantidade=None, markup=None):
    conn = get_conn()
    try:
        conn.execute(
            '''INSERT INTO calculos (tipo, custo, preco_venda, quantidade, markup, resultado)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (tipo, custo, preco_venda, quantidade, markup, resultado),
        )
        conn.commit()
    finally:
        conn.close()


def listar_calculos(limite=50):
    conn = get_conn()
    try:
        rows = conn.execute(
            'SELECT * FROM calculos ORDER BY id DESC LIMIT ?', (limite,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ─── Usuários ────────────────────────────────────────────────────────────────

def criar_usuario(email, senha_hash):
    """Retorna o id criado, ou None se o e-mail já existir."""
    conn = get_conn()
    try:
        cur = conn.execute(
            'INSERT INTO usuarios (email, senha_hash) VALUES (?, ?)', (email, senha_hash)
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def buscar_usuario_por_email(email):
    conn = get_conn()
    try:
        row = conn.execute('SELECT * FROM usuarios WHERE email = ?', (email,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def listar_usuarios():
    conn = get_conn()
    try:
        rows = conn.execute('SELECT id, email, criado_em FROM usuarios ORDER BY id').fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def remover_usuario(email):
    conn = get_conn()
    try:
        cur = conn.execute('DELETE FROM usuarios WHERE email = ?', (email,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
