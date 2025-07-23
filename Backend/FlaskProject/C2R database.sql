-- Schema MySQL para Sistema Cliente Blockchain
-- Criação do banco de dados
DROP DATABASE IF EXISTS sistema_blockchain_cliente;
CREATE DATABASE IF NOT EXISTS sistema_blockchain_cliente;
USE sistema_blockchain_cliente;

-- Tabela de Clientes
CREATE TABLE clientes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    referencia_pix VARCHAR(255) NOT NULL UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    carteira_endereco VARCHAR(42) NOT NULL UNIQUE, -- Endereço Ethereum (42 chars com 0x)
    saldo_wei DECIMAL(65, 0) DEFAULT 0, -- Wei (máximo suportado pelo MySQL)
    saldo_ether DECIMAL(20, 8) DEFAULT 0.00000000,
    saldo_reais DECIMAL(15, 2) DEFAULT 0.00,
    registrado BOOLEAN DEFAULT TRUE,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    ativo BOOLEAN DEFAULT TRUE,
    INDEX idx_carteira (carteira_endereco),
    INDEX idx_pix (referencia_pix),
    INDEX idx_email (email)
);

CREATE TABLE IF NOT EXISTS transacao (
    id INT AUTO_INCREMENT PRIMARY KEY,
    valor_pagamento DECIMAL(10,2) NOT NULL COMMENT 'Valor do pagamento em reais',
    descricao VARCHAR(255) NULL COMMENT 'Descrição opcional da transação',
    beneficiado VARCHAR(100) NOT NULL COMMENT 'Nome do beneficiado do pagamento',
    data_transacao DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Data e hora da transação',
    hash_transacao VARCHAR(66) NOT NULL COMMENT 'Hash da transação na blockchain',
    cliente_id INT NOT NULL COMMENT 'ID do cliente que realizou a transação',

    -- Índices para melhor performance
    INDEX idx_cliente_id (cliente_id),
    INDEX idx_data_transacao (data_transacao),
    INDEX idx_hash_transacao (hash_transacao),

    -- Chave estrangeira
    CONSTRAINT fk_transacao_cliente
        FOREIGN KEY (cliente_id)
        REFERENCES clientes(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Tabela de transações PIX dos clientes';

-- Tabela de Comerciantes
CREATE TABLE comerciantes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nome VARCHAR(255) NOT NULL,
    endereco_carteira VARCHAR(42) NOT NULL UNIQUE,
    cnpj VARCHAR(18),
    email VARCHAR(255),
    telefone VARCHAR(20),
    saldo_wei DECIMAL(65, 0) DEFAULT 0,
    saldo_ether DECIMAL(20, 8) DEFAULT 0.00000000,
    saldo_reais DECIMAL(15, 2) DEFAULT 0.00,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    ativo BOOLEAN DEFAULT TRUE,
    INDEX idx_carteira_comerciante (endereco_carteira)
);

-- Tabela de ONGs
CREATE TABLE ongs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nome VARCHAR(255) NOT NULL,
    endereco_carteira VARCHAR(42) NOT NULL UNIQUE,
    cnpj VARCHAR(18),
    descricao TEXT,
    email VARCHAR(255),
    telefone VARCHAR(20),
    saldo_wei DECIMAL(65, 0) DEFAULT 0,
    saldo_ether DECIMAL(20, 8) DEFAULT 0.00000000,
    saldo_reais DECIMAL(15, 2) DEFAULT 0.00,
    ativa BOOLEAN DEFAULT TRUE,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_carteira_ong (endereco_carteira)
);

-- Tabela de Transações/Pagamentos
CREATE TABLE transacoes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    hash_transacao VARCHAR(66) NOT NULL UNIQUE, -- Hash da transação blockchain
    tipo_transacao ENUM('PAGAMENTO', 'DEPOSITO', 'SAQUE', 'TRANSFERENCIA') NOT NULL,
    cliente_id INT,
    comerciante_id INT,
    ong_id INT,
    referencia_pix VARCHAR(255),
    valor_wei DECIMAL(65, 0) NOT NULL,
    valor_ether DECIMAL(20, 8) NOT NULL,
    valor_reais DECIMAL(15, 2),
    taxa_ong_wei DECIMAL(65, 0) DEFAULT 0,
    taxa_ong_ether DECIMAL(20, 8) DEFAULT 0.00000000,
    taxa_ong_reais DECIMAL(15, 2) DEFAULT 0.00,
    status_transacao ENUM('PENDENTE', 'CONFIRMADA', 'FALHADA', 'CANCELADA') DEFAULT 'PENDENTE',
    block_number BIGINT,
    gas_usado INT,
    gas_price_wei DECIMAL(65, 0),
    nonce_transacao INT,
    data_transacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    observacoes TEXT,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE SET NULL,
    FOREIGN KEY (comerciante_id) REFERENCES comerciantes(id) ON DELETE SET NULL,
    FOREIGN KEY (ong_id) REFERENCES ongs(id) ON DELETE SET NULL,
    INDEX idx_hash (hash_transacao),
    INDEX idx_cliente (cliente_id),
    INDEX idx_comerciante (comerciante_id),
    INDEX idx_data (data_transacao),
    INDEX idx_status (status_transacao),
    INDEX idx_tipo (tipo_transacao)
);

-- Tabela de Configurações do Sistema
CREATE TABLE configuracoes_sistema (
    id INT PRIMARY KEY AUTO_INCREMENT,
    chave VARCHAR(100) NOT NULL UNIQUE,
    valor TEXT NOT NULL,
    descricao VARCHAR(255),
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_chave (chave)
);

-- Tabela de Log de Operações (para auditoria)
CREATE TABLE logs_operacoes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    usuario_tipo ENUM('CLIENTE', 'COMERCIANTE', 'ADMIN', 'SISTEMA') NOT NULL,
    usuario_id INT,
    operacao VARCHAR(100) NOT NULL,
    detalhes JSON,
    ip_origem VARCHAR(45),
    user_agent TEXT,
    status_operacao ENUM('SUCESSO', 'ERRO', 'TENTATIVA') NOT NULL,
    mensagem_erro TEXT,
    data_operacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_usuario (usuario_tipo, usuario_id),
    INDEX idx_operacao (operacao),
    INDEX idx_data_operacao (data_operacao),
    INDEX idx_status (status_operacao)
);

-- Tabela de Cotações (para conversão ETH/BRL)
CREATE TABLE cotacoes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    moeda_origem VARCHAR(10) NOT NULL DEFAULT 'ETH',
    moeda_destino VARCHAR(10) NOT NULL DEFAULT 'BRL',
    valor_cotacao DECIMAL(20, 8) NOT NULL,
    fonte VARCHAR(100), -- API ou fonte da cotação
    data_cotacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_moedas (moeda_origem, moeda_destino),
    INDEX idx_data_cotacao (data_cotacao)
);

-- Tabela de Sessões de Usuário (opcional, para controle de login)
CREATE TABLE sessoes_usuario (
    id INT PRIMARY KEY AUTO_INCREMENT,
    cliente_id INT NOT NULL,
    token_sessao VARCHAR(255) NOT NULL UNIQUE,
    ip_cliente VARCHAR(45),
    user_agent TEXT,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_expiracao TIMESTAMP NOT NULL,
    ativa BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE,
    INDEX idx_token (token_sessao),
    INDEX idx_cliente_sessao (cliente_id),
    INDEX idx_expiracao (data_expiracao)
);

-- Inserção de dados iniciais
INSERT INTO configuracoes_sistema (chave, valor, descricao) VALUES 
('cotacao_eth_brl_padrao', '18000', 'Cotação padrão ETH para BRL quando não há cotação atual'),
('taxa_ong_percentual', '5', 'Percentual da taxa destinada à ONG (em %)'),
('endereco_ong_atual', '0xC1009cB7c88bF71BcF562Dc105aEfa18459184B7', 'Endereço atual da ONG no blockchain'),
('gas_limit_padrao', '2000000', 'Limite de gas padrão para transações'),
('gas_price_gwei', '20', 'Preço do gas em Gwei');

-- Inserção da ONG padrão
INSERT INTO ongs (nome, endereco_carteira, descricao) VALUES 
('ONG Padrão do Sistema', '0xC1009cB7c88bF71BcF562Dc105aEfa18459184B7', 'ONG padrão configurada no sistema para receber taxas');

-- Views úteis para consultas
CREATE VIEW vw_transacoes_completas AS
SELECT 
    t.id,
    t.hash_transacao,
    t.tipo_transacao,
    c.nome AS nome_cliente,
    c.referencia_pix,
    com.nome AS nome_comerciante,
    o.nome AS nome_ong,
    t.valor_ether,
    t.valor_reais,
    t.status_transacao,
    t.data_transacao
FROM transacoes t
LEFT JOIN clientes c ON t.cliente_id = c.id
LEFT JOIN comerciantes com ON t.comerciante_id = com.id
LEFT JOIN ongs o ON t.ong_id = o.id;

CREATE VIEW vw_saldos_resumo AS
SELECT 
    'CLIENTES' AS tipo,
    COUNT(*) AS quantidade,
    SUM(saldo_ether) AS total_ether,
    SUM(saldo_reais) AS total_reais
FROM clientes WHERE ativo = TRUE
UNION ALL
SELECT 
    'COMERCIANTES' AS tipo,
    COUNT(*) AS quantidade,
    SUM(saldo_ether) AS total_ether,
    SUM(saldo_reais) AS total_reais
FROM comerciantes WHERE ativo = TRUE
UNION ALL
SELECT 
    'ONGS' AS tipo,
    COUNT(*) AS quantidade,
    SUM(saldo_ether) AS total_ether,
    SUM(saldo_reais) AS total_reais
FROM ongs WHERE ativa = TRUE;