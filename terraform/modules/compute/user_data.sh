#!/bin/bash
set -euo pipefail
exec > /var/log/user-data.log 2>&1

echo "=== Bootstrap started at $(date) ==="

# ── Docker + Compose ──
dnf update -y
dnf install -y docker git --allowerasing
systemctl enable docker && systemctl start docker
usermod -aG docker ec2-user

DOCKER_CONFIG=/usr/local/lib/docker/cli-plugins
mkdir -p $DOCKER_CONFIG
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
  -o $DOCKER_CONFIG/docker-compose
chmod +x $DOCKER_CONFIG/docker-compose

curl -SL "https://github.com/docker/buildx/releases/download/v0.21.1/buildx-v0.21.1.linux-amd64" \
  -o $DOCKER_CONFIG/docker-buildx
chmod +x $DOCKER_CONFIG/docker-buildx

# ── Clone Repo ──
cd /opt
git clone --depth 1 https://github.com/AyushSriva2598/APIGateway.git apigateway
cd apigateway
rm -rf gateway/vevn

# ── Ensure Dockerfile.prod exists ──
cat << 'DOCKERFILE_EOF' > Dockerfile.prod
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/prod.txt

COPY gateway/ .

RUN python manage.py collectstatic --noinput 2>/dev/null || true

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-", "--timeout", "30", "config.wsgi"]
DOCKERFILE_EOF

# ── Ensure docker-compose.prod.yml exists ──
cat << 'COMPOSE_EOF' > docker-compose.prod.yml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: gateway
      POSTGRES_USER: gateway
      POSTGRES_PASSWORD: gateway-demo-2026
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U gateway"]
      interval: 5s
      retries: 5
    restart: always

  gateway:
    build:
      context: .
      dockerfile: Dockerfile.prod
    env_file: .env.prod
    depends_on:
      postgres: { condition: service_healthy }
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 10s
      retries: 3
      start_period: 30s

  nginx:
    image: nginx:alpine
    ports: ["8080:80"]
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      gateway: { condition: service_healthy }
    restart: always

  prometheus:
    image: prom/prometheus
    ports: ["9090:9090"]
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    restart: always

  grafana:
    image: grafana/grafana
    ports: ["3000:3000"]
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=demo
      - GF_AUTH_ANONYMOUS_ENABLED=true
      - GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer
    volumes:
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
    restart: always

volumes:
  pgdata:
COMPOSE_EOF

# ── Ensure seed_demo_data command exists ──
mkdir -p gateway/authentication/management/commands
touch gateway/authentication/management/__init__.py
touch gateway/authentication/management/commands/__init__.py
cat << 'SEED_EOF' > gateway/authentication/management/commands/seed_demo_data.py
from django.core.management.base import BaseCommand
from authentication.models import Tier, APIKey

class Command(BaseCommand):
    help = "Seed demo tiers and API keys"

    def handle(self, *args, **options):
        free_tier, _ = Tier.objects.get_or_create(
            name="free",
            defaults=dict(algorithm="token_bucket", capacity=10, refill_rate=10 / 60),
        )
        pro_tier, _ = Tier.objects.get_or_create(
            name="pro",
            defaults=dict(algorithm="sliding_window", limit=100, window_seconds=60),
        )
        ent_tier, _ = Tier.objects.get_or_create(
            name="enterprise",
            defaults=dict(algorithm="fixed_window", limit=1000, window_seconds=60),
        )
        for tier, owner in [(free_tier, "demo-free"), (pro_tier, "demo-pro"), (ent_tier, "demo-enterprise")]:
            if not APIKey.objects.filter(owner=owner).exists():
                raw_key, key_hash, key_prefix = APIKey.generate_key()
                APIKey.objects.create(key_hash=key_hash, key_prefix=key_prefix, owner=owner, tier=tier)
                self.stdout.write(f"  demo key: {owner} -> {raw_key}")
SEED_EOF

# ── Production env (Postgres=local container, Redis=ElastiCache) ──
cat > .env.prod <<EOF
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_SECRET_KEY=${django_secret}
ALLOWED_HOSTS=${allowed_hosts}
POSTGRES_DB=gateway
POSTGRES_USER=gateway
POSTGRES_PASSWORD=gateway-demo-2026
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
REDIS_HOST=${redis_host}
REDIS_PORT=${redis_port}
EOF

# ── Build & Launch ──
docker build -t apigateway-gateway:latest -f Dockerfile.prod .
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# ── Wait → Migrate → Seed ──
echo "Waiting for containers..."
sleep 25

docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T gateway \
  python manage.py migrate --noinput 2>&1 || true

sleep 5

docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T gateway \
  python manage.py migrate --noinput 2>&1 || true

echo ""
echo "============================================"
echo "  SEEDING DEMO DATA"
echo "============================================"
docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T gateway \
  python manage.py seed_demo_data 2>&1

echo ""
echo "=== Bootstrap completed at $(date) ==="
