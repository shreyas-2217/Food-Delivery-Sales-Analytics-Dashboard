-- 02_monthly_revenue_trend.sql
-- BUSINESS QUESTION: How does revenue move month to month?
-- TECHNIQUE: Window function LAG() compares each month with the previous month.
-- TABLE: orders(..., OrderDate TEXT 'YYYY-MM-DD', Revenue)

WITH monthly AS (
    SELECT
        strftime('%Y-%m', OrderDate) AS month,
        SUM(Revenue) AS revenue,
        COUNT(*) AS records,
        COUNT(DISTINCT Restaurant) AS active_restaurants
    FROM orders
    GROUP BY month
)
SELECT
    month,
    ROUND(revenue, 2) AS revenue,
    records,
    active_restaurants,
    ROUND(LAG(revenue) OVER (ORDER BY month), 2) AS prev_month_revenue,
    ROUND(
        100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
        / NULLIF(LAG(revenue) OVER (ORDER BY month), 0),
        2
    ) AS mom_growth_pct
FROM monthly
ORDER BY month;
