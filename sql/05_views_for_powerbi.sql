-- =====================================================================
-- 05_views_for_powerbi.sql — optional: connect Power BI directly to Postgres
-- (Get Data > PostgreSQL database) instead of importing the CSVs.
-- =====================================================================
SET search_path TO retail;

DROP VIEW IF EXISTS vw_customer_360;
CREATE VIEW vw_customer_360 AS
SELECT dc.customer_id, dc.home_country, co.region, dc.first_purchase_date,
       dc.last_purchase_date, dc.cohort_month,
       ci.recency_days, ci.frequency, ci.monetary, ci.rfm_score, ci.segment,
       ci.churn_probability, ci.risk_tier, ci.annual_value, ci.revenue_at_risk_90d,
       ci.campaign_tier, ci.expected_recovery, ci.recommended_action
FROM dim_customer dc
JOIN customer_insights ci USING (customer_id)
LEFT JOIN dim_country co ON co.country = dc.home_country;

DROP VIEW IF EXISTS vw_monthly_kpis;
CREATE VIEW vw_monthly_kpis AS
WITH s AS (
    SELECT DATE_TRUNC('month', invoice_datetime)::date AS month,
           SUM(line_value) AS gross, COUNT(DISTINCT invoice_no) AS orders,
           COUNT(DISTINCT customer_id) FILTER (WHERE customer_id <> 0) AS active_customers
    FROM fact_sales GROUP BY 1
), r AS (
    SELECT DATE_TRUNC('month', invoice_datetime)::date AS month, SUM(line_value) AS returns_value
    FROM fact_returns GROUP BY 1
)
SELECT s.month, s.gross, COALESCE(r.returns_value, 0) AS returns_value,
       s.gross - COALESCE(r.returns_value, 0) AS net_revenue,
       s.orders, s.active_customers, s.gross / s.orders AS avg_order_value
FROM s LEFT JOIN r USING (month);
