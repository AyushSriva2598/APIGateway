#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Load AWS credentials from .env if present
if [ -f .env ]; then
  echo "Loading environment variables from .env..."
  set -a
  source .env
  set +a
fi

echo "╔══════════════════════════════════════════════════╗"
echo "║  API Gateway — HA Architecture Demo Deployment  ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "Step 1/3: Initializing Terraform..."
terraform init

echo ""
echo "Step 2/3: Planning infrastructure..."
terraform plan -out=demo.tfplan

echo ""
read -p "Step 3/3: Apply? (yes/no): " confirm
if [ "$confirm" = "yes" ]; then
  terraform apply demo.tfplan
  echo ""
  echo "════════════════════════════════════════"
  echo "  ✅ DEPLOYMENT COMPLETE"
  echo "════════════════════════════════════════"
  terraform output
  echo ""
  echo "⚠️  Run ./scripts/teardown.sh after the demo!"
else
  echo "Aborted."
fi
