#!/usr/bin/env bash
set -euo pipefail

SITE_URL="${1:-https://example.com}"
OUTPUT_DIR="${2:-./output/single-site-audit}"

python technical-seo-audit/scripts/technical_seo_audit.py \
  --url "${SITE_URL}" \
  --max-pages 20 \
  --output-dir "${OUTPUT_DIR}"

echo "Audit finished. Open ${OUTPUT_DIR}/report.md and ${OUTPUT_DIR}/issues.csv."
