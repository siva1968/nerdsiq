#!/bin/bash
# NerdsIQ Production Deployment Script
# Usage: ./scripts/deploy.sh [build|up|down|logs|backup]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check required files exist
check_requirements() {
    if [ ! -f "backend/.env.prod" ]; then
        log_error "backend/.env.prod not found!"
        log_info "Copy backend/.env.prod.example to backend/.env.prod and fill in production values"
        exit 1
    fi
    
    if [ ! -f "backend/credentials/oauth-token.json" ]; then
        log_error "Google OAuth credentials not found!"
        log_info "Run: python backend/scripts/authenticate_drive.py"
        exit 1
    fi
}

# Build production images
build() {
    log_info "Building production images..."
    docker-compose -f docker-compose.prod.yml build --no-cache
    log_info "Build complete!"
}

# Start production services
up() {
    check_requirements
    log_info "Starting production services..."
    docker-compose -f docker-compose.prod.yml up -d
    log_info "Services started!"
    log_info "Run './scripts/deploy.sh logs' to view logs"
}

# Stop production services
down() {
    log_info "Stopping production services..."
    docker-compose -f docker-compose.prod.yml down
    log_info "Services stopped!"
}

# View logs
logs() {
    docker-compose -f docker-compose.prod.yml logs -f "${2:-api}"
}

# Backup databases
backup() {
    BACKUP_DIR="$PROJECT_DIR/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    log_info "Backing up PostgreSQL..."
    docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U nerdsiq nerdsiq > "$BACKUP_DIR/postgres.sql"
    
    log_info "Backing up Qdrant..."
    docker cp nerdsiq-qdrant:/qdrant/storage "$BACKUP_DIR/qdrant_storage"
    
    log_info "Backup complete: $BACKUP_DIR"
}

# Run database migrations
migrate() {
    log_info "Running database migrations..."
    docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
    log_info "Migrations complete!"
}

# Health check
health() {
    log_info "Checking service health..."
    curl -s http://localhost:8000/health | python3 -m json.tool
}

# Update and restart
update() {
    log_info "Pulling latest code..."
    git pull origin main
    
    log_info "Rebuilding API..."
    docker-compose -f docker-compose.prod.yml up -d --build api
    
    log_info "Running migrations..."
    migrate
    
    log_info "Update complete!"
}

# Show usage
usage() {
    echo "NerdsIQ Production Deployment"
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  build   - Build production Docker images"
    echo "  up      - Start production services"
    echo "  down    - Stop production services"
    echo "  logs    - View logs (default: api, or specify service)"
    echo "  backup  - Backup databases"
    echo "  migrate - Run database migrations"
    echo "  health  - Check API health"
    echo "  update  - Pull code, rebuild, and migrate"
    echo ""
}

# Main
case "${1:-}" in
    build)  build ;;
    up)     up ;;
    down)   down ;;
    logs)   logs "$@" ;;
    backup) backup ;;
    migrate) migrate ;;
    health) health ;;
    update) update ;;
    *)      usage ;;
esac
