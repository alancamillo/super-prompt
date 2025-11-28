#!/bin/bash
# =============================================================================
# Script de setup para o Prompt Optimizer
# =============================================================================
# Uso:
#   ./setup.sh              # Menu interativo
#   ./setup.sh --local      # LM Studio (embeddings locais)
#   ./setup.sh --openai     # OpenAI API
#   ./setup.sh --help       # Ajuda
# =============================================================================

set -e

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Diretório do script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Variáveis
EMBEDDING_MODE=""
COMPOSE_FILE=""

# =============================================================================
# Funções
# =============================================================================

show_help() {
    echo -e "${BOLD}Prompt Optimizer - Setup Script${NC}"
    echo ""
    echo "Uso: ./setup.sh [OPÇÃO]"
    echo ""
    echo "Opções:"
    echo "  --local, -l     Usar LM Studio para embeddings (local, gratuito)"
    echo "  --openai, -o    Usar OpenAI API para embeddings (requer API key)"
    echo "  --help, -h      Mostrar esta ajuda"
    echo ""
    echo "Sem argumentos: mostra menu interativo"
    echo ""
    echo "Exemplos:"
    echo "  ./setup.sh --local     # Setup com LM Studio"
    echo "  ./setup.sh --openai    # Setup com OpenAI"
}

show_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║           🚀 Prompt Optimizer - Setup                         ║"
    echo "╠═══════════════════════════════════════════════════════════════╣"
    echo "║  Sistema de otimização de prompts com:                        ║"
    echo "║  • Persistência (PostgreSQL + Redis)                          ║"
    echo "║  • Busca vetorial (Weaviate)                                  ║"
    echo "║  • Feedback human-in-the-loop                                 ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

show_menu() {
    echo -e "${BOLD}Escolha o modo de embeddings:${NC}"
    echo ""
    echo -e "  ${GREEN}1)${NC} LM Studio (Local)"
    echo "     • Embeddings gerados localmente"
    echo "     • Sem custos de API"
    echo "     • Requer LM Studio rodando com modelo de embeddings"
    echo ""
    echo -e "  ${GREEN}2)${NC} OpenAI API"
    echo "     • Embeddings via API da OpenAI"
    echo "     • Mais rápido e fácil de configurar"
    echo "     • Requer OPENAI_API_KEY"
    echo ""
    read -p "Opção [1/2]: " choice
    
    case $choice in
        1) EMBEDDING_MODE="local" ;;
        2) EMBEDDING_MODE="openai" ;;
        *) 
            echo -e "${RED}Opção inválida. Usando padrão (local).${NC}"
            EMBEDDING_MODE="local"
            ;;
    esac
}

setup_env_local() {
    echo -e "${YELLOW}Configurando .env para LM Studio...${NC}"
    
    cat > "$PROJECT_DIR/.env" << 'EOF'
# =============================================================================
# Prompt Optimizer - Configuração LM Studio (Local)
# =============================================================================

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://prompt_optimizer:prompt_optimizer_secret@localhost:5432/prompt_optimizer

# Redis
REDIS_URL=redis://localhost:6379/0
CACHE_TTL_SECONDS=3600

# Weaviate
WEAVIATE_URL=http://localhost:8080
SIMILARITY_THRESHOLD=0.85

# LM Studio - Embeddings locais
# Ajuste LMSTUDIO_BASE_URL para o endereço do seu LM Studio
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_EMBEDDING_MODEL=nomic-embed-text-v1.5
USE_LOCAL_EMBEDDINGS=true

# OpenAI (não usado neste modo)
OPENAI_API_KEY=
EMBEDDING_MODEL=text-embedding-3-small

# Aplicação
DEBUG=false
API_PREFIX=/api/v1
EOF

    echo -e "${GREEN}✅ Arquivo .env criado para LM Studio${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANTE:${NC}"
    echo "   1. Certifique-se de que o LM Studio está rodando"
    echo "   2. Carregue um modelo de embeddings (ex: nomic-embed-text-v1.5)"
    echo "   3. Inicie o servidor local na porta 1234"
    echo ""
}

setup_env_openai() {
    echo -e "${YELLOW}Configurando .env para OpenAI...${NC}"
    
    # Pergunta pela API key
    read -p "Digite sua OPENAI_API_KEY (ou deixe vazio para configurar depois): " api_key
    
    cat > "$PROJECT_DIR/.env" << EOF
# =============================================================================
# Prompt Optimizer - Configuração OpenAI
# =============================================================================

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://prompt_optimizer:prompt_optimizer_secret@localhost:5432/prompt_optimizer

# Redis
REDIS_URL=redis://localhost:6379/0
CACHE_TTL_SECONDS=3600

# Weaviate
WEAVIATE_URL=http://localhost:8080
SIMILARITY_THRESHOLD=0.85

# OpenAI - Embeddings via API
USE_LOCAL_EMBEDDINGS=false
OPENAI_API_KEY=${api_key}
EMBEDDING_MODEL=text-embedding-3-small

# LM Studio (não usado neste modo)
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_EMBEDDING_MODEL=nomic-embed-text-v1.5

# Aplicação
DEBUG=false
API_PREFIX=/api/v1
EOF

    echo -e "${GREEN}✅ Arquivo .env criado para OpenAI${NC}"
    
    if [ -z "$api_key" ]; then
        echo ""
        echo -e "${YELLOW}⚠️  Lembre-se de configurar OPENAI_API_KEY no arquivo .env${NC}"
    fi
}

install_dependencies() {
    echo -e "${YELLOW}Instalando dependências Python...${NC}"
    cd "$PROJECT_DIR"
    pip install -r requirements.txt -r requirements-optimizer.txt
    echo -e "${GREEN}✅ Dependências instaladas${NC}"
}

start_docker() {
    echo -e "${YELLOW}Iniciando infraestrutura Docker...${NC}"
    cd "$PROJECT_DIR/docker"
    
    if [ "$EMBEDDING_MODE" = "openai" ]; then
        COMPOSE_FILE="docker-compose-openai.yml"
        echo "   Usando: docker-compose-openai.yml"
        docker compose -f docker-compose-openai.yml up -d postgres redis weaviate
    else
        COMPOSE_FILE="docker-compose.yml"
        echo "   Usando: docker-compose.yml"
        docker compose up -d postgres redis weaviate
    fi
    
    cd "$PROJECT_DIR"
    echo -e "${GREEN}✅ Containers iniciados${NC}"
}

wait_services() {
    echo -e "${YELLOW}Aguardando serviços ficarem prontos...${NC}"
    sleep 10
}

check_health() {
    echo -e "${YELLOW}Verificando saúde dos serviços...${NC}"
    
    # PostgreSQL
    if docker exec prompt_optimizer_postgres pg_isready -U prompt_optimizer > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PostgreSQL pronto${NC}"
    else
        echo -e "${RED}❌ PostgreSQL não está respondendo${NC}"
        exit 1
    fi
    
    # Redis
    if docker exec prompt_optimizer_redis redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis pronto${NC}"
    else
        echo -e "${RED}❌ Redis não está respondendo${NC}"
        exit 1
    fi
    
    # Weaviate
    if curl -s http://localhost:8080/v1/.well-known/ready > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Weaviate pronto${NC}"
    else
        echo -e "${YELLOW}⚠️  Weaviate ainda iniciando (pode levar alguns minutos)${NC}"
    fi
}

show_success() {
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}🎉 Setup completo!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BOLD}Modo de embeddings:${NC} $( [ "$EMBEDDING_MODE" = "openai" ] && echo "OpenAI API" || echo "LM Studio (Local)" )"
    echo ""
    echo -e "${BOLD}Próximos passos:${NC}"
    echo ""
    
    if [ "$EMBEDDING_MODE" = "local" ]; then
        echo "  1. Inicie o LM Studio com modelo de embeddings"
        echo "     (ex: nomic-embed-text-v1.5)"
        echo ""
        echo "  2. Inicie a API:"
        echo "     uvicorn src.prompt_optimizer.main:app --reload"
    else
        echo "  1. Verifique se OPENAI_API_KEY está configurada no .env"
        echo ""
        echo "  2. Inicie a API:"
        echo "     uvicorn src.prompt_optimizer.main:app --reload"
    fi
    
    echo ""
    echo -e "${BOLD}Comandos úteis:${NC}"
    echo ""
    echo "  # Iniciar API"
    echo "  uvicorn src.prompt_optimizer.main:app --reload"
    echo ""
    echo "  # Rodar testes"
    echo "  pytest src/prompt_optimizer/tests/ -v"
    echo ""
    echo "  # Ver logs dos containers"
    echo "  docker compose -f docker/$COMPOSE_FILE logs -f"
    echo ""
    echo "  # Parar containers"
    echo "  docker compose -f docker/$COMPOSE_FILE down"
    echo ""
    echo -e "${BOLD}Documentação da API:${NC}"
    echo "  http://localhost:8000/docs"
    echo ""
}

# =============================================================================
# Main
# =============================================================================

# Parse argumentos
case "${1:-}" in
    --local|-l)
        EMBEDDING_MODE="local"
        ;;
    --openai|-o)
        EMBEDDING_MODE="openai"
        ;;
    --help|-h)
        show_help
        exit 0
        ;;
    "")
        # Sem argumentos - mostra menu
        show_banner
        show_menu
        ;;
    *)
        echo -e "${RED}Opção desconhecida: $1${NC}"
        show_help
        exit 1
        ;;
esac

# Executa setup
echo ""
echo -e "${BLUE}Modo selecionado: $( [ "$EMBEDDING_MODE" = "openai" ] && echo "OpenAI API" || echo "LM Studio (Local)" )${NC}"
echo ""

# 1. Configura .env
if [ "$EMBEDDING_MODE" = "openai" ]; then
    setup_env_openai
else
    setup_env_local
fi

# 2. Instala dependências
install_dependencies

# 3. Inicia Docker
start_docker

# 4. Aguarda serviços
wait_services

# 5. Verifica saúde
check_health

# 6. Mostra sucesso
show_success
