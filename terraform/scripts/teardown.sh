#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Load AWS credentials from .env if present
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

echo "╔══════════════════════════════════════════════╗"
echo "║  DESTROYING ALL DEMO INFRASTRUCTURE          ║"
echo "╚══════════════════════════════════════════════╝"

terraform destroy -auto-approve

echo ""
echo "✅ All resources destroyed. AWS bill stops now."
