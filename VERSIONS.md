# NerdsIQ Docker Image Versions
# Update both docker-compose.yml AND docker-compose.prod.yml when changing versions
# Test changes in dev before deploying to production

# Core Services
POSTGRES_VERSION=16.2-alpine
QDRANT_VERSION=v1.7.4
MYSQL_VERSION=8.0
WORDPRESS_VERSION=latest
CLOUDFLARED_VERSION=latest

# Python Runtime (in Dockerfile)
PYTHON_VERSION=3.11-slim

# Last updated: 2026-02-03
# Tested by: Development team
