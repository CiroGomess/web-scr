-- websrc.sql

-- Tabela de Usuários (Login)
CREATE TABLE IF NOT EXISTS user_login (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    senha TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Lotes de Processamento (Cabeçalho)
CREATE TABLE IF NOT EXISTS processamentos_lotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fornecedor TEXT,
    data_processamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_itens INTEGER
);

-- Tabela de Controle de Processamento (Status geral)
CREATE TABLE IF NOT EXISTS controle_ultimo_processamento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ultima_data_processamento TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Itens Processados (Detalhes do lote)
CREATE TABLE IF NOT EXISTS itens_processados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lote_id INTEGER,
    codigo_produto TEXT,
    nome_produto TEXT,
    marca TEXT,
    imagem_url TEXT,
    preco_unitario REAL, -- REAL substitui Numeric/Decimal
    qtd_solicitada INTEGER,
    qtd_disponivel INTEGER,
    valor_total REAL,
    pode_comprar BOOLEAN, -- SQLite aceita BOOLEAN (0 ou 1 internamente)
    status_texto TEXT,
    mensagem_erro TEXT,
    FOREIGN KEY(lote_id) REFERENCES processamentos_lotes(id)
);

-- Tabela de Detalhes Regionais (Preço por UF)
CREATE TABLE IF NOT EXISTS itens_detalhes_regionais (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER,
    uf TEXT,
    preco_regional REAL,
    qtd_disponivel_regional INTEGER,
    pode_comprar_regional BOOLEAN,
    FOREIGN KEY(item_id) REFERENCES itens_processados(id)
);