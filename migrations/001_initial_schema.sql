-- CBF Robot - Supabase Database Schema
-- Run this in Supabase SQL Editor to create all tables and indexes

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- Main Match Summary Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS jogos_resumo (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Match identifiers
    id_jogo_cbf VARCHAR(20) UNIQUE NOT NULL,  -- CBF match ID (e.g., "142-2025-001234")

    -- Match details
    data_jogo DATE NOT NULL,
    hora_inicio TIME,
    competicao VARCHAR(200) NOT NULL,
    fase VARCHAR(200),
    rodada VARCHAR(50),

    -- Teams
    time_mandante VARCHAR(200) NOT NULL,
    time_visitante VARCHAR(200) NOT NULL,

    -- Normalized names (after AI processing)
    time_mandante_normalizado VARCHAR(200),
    time_visitante_normalizado VARCHAR(200),

    -- Location
    estadio VARCHAR(200),
    estadio_normalizado VARCHAR(200),
    cidade VARCHAR(100),
    uf CHAR(2),

    -- Match result
    placar_mandante INTEGER,
    placar_visitante INTEGER,

    -- Financial data (mandante perspective)
    receita_total DECIMAL(12, 2),
    despesa_total DECIMAL(12, 2),
    saldo DECIMAL(12, 2),

    -- Audience statistics
    publico_total INTEGER,
    publico_pagante INTEGER,
    publico_nao_pagante INTEGER,
    renda_liquida DECIMAL(12, 2),

    -- Ticket pricing
    preco_ingresso_min DECIMAL(10, 2),
    preco_ingresso_max DECIMAL(10, 2),
    preco_ingresso_medio DECIMAL(10, 2),

    -- Storage
    pdf_storage_path TEXT,  -- Supabase Storage path

    -- Processing metadata
    processado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    versao_extracao INTEGER DEFAULT 1,
    modelo_ia VARCHAR(100) DEFAULT 'claude-haiku-4-5-20251001',

    -- Audit fields
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- Detailed Revenue Breakdown
-- ============================================================================
CREATE TABLE IF NOT EXISTS receitas_detalhe (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Foreign key to match
    id_jogo_cbf VARCHAR(20) NOT NULL REFERENCES jogos_resumo(id_jogo_cbf) ON DELETE CASCADE,

    -- Revenue source
    categoria VARCHAR(200) NOT NULL,  -- e.g., "Bilheteria", "Camarotes", "Patrocínio"
    subcategoria VARCHAR(200),

    -- Amount
    valor DECIMAL(12, 2) NOT NULL,

    -- Metadata
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- Detailed Expense Breakdown
-- ============================================================================
CREATE TABLE IF NOT EXISTS despesas_detalhe (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Foreign key to match
    id_jogo_cbf VARCHAR(20) NOT NULL REFERENCES jogos_resumo(id_jogo_cbf) ON DELETE CASCADE,

    -- Expense category
    categoria VARCHAR(200) NOT NULL,  -- e.g., "Arbitragem", "Segurança", "Transporte"
    subcategoria VARCHAR(200),

    -- Amount
    valor DECIMAL(12, 2) NOT NULL,

    -- Metadata
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- Processing Queue (for tracking pending PDFs)
-- ============================================================================
CREATE TABLE IF NOT EXISTS processing_queue (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Match identifier
    id_jogo_cbf VARCHAR(20) UNIQUE NOT NULL,

    -- PDF info
    pdf_url TEXT NOT NULL,
    pdf_downloaded BOOLEAN DEFAULT FALSE,
    pdf_storage_path TEXT,

    -- Processing status
    status VARCHAR(50) DEFAULT 'pending',  -- pending, processing, completed, failed
    tentativas INTEGER DEFAULT 0,
    ultimo_erro TEXT,

    -- Timestamps
    adicionado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processado_em TIMESTAMP WITH TIME ZONE,

    -- Metadata
    competicao VARCHAR(200),
    ano INTEGER
);

-- ============================================================================
-- Name Normalization Lookups
-- ============================================================================
CREATE TABLE IF NOT EXISTS normalization_lookups (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Lookup info
    categoria VARCHAR(50) NOT NULL,  -- 'team', 'stadium', 'competition'
    nome_original VARCHAR(200) NOT NULL,
    nome_normalizado VARCHAR(200) NOT NULL,

    -- Confidence (from AI normalization)
    confianca DECIMAL(3, 2) DEFAULT 1.0,  -- 0.0 to 1.0

    -- Metadata
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Unique constraint
    UNIQUE(categoria, nome_original)
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Match lookups
CREATE INDEX idx_jogos_resumo_data ON jogos_resumo(data_jogo DESC);
CREATE INDEX idx_jogos_resumo_time_mandante ON jogos_resumo(time_mandante_normalizado);
CREATE INDEX idx_jogos_resumo_time_visitante ON jogos_resumo(time_visitante_normalizado);
CREATE INDEX idx_jogos_resumo_competicao ON jogos_resumo(competicao);
CREATE INDEX idx_jogos_resumo_estadio ON jogos_resumo(estadio_normalizado);

-- Detail table foreign keys
CREATE INDEX idx_receitas_id_jogo ON receitas_detalhe(id_jogo_cbf);
CREATE INDEX idx_despesas_id_jogo ON despesas_detalhe(id_jogo_cbf);

-- Processing queue
CREATE INDEX idx_queue_status ON processing_queue(status);
CREATE INDEX idx_queue_data ON processing_queue(adicionado_em DESC);

-- Normalization lookups
CREATE INDEX idx_normalization_categoria ON normalization_lookups(categoria);

-- ============================================================================
-- Row Level Security (RLS) Policies
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE jogos_resumo ENABLE ROW LEVEL SECURITY;
ALTER TABLE receitas_detalhe ENABLE ROW LEVEL SECURITY;
ALTER TABLE despesas_detalhe ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE normalization_lookups ENABLE ROW LEVEL SECURITY;

-- Public read access (anyone can read)
CREATE POLICY "Public read access" ON jogos_resumo FOR SELECT USING (true);
CREATE POLICY "Public read access" ON receitas_detalhe FOR SELECT USING (true);
CREATE POLICY "Public read access" ON despesas_detalhe FOR SELECT USING (true);
CREATE POLICY "Public read access" ON normalization_lookups FOR SELECT USING (true);

-- Service role full access (for backend worker)
-- Note: Use service_role key in backend, anon key in dashboard

-- ============================================================================
-- Helpful Views
-- ============================================================================

-- View: Match summary with team names normalized
CREATE OR REPLACE VIEW v_jogos_limpo AS
SELECT
    j.id,
    j.id_jogo_cbf,
    j.data_jogo,
    j.hora_inicio,
    j.competicao,
    j.fase,
    j.rodada,
    COALESCE(j.time_mandante_normalizado, j.time_mandante) as time_mandante,
    COALESCE(j.time_visitante_normalizado, j.time_visitante) as time_visitante,
    COALESCE(j.estadio_normalizado, j.estadio) as estadio,
    j.cidade,
    j.uf,
    j.placar_mandante,
    j.placar_visitante,
    j.receita_total,
    j.despesa_total,
    j.saldo,
    j.publico_total,
    j.publico_pagante,
    j.renda_liquida,
    j.preco_ingresso_medio
FROM jogos_resumo j
ORDER BY j.data_jogo DESC;

-- View: Revenue aggregation by team
CREATE OR REPLACE VIEW v_receita_por_time AS
SELECT
    COALESCE(time_mandante_normalizado, time_mandante) as time,
    COUNT(*) as total_jogos,
    SUM(receita_total) as receita_total,
    AVG(receita_total) as receita_media,
    SUM(publico_pagante) as publico_total,
    AVG(publico_pagante) as publico_medio
FROM jogos_resumo
WHERE time_mandante IS NOT NULL
GROUP BY COALESCE(time_mandante_normalizado, time_mandante)
ORDER BY receita_total DESC;

-- View: Stadium statistics
CREATE OR REPLACE VIEW v_estatisticas_estadio AS
SELECT
    COALESCE(estadio_normalizado, estadio) as estadio,
    cidade,
    uf,
    COUNT(*) as total_jogos,
    AVG(publico_total) as publico_medio,
    MAX(publico_total) as publico_maximo,
    AVG(renda_liquida) as renda_media,
    SUM(renda_liquida) as renda_total
FROM jogos_resumo
WHERE estadio IS NOT NULL
GROUP BY COALESCE(estadio_normalizado, estadio), cidade, uf
ORDER BY total_jogos DESC;

-- ============================================================================
-- Functions
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for jogos_resumo
CREATE TRIGGER update_jogos_resumo_updated_at
    BEFORE UPDATE ON jogos_resumo
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for normalization_lookups
CREATE TRIGGER update_normalization_lookups_updated_at
    BEFORE UPDATE ON normalization_lookups
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Sample Data Insert (for testing)
-- ============================================================================

-- You can uncomment this to add test data:
/*
INSERT INTO jogos_resumo (
    id_jogo_cbf, data_jogo, competicao, time_mandante, time_visitante,
    estadio, cidade, uf, placar_mandante, placar_visitante,
    receita_total, despesa_total, publico_total
) VALUES (
    '142-2025-001234',
    '2025-01-15',
    'Campeonato Brasileiro Série A',
    'São Paulo Futebol Clube',
    'Santos Futebol Clube',
    'Estádio do Morumbi',
    'São Paulo',
    'SP',
    2,
    1,
    1500000.00,
    300000.00,
    45000
);
*/

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Run these to verify the schema was created correctly:

-- Check tables
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- Check indexes
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- Check RLS policies
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
FROM pg_policies
WHERE schemaname = 'public';
