-- 03_top_products.sql
-- BUSINESS QUESTION: Which 10 dishes drive the most revenue?
-- TABLE: orders(..., Item, Category, Restaurant, Price, Rating, Revenue)
-- Each row is one order line with quantity of 1, so units sold equals record count.

WITH item_stats AS (
    SELECT
        Item,
        Category,
        COUNT(*) AS times_ordered,
        COUNT(DISTINCT Restaurant) AS restaurants_offering,
        AVG(Rating) AS avg_rating,
        SUM(Revenue) AS revenue
    FROM orders
    GROUP BY Item, Category
)
SELECT
    Item,
    Category,
    times_ordered,
    restaurants_offering,
    ROUND(avg_rating, 2) AS avg_rating,
    ROUND(revenue, 2) AS revenue,
    ROUND(100.0 * revenue / SUM(revenue) OVER (), 3) AS pct_of_revenue
FROM item_stats
ORDER BY revenue DESC
LIMIT 10;
