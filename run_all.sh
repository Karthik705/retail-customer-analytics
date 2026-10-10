#!/usr/bin/env bash
# Reproduce the whole project: notebooks (in order) -> PostgreSQL warehouse -> SQL analysis.
# Usage:  bash run_all.sh            (requires Python deps + a local PostgreSQL)
#         SKIP_SQL=1 bash run_all.sh (Python only)
set -euo pipefail
cd "$(dirname "$0")"

echo "==> Executing notebooks"
for nb in notebooks/0*.ipynb; do
  echo "    $nb"
  jupyter nbconvert --to notebook --execute --inplace "$nb" --ExecutePreprocessor.timeout=1800 --log-level=WARN
done

if [ "${SKIP_SQL:-0}" != "1" ]; then
  DB="${PGDATABASE:-retail}"
  echo "==> Building PostgreSQL warehouse in database '$DB'"
  psql -d "$DB" -q -f sql/01_create_schema.sql
  psql -d "$DB" -f sql/02_load_data.sql
  for f in sql/03_sales_analysis.sql sql/04_customer_analysis.sql sql/05_views_for_powerbi.sql; do
    [ -f "$f" ] && psql -d "$DB" -q -f "$f" > /dev/null && echo "    ran $f"
  done
fi
echo "==> Done. Processed data in data/processed/, charts in images/."
