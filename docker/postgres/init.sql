-- Extensão para UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enum para tipos de feedback
CREATE TYPE feedback_type AS ENUM ('positive', 'negative', 'suggestion');

-- Tabela: prompt_templates
-- Armazena templates de prompts com versionamento
CREATE TABLE prompt_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Índice único para name + version (evita duplicatas)
    CONSTRAINT unique_name_version UNIQUE (name, version)
);

-- Tabela: optimization_requests
-- Registra cada requisição de otimização recebida
CREATE TABLE optimization_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    original_request TEXT NOT NULL,
    weaviate_vector_id VARCHAR(255),
    matched_request_id UUID REFERENCES optimization_requests(id),
    similarity_score FLOAT,
    prompt_template_id UUID REFERENCES prompt_templates(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela: prompt_executions
-- Registra a execução real do prompt com resposta do LLM
CREATE TABLE prompt_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    optimization_request_id UUID REFERENCES optimization_requests(id),
    prompt_template_id UUID REFERENCES prompt_templates(id),
    prompt_rendered TEXT NOT NULL,
    llm_response TEXT,
    llm_model VARCHAR(100),
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    latency_ms INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela: feedbacks
-- Armazena feedback humano sobre as respostas
CREATE TABLE feedbacks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id UUID NOT NULL REFERENCES prompt_executions(id),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    observation TEXT,
    suggested_correction TEXT,
    feedback_type feedback_type NOT NULL DEFAULT 'suggestion',
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índices para performance
CREATE INDEX idx_prompt_templates_name ON prompt_templates(name);
CREATE INDEX idx_prompt_templates_active ON prompt_templates(is_active);
CREATE INDEX idx_optimization_requests_created ON optimization_requests(created_at);
CREATE INDEX idx_optimization_requests_matched ON optimization_requests(matched_request_id);
CREATE INDEX idx_prompt_executions_request ON prompt_executions(optimization_request_id);
CREATE INDEX idx_feedbacks_execution ON feedbacks(execution_id);
CREATE INDEX idx_feedbacks_type ON feedbacks(feedback_type);
CREATE INDEX idx_feedbacks_rating ON feedbacks(rating);

-- Função para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger para prompt_templates
CREATE TRIGGER update_prompt_templates_updated_at
    BEFORE UPDATE ON prompt_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

