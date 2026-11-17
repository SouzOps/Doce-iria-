-- schema.sql — Estrutura do banco de dados da Calculateria (SQLite)
-- Executado automaticamente por database.init_db() ao iniciar o servidor.

PRAGMA foreign_keys = ON;

-- Entradas (vendas) e saídas (gastos) do controle financeiro
CREATE TABLE IF NOT EXISTS transacoes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo       TEXT    NOT NULL CHECK (tipo IN ('venda', 'gasto')),
    valor      REAL    NOT NULL CHECK (valor > 0),
    descricao  TEXT,
    criado_em  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Histórico de cálculos feitos na calculadora de preços
CREATE TABLE IF NOT EXISTS calculos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo        TEXT NOT NULL CHECK (tipo IN
                    ('lucro_unidade', 'percentual_lucro', 'vendas_totais', 'markup')),
    custo       REAL NOT NULL,
    preco_venda REAL,          -- usado em lucro_unidade, percentual_lucro, vendas_totais
    quantidade  REAL,          -- usado em vendas_totais
    markup      REAL,          -- usado em markup
    resultado   REAL NOT NULL, -- resultado principal (lucro, %, lucro total ou preço sugerido)
    criado_em   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_transacoes_tipo ON transacoes (tipo);
CREATE INDEX IF NOT EXISTS idx_calculos_tipo   ON calculos (tipo);

-- Usuários que podem entrar no sistema (cadastrados "por fora", via adicionar_usuario.py)
CREATE TABLE IF NOT EXISTS usuarios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       TEXT NOT NULL UNIQUE,   -- sempre em minúsculas
    senha_hash  TEXT NOT NULL,          -- a senha NUNCA é guardada em texto puro
    criado_em   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
