#!/usr/bin/env bash
set -euo pipefail

INPUT_FILE="${1:-examples/sites.csv}"
OUTPUT_DIR="${2:-./output/batch-audit}"
MAX_PAGES="${3:-5}"
CONCURRENCY="${4:-10}"

python technical-seo-audit/scripts/technical_seo_audit.py \
  --input "${INPUT_FILE}" \
  --max-pages "${MAX_PAGES}" \
  --concurrency "${CONCURRENCY}" \
  --output-dir "${OUTPUT_DIR}"

echo "Batch audit finished. Open ${OUTPUT_DIR}/report.md, ${OUTPUT_DIR}/issues.csv, ${OUTPUT_DIR}/pages.csv, and ${OUTPUT_DIR}/summary.json."
