-- =====================================================================
-- 04_customer_analysis.sql — concentration, cohorts, RFM, churn/campaign
-- Techniques: multi-step CTEs, NTILE, PERCENT_RANK, CASE segmentation,
-- self-referencing cohort logic, joins to model output
-- =====================================================================
SET search_path TO retail;

-- Q8. Customer concentration: share of net revenue from the top 20% of customers
WITH cust AS (
    SELECT customer_id, SUM(line_value) AS gross FROM fact_sales
    WHERE customer_id <> 0 GROUP BY customer_id
), net AS (
    SELECT c.customer_id,
           GREATEST(c.gross - COALESCE(SUM(r.line_value), 0), 0) AS net_revenue
    FROM cust c LEFT JOIN fact_returns r USING (customer_id)
    GROUP BY c.customer_id, c.gross
), ranked AS (
    SELECT net_revenue, NTILE(5) OVER (ORDER BY net_revenue DESC) AS quintile FROM net
)
SELECT quintile,
       COUNT(*) AS customers,
       ROUND(SUM(net_revenue), 0) AS net_revenue,
       ROUND(100.0 * SUM(net_revenue) / SUM(SUM(net_revenue)) OVER (), 1) AS revenue_share_pct
FROM ranked GROUP BY quintile ORDER BY quintile;

-- Q9. Repeat-purchase funnel: 1st -> 2nd -> 3rd -> 5th -> 10th order
WITH orders_per_customer AS (
    SELECT customer_id, COUNT(DISTINCT invoice_no) AS n_orders
    FROM fact_sales WHERE customer_id <> 0 GROUP BY customer_id
)
SELECT stage, customers,
       ROUND(100.0 * customers / FIRST_VALUE(customers) OVER (ORDER BY min_orders), 1) AS pct_of_all
FROM (
    SELECT '1+ orders' AS stage, 1 AS min_orders, COUNT(*) FILTER (WHERE n_orders >= 1) AS customers FROM orders_per_customer
    UNION ALL SELECT '2+ orders', 2, COUNT(*) FILTER (WHERE n_orders >= 2) FROM orders_per_customer
    UNION ALL SELECT '3+ orders', 3, COUNT(*) FILTER (WHERE n_orders >= 3) FROM orders_per_customer
    UNION ALL SELECT '5+ orders', 5, COUNT(*) FILTER (WHERE n_orders >= 5) FROM orders_per_customer
    UNION ALL SELECT '10+ orders', 10, COUNT(*) FILTER (WHERE n_orders >= 10) FROM orders_per_customer
) f
ORDER BY min_orders;

-- Q10. Cohort retention matrix (months 0-6) computed purely in SQL
WITH first_purchase AS (
    SELECT customer_id, DATE_TRUNC('month', MIN(invoice_datetime))::date AS cohort_month
    FROM fact_sales WHERE customer_id <> 0 GROUP BY customer_id
), activity AS (
    SELECT DISTINCT fs.customer_id, fp.cohort_month,
           (EXTRACT(YEAR FROM fs.invoice_datetime) - EXTRACT(YEAR FROM fp.cohort_month)) * 12
         + (EXTRACT(MONTH FROM fs.invoice_datetime) - EXTRACT(MONTH FROM fp.cohort_month)) AS month_index
    FROM fact_sales fs JOIN first_purchase fp USING (customer_id)
), counts AS (
    SELECT cohort_month, month_index, COUNT(*) AS active
    FROM activity GROUP BY cohort_month, month_index
)
SELECT TO_CHAR(cohort_month, 'YYYY-MM') AS cohort,
       MAX(active) FILTER (WHERE month_index = 0) AS cohort_size,
       ROUND(100.0 * MAX(active) FILTER (WHERE month_index = 1) / MAX(active) FILTER (WHERE month_index = 0), 1) AS m1,
       ROUND(100.0 * MAX(active) FILTER (WHERE month_index = 2) / MAX(active) FILTER (WHERE month_index = 0), 1) AS m2,
       ROUND(100.0 * MAX(active) FILTER (WHERE month_index = 3) / MAX(active) FILTER (WHERE month_index = 0), 1) AS m3,
       ROUND(100.0 * MAX(active) FILTER (WHERE month_index = 6) / MAX(active) FILTER (WHERE month_index = 0), 1) AS m6
FROM counts
GROUP BY cohort_month
ORDER BY cohort_month
LIMIT 13;

-- Q11. RFM scoring in SQL (cross-check against the Python segmentation)
WITH base AS (
    SELECT fs.customer_id,
           DATE '2011-12-10' - MAX(fs.invoice_datetime)::date AS recency_days,
           COUNT(DISTINCT fs.invoice_no)                     AS frequency,
           SUM(fs.line_value)                                AS gross
    FROM fact_sales fs WHERE fs.customer_id <> 0 GROUP BY fs.customer_id
), with_net AS (
    SELECT b.*, GREATEST(b.gross - COALESCE(r.ret, 0), 0) AS monetary
    FROM base b
    LEFT JOIN (SELECT customer_id, SUM(line_value) AS ret FROM fact_returns GROUP BY customer_id) r USING (customer_id)
), scored AS (
    SELECT *,
           6 - NTILE(5) OVER (ORDER BY recency_days, customer_id)   AS r,
           NTILE(5) OVER (ORDER BY frequency, customer_id)          AS f,
           NTILE(5) OVER (ORDER BY monetary, customer_id)           AS m
    FROM with_net
), segmented AS (
    SELECT *, CASE
        WHEN r >= 5 AND f >= 4 THEN 'Champions'
        WHEN r BETWEEN 3 AND 4 AND f >= 4 THEN 'Loyal Customers'
        WHEN r >= 4 AND f BETWEEN 2 AND 3 THEN 'Potential Loyalists'
        WHEN r = 5 AND f = 1 THEN 'New Customers'
        WHEN r = 4 AND f = 1 THEN 'Promising'
        WHEN r = 3 AND f = 3 THEN 'Need Attention'
        WHEN r = 3 AND f <= 2 THEN 'About to Sleep'
        WHEN r <= 2 AND f = 5 THEN 'Can''t Lose Them'
        WHEN r <= 2 AND f BETWEEN 3 AND 4 THEN 'At Risk'
        ELSE 'Hibernating' END AS segment_sql
    FROM scored
)
SELECT s.segment_sql AS segment,
       COUNT(*) AS customers,
       ROUND(SUM(s.monetary), 0) AS net_revenue,
       ROUND(100.0 * SUM(s.monetary) / SUM(SUM(s.monetary)) OVER (), 1) AS revenue_share_pct,
       ROUND(100.0 * AVG((s.segment_sql = ci.segment)::int), 1) AS pct_matching_python
FROM segmented s JOIN customer_insights ci USING (customer_id)
GROUP BY s.segment_sql
ORDER BY net_revenue DESC;

-- Q12. Segment x churn-risk matrix (model output joined back to the warehouse)
SELECT segment,
       COUNT(*) FILTER (WHERE risk_tier = 'High')          AS high_risk,
       COUNT(*) FILTER (WHERE risk_tier = 'Medium')        AS medium_risk,
       COUNT(*) FILTER (WHERE risk_tier = 'Low')           AS low_risk,
       COUNT(*) FILTER (WHERE risk_tier = 'Lapsed (>12m)') AS lapsed,
       ROUND(SUM(revenue_at_risk_90d), 0)                  AS revenue_at_risk_90d
FROM customer_insights
GROUP BY segment
ORDER BY revenue_at_risk_90d DESC NULLS LAST;

-- Q13. Campaign call list: Tier 1 customers, highest expected recovery first
SELECT ci.customer_id, dc.home_country, ci.segment, ci.risk_tier,
       ROUND(ci.churn_probability, 3) AS churn_probability,
       ci.annual_value, ci.expected_recovery, ci.recommended_action
FROM customer_insights ci JOIN dim_customer dc USING (customer_id)
WHERE ci.campaign_tier LIKE 'Tier 1%'
ORDER BY ci.expected_recovery DESC
LIMIT 15;

-- Q14. Campaign summary by tier
SELECT campaign_tier,
       COUNT(*) AS customers,
       ROUND(SUM(revenue_at_risk_90d), 0) AS revenue_at_risk_90d,
       ROUND(SUM(expected_recovery), 0)   AS expected_recovery
FROM customer_insights
GROUP BY campaign_tier
ORDER BY expected_recovery DESC;
