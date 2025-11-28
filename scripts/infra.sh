#!/bin/bash
# =============================================================================
# Script de gerenciamento da infraestrutura - Prompt Optimizer
# =============================================================================
# Uso:
#   ./infra.sh start      # Inicia todos os containers
#   ./infra.sh stop       # Para todos os containers
#   ./infra.sh restart    # Reinicia todos os containers
#   ./infra.sh status     # Mostra status dos containers
#   ./infra.sh logs       # Mostra logs (Ctrl+C para sair)
#   ./infra.sh clean      # Para e remove volumes (CUIDADO: apaga dados!)
#   ./infra.sh help       # Mostra ajuda
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
DOCKER_DIR="$PROJECT_DIR/docker"
ENV_FILE="$PROJECT_DIR/.env"

# Detecta qual compose file usar baseado no .env
detect_compose_file() {
    if [ -f "$ENV_FILE" ]; then
        USE_LOCAL=$(grep -E "^USE_LOCAL_EMBEDDINGS=" "$ENV_FILE" | cut -d '=' -f2 | tr -d '"' | tr -d "'" | tr '[:upper:]' '[:lower:]')
        if [ "$USE_LOCAL" = "false" ]; then
            echo "docker-compose-openai.yml"
            return
        fi
    fi
    echo "docker-compose.yml"
}

COMPOSE_FILE=$(detect_compose_file)

# Comando docker compose com env-file
DOCKER_COMPOSE="docker compose --env-file $ENV_FILE -f $COMPOSE_FILE"

# =============================================================================
# Funções
# =============================================================================

show_help() {
    echo -e "${BOLD}Prompt Optimizer - Gerenciamento de Infraestrutura${NC}"
    echo ""
    echo "Uso: ./infra.sh [COMANDO]"
    echo ""
    echo "Comandos:"
    echo "  start       Inicia todos os containers"
    echo "  stop        Para todos os containers"
    echo "  restart     Reinicia todos os containers"
    echo "  status      Mostra status dos containers"
    echo "  logs        Mostra logs em tempo real (Ctrl+C para sair)"
    echo "  logs-api    Mostra logs apenas da API"
    echo "  logs-db     Mostra logs apenas do PostgreSQL"
    echo "  health      Verifica saúde dos serviços"
    echo "  config      Mostra configuração resolvida do Docker Compose"
    echo "  clean       Para containers e remove volumes (APAGA DADOS!)"
    echo "  rebuild     Reconstrói imagem da API"
    echo "  shell-db    Abre shell psql no PostgreSQL"
    echo "  shell-redis Abre shell redis-cli no Redis"
    echo "  help        Mostra esta ajuda"
    echo ""
    echo -e "Compose file: ${BLUE}$COMPOSE_FILE${NC}"
}

cmd_start() {
    echo -e "${GREEN}▶ Iniciando infraestrutura...${NC}"
    echo -e "  Usando: ${BLUE}$COMPOSE_FILE${NC}"
    echo -e "  Env:    ${BLUE}$ENV_FILE${NC}"
    cd "$DOCKER_DIR"
    $DOCKER_COMPOSE up -d
    echo ""
    echo -e "${GREEN}✅ Containers iniciados${NC}"
    echo ""
    cmd_status
}

cmd_stop() {
    echo -e "${YELLOW}⏹ Parando infraestrutura...${NC}"
    cd "$DOCKER_DIR"
    $DOCKER_COMPOSE down
    echo -e "${GREEN}✅ Containers parados${NC}"
}

cmd_restart() {
    echo -e "${YELLOW}🔄 Reiniciando infraestrutura...${NC}"
    cmd_stop
    echo ""
    cmd_start
}

cmd_status() {
    echo -e "${BOLD}📊 Status dos containers:${NC}"
    echo ""
    cd "$DOCKER_DIR"
    $DOCKER_COMPOSE ps
}

cmd_logs() {
    echo -e "${BOLD}📜 Logs dos containers (Ctrl+C para sair):${NC}"
    echo ""
    cd "$DOCKER_DIR"
    $DOCKER_COMPOSE logs -f
}

cmd_logs_api() {
    echo -e "${BOLD}📜 Logs da API (Ctrl+C para sair):${NC}"
    echo ""
    cd "$DOCKER_DIR"
    $DOCKER_COMPOSE logs -f api
}

cmd_logs_db() {
    echo -e "${BOLD}📜 Logs do PostgreSQL (Ctrl+C para sair):${NC}"
    echo ""
    cd "$DOCKER_DIR"
    $DOCKER_COMPOSE logs -f postgres
}

cmd_health() {
    echo -e "${BOLD}🏥 Verificando saúde dos serviços:${NC}"
    echo ""
    
    # PostgreSQL
    echo -n "  PostgreSQL: "
    if docker exec prompt_optimizer_postgres pg_isready -U prompt_optimizer > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Healthy${NC}"
    else
        echo -e "${RED}❌ Unhealthy${NC}"
    fi
    
    # Redis
    echo -n "  Redis:      "
    if docker exec prompt_optimizer_redis redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Healthy${NC}"
    else
        echo -e "${RED}❌ Unhealthy${NC}"
    fi
    
    # Weaviate
    echo -n "  Weaviate:   "
    if curl -s http://localhost:8080/v1/.well-known/ready > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Healthy${NC}"
    else
        echo -e "${YELLOW}⏳ Starting...${NC}"
    fi
    
    # API
    echo -n "  API:        "
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Healthy${NC}"
    else
        echo -e "${YELLOW}⚠️  Not running (start with uvicorn)${NC}"
    fi
    
    echo ""
}

cmd_clean() {
    echo -e "${RED}⚠️  ATENÇÃO: Este comando irá APAGAR TODOS OS DADOS!${NC}"
    echo ""
    read -p "Tem certeza? Digite 'sim' para confirmar: " confirm
    
    if [ "$confirm" = "sim" ]; then
        echo ""
        echo -e "${YELLOW}🗑️  Removendo containers e volumes...${NC}"
        cd "$DOCKER_DIR"
        $DOCKER_COMPOSE down -v
        echo -e "${GREEN}✅ Containers e volumes removidos${NC}"
    else
        echo -e "${BLUE}Operação cancelada.${NC}"
    fi
}

cmd_rebuild() {
    echo -e "${YELLOW}🔨 Reconstruindo imagem da API...${NC}"
    cd "$DOCKER_DIR"
    $DOCKER_COMPOSE build --no-cache api
    echo -e "${GREEN}✅ Imagem reconstruída${NC}"
    echo ""
    echo "Para aplicar, execute: ./infra.sh restart"
}

cmd_config() {
    echo -e "${BOLD}⚙️  Configuração do Docker Compose:${NC}"
    echo ""
    cd "$DOCKER_DIR"
    $DOCKER_COMPOSE config
}

cmd_shell_db() {
    echo -e "${BLUE}🐘 Abrindo shell PostgreSQL...${NC}"
    echo "  (Digite \\q para sair)"
    echo ""
    docker exec -it prompt_optimizer_postgres psql -U prompt_optimizer -d prompt_optimizer
}

cmd_shell_redis() {
    echo -e "${RED}📦 Abrindo shell Redis...${NC}"
    echo "  (Digite quit para sair)"
    echo ""
    docker exec -it prompt_optimizer_redis redis-cli
}

# =============================================================================
# Main
# =============================================================================

case "${1:-}" in
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    restart)
        cmd_restart
        ;;
    status)
        cmd_status
        ;;
    logs)
        cmd_logs
        ;;
    logs-api)
        cmd_logs_api
        ;;
    logs-db)
        cmd_logs_db
        ;;
    health)
        cmd_health
        ;;
    clean)
        cmd_clean
        ;;
    rebuild)
        cmd_rebuild
        ;;
    config)
        cmd_config
        ;;
    shell-db)
        cmd_shell_db
        ;;
    shell-redis)
        cmd_shell_redis
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        echo -e "${RED}Comando desconhecido: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac

