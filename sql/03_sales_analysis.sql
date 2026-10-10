-- =====================================================================
-- 03_sales_analysis.sql — revenue, growth, products, geography
-- Techniques: CTEs, window functions (LAG, SUM OVER, AVG OVER ROWS,
-- RANK/DENSE_RANK with PARTITION BY), FILTER, conditional aggregation
-- =====================================================================
SET search_path TO retail;

-- Q1. Headline KPIs (net revenue = sales - returns)
WITH s AS (
    SELECT SUM(line_value) AS gross, COUNT(DISTINCT invoice_no) AS orders,
           COUNT(DISTINCT customer_id) FILTER (WHERE customer_id <> 0) AS customers
    FROM fact_sales
), r AS (SELECT SUM(line_value) AS returns_value FROM fact_returns)
SELECT ROUND(gross, 0)                         AS gross_sales,
       ROUND(returns_value, 0)                 AS returns_value,
       ROUND(gross - returns_value, 0)         AS net_revenue,
       ROUND(100.0 * returns_value / gross, 2) AS return_rate_pct,
       orders,
       customers,
       ROUND(gross / orders, 2)                AS avg_order_value
FROM s CROSS JOIN r;

-- Q2. Monthly net revenue with MoM growth, YoY growth, running total, 3-month moving average
WITH monthly AS (
    SELECT d.year_month, MIN(d.date_value) AS month_start,
           SUM(fs.line_value) AS gross
    FROM fact_sales fs JOIN dim_date d USING (date_key)
    GROUP BY d.year_month
), monthly_ret AS (
    SELECT d.year_month, SUM(fr.line_value) AS returns_value
    FROM fact_returns fr JOIN dim_date d USING (date_key)
    GROUP BY d.year_month
), net AS (
    SELECT m.year_month, m.month_start,
           m.gross - COALESCE(r.returns_value, 0) AS net_revenue
    FROM monthly m LEFT JOIN monthly_ret r USING (year_month)
)
SELECT year_month,
       ROUND(net_revenue, 0) AS net_revenue,
       ROUND(100.0 * (net_revenue / LAG(net_revenue) OVER (ORDER BY month_start) - 1), 1)   AS mom_growth_pct,
       ROUND(100.0 * (net_revenue / LAG(net_revenue, 12) OVER (ORDER BY month_start) - 1), 1) AS yoy_growth_pct,
       ROUND(SUM(net_revenue) OVER (PARTITION BY EXTRACT(YEAR FROM month_start) ORDER BY month_start), 0) AS ytd_running_total,
       ROUND(AVG(net_revenue) OVER (ORDER BY month_start ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 0) AS moving_avg_3m
FROM net
ORDER BY month_start;

-- Q3. Category performance: revenue, share, return rate
WITH cat_sales AS (
    SELECT p.category, SUM(fs.line_value) AS gross, SUM(fs.quantity) AS units
    FROM fact_sales fs JOIN dim_product p USING (stock_code)
    GROUP BY p.category
), cat_ret AS (
    SELECT p.category, SUM(fr.line_value) AS returned
    FROM fact_returns fr JOIN dim_product p USING (stock_code)
    GROUP BY p.category
)
SELECT c.category,
       ROUND(c.gross, 0)                                       AS gross_sales,
       ROUND(100.0 * c.gross / SUM(c.gross) OVER (), 1)        AS revenue_share_pct,
       ROUND(100.0 * COALESCE(r.returned, 0) / c.gross, 2)     AS return_rate_pct,
       RANK() OVER (ORDER BY c.gross DESC)                     AS revenue_rank
FROM cat_sales c LEFT JOIN cat_ret r USING (category)
ORDER BY revenue_rank;

-- Q4. Product Pareto: how many products make up 80% of revenue?
WITH prod AS (
    SELECT stock_code, SUM(line_value) AS revenue
    FROM fact_sales GROUP BY stock_code
), ranked AS (
    SELECT stock_code, revenue,
           ROW_NUMBER() OVER (ORDER BY revenue DESC) AS rn,
           COUNT(*)     OVER ()                      AS n_products,
           SUM(revenue) OVER (ORDER BY revenue DESC ROWS UNBOUNDED PRECEDING) / SUM(revenue) OVER () AS cum_share
    FROM prod
)
SELECT MIN(rn) AS products_for_80pct,
       MAX(n_products) AS total_products,
       ROUND(100.0 * MIN(rn) / MAX(n_products), 1) AS pct_of_products
FROM ranked WHERE cum_share >= 0.80;

-- Q5. Top 3 products in each category (DENSE_RANK + PARTITION BY)
WITH prod AS (
    SELECT p.category, p.description, SUM(fs.line_value) AS revenue
    FROM fact_sales fs JOIN dim_product p USING (stock_code)
    GROUP BY p.category, p.description
), ranked AS (
    SELECT *, DENSE_RANK() OVER (PARTITION BY category ORDER BY revenue DESC) AS rnk
    FROM prod
)
SELECT category, rnk, description, ROUND(revenue, 0) AS revenue
FROM ranked WHERE rnk <= 3
ORDER BY category, rnk;

-- Q6. International markets: revenue, customers, AOV, rank (excluding UK)
SELECT fs.country, c.region,
       ROUND(SUM(fs.line_value), 0)                                       AS revenue,
       COUNT(DISTINCT fs.customer_id) FILTER (WHERE fs.customer_id <> 0) AS customers,
       ROUND(SUM(fs.line_value) / COUNT(DISTINCT fs.invoice_no), 0)       AS avg_order_value,
       RANK() OVER (ORDER BY SUM(fs.line_value) DESC)                     AS market_rank
FROM fact_sales fs JOIN dim_country c USING (country)
WHERE NOT c.is_domestic
GROUP BY fs.country, c.region
ORDER BY revenue DESC
LIMIT 10;

-- Q7. Ordering pattern: revenue by weekday and hour band
SELECT d.day_name,
       ROUND(SUM(line_value) FILTER (WHERE EXTRACT(HOUR FROM invoice_datetime) < 10), 0)              AS before_10,
       ROUND(SUM(line_value) FILTER (WHERE EXTRACT(HOUR FROM invoice_datetime) BETWEEN 10 AND 12), 0) AS h10_13,
       ROUND(SUM(line_value) FILTER (WHERE EXTRACT(HOUR FROM invoice_datetime) BETWEEN 13 AND 15), 0) AS h13_16,
       ROUND(SUM(line_value) FILTER (WHERE EXTRACT(HOUR FROM invoice_datetime) >= 16), 0)             AS after_16
FROM fact_sales JOIN dim_date d USING (date_key)
GROUP BY d.day_name, d.day_of_week_num
ORDER BY d.day_of_week_num;
