#!/bin/bash
# Lightweight Docker context detection for odoo-docker plugin
# Outputs a brief status line if Docker-related files are found

status=""

# Check for docker-compose files
compose_count=$(find . -maxdepth 2 -name "docker-compose*.yml" -o -name "docker-compose*.yaml" 2>/dev/null | wc -l)
if [ "$compose_count" -gt 0 ]; then
    status="Docker compose files: $compose_count"
fi

# Check for Dockerfile
if [ -f "Dockerfile" ] || [ -f "docker/Dockerfile" ]; then
    if [ -n "$status" ]; then
        status="$status | Dockerfile: found"
    else
        status="Dockerfile: found"
    fi
fi

# Check if Docker is running
if docker info >/dev/null 2>&1; then
    running=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -c "odoo\|_web\|_db" || true)
    if [ "$running" -gt 0 ]; then
        status="${status:+$status | }Odoo containers running: $running"
    fi
fi

if [ -n "$status" ]; then
    echo "[odoo-docker] $status. Use /odoo-docker for infrastructure commands."
fi
