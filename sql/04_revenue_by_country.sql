-- 04_revenue_by_country.sql
-- BUSINESS QUESTION: Which cities contribute the most revenue?
-- File name is kept for compatibility; it analyses City rather than Country.
-- TABLE: orders(..., City, State, Revenue, Restaurant)

WITH city_stats AS (
    SELECT
        City,
        State,
        SUM(Revenue) AS revenue,
        COUNT(*) AS records,
        COUNT(DISTINCT Restaurant) AS restaurants
    FROM orders
    GROUP BY City, State
),
grand_total AS (
    SELECT SUM(Revenue) AS total_revenue FROM orders
)
SELECT
    c.City,
    c.State,
    ROUND(c.revenue, 2) AS revenue,
    c.records,
    c.restaurants,
    ROUND(100.0 * c.revenue / g.total_revenue, 2) AS pct_of_revenue,
    ROUND(c.revenue / NULLIF(c.records, 0), 2) AS avg_order_value
FROM city_stats c
CROSS JOIN grand_total g
ORDER BY c.revenue DESC;
