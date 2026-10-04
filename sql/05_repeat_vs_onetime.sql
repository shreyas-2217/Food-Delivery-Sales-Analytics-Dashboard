-- 05_repeat_vs_onetime.sql
-- BUSINESS QUESTION: Which categories and diet types drive sales?
-- File name is kept for compatibility.
-- NOTE: The Swiggy file has no CustomerID, so customer repeat analysis is not
-- possible. Category and VegType mix is used instead: it shows where demand
-- concentrates, which guides menu and stock decisions.

-- Part A: revenue by category
WITH category_stats AS (
    SELECT
        Category,
        COUNT(*) AS records,
        SUM(Revenue) AS revenue,
        AVG(Rating) AS avg_rating
    FROM orders
    GROUP BY Category
)
SELECT
    Category,
    records,
    ROUND(revenue, 2) AS revenue,
    ROUND(100.0 * revenue / SUM(revenue) OVER (), 2) AS pct_of_revenue,
    ROUND(avg_rating, 2) AS avg_rating
FROM category_stats
ORDER BY revenue DESC;

-- Part B (run separately): Veg vs Non-Veg split
-- SELECT
--     VegType,
--     COUNT(*) AS records,
--     ROUND(SUM(Revenue), 2) AS revenue,
--     ROUND(100.0 * SUM(Revenue) / (SELECT SUM(Revenue) FROM orders), 2) AS pct_of_revenue,
--     ROUND(AVG(Rating), 2) AS avg_rating
-- FROM orders
-- GROUP BY VegType
-- ORDER BY revenue DESC;
