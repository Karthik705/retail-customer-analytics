-- =====================================================================
-- 02_load_data.sql  —  bulk-load the processed CSVs
-- Run from the repository root:  psql -d retail -f sql/02_load_data.sql
-- (\copy reads files on the client, so no server file permissions needed)
-- =====================================================================
SET search_path TO retail;

\copy dim_date     FROM 'data/processed/dim_date.csv'     WITH (FORMAT csv, HEADER true)
\copy dim_country  FROM 'data/processed/dim_country.csv'  WITH (FORMAT csv, HEADER true)
\copy dim_product  FROM 'data/processed/dim_product.csv'  WITH (FORMAT csv, HEADER true)
\copy dim_customer FROM 'data/processed/dim_customer.csv' WITH (FORMAT csv, HEADER true)

\copy fact_sales   FROM 'data/processed/fact_sales/fact_sales_2009.csv' WITH (FORMAT csv, HEADER true)
\copy fact_sales   FROM 'data/processed/fact_sales/fact_sales_2010.csv' WITH (FORMAT csv, HEADER true)
\copy fact_sales   FROM 'data/processed/fact_sales/fact_sales_2011.csv' WITH (FORMAT csv, HEADER true)
\copy fact_returns FROM 'data/processed/fact_returns.csv' WITH (FORMAT csv, HEADER true)
\copy fact_fees    FROM 'data/processed/fact_fees.csv'    WITH (FORMAT csv, HEADER true)

\copy customer_insights FROM 'data/processed/customer_insights.csv' WITH (FORMAT csv, HEADER true)

ANALYZE;

-- Row-count reconciliation against the Python pipeline
SELECT 'fact_sales' AS tbl, COUNT(*) FROM fact_sales
UNION ALL SELECT 'fact_returns', COUNT(*) FROM fact_returns
UNION ALL SELECT 'fact_fees', COUNT(*) FROM fact_fees
UNION ALL SELECT 'dim_customer', COUNT(*) FROM dim_customer
UNION ALL SELECT 'dim_product', COUNT(*) FROM dim_product
UNION ALL SELECT 'customer_insights', COUNT(*) FROM customer_insights;
