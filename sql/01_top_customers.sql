-- 01_top_restaurants.sql
-- BUSINESS QUESTION: Which 10 restaurants generate the most revenue?
-- TABLE: orders(State, City, OrderDate, Restaurant, Area, Category, Item, Price, Rating, Revenue)
-- NOTE: The Swiggy file has no CustomerID, so restaurant performance replaces customer analysis.

WITH restaurant_stats AS (
    SELECT
        Restaurant,
        City,
        COUNT(*) AS records,
        COUNT(DISTINCT Item) AS distinct_items,
        SUM(Revenue) AS revenue,
        AVG(Price) AS avg_price,
        AVG(Rating) AS avg_rating
    FROM orders
    GROUP BY Restaurant, City
)
SELECT
    Restaurant,
    City,
    records,
    distinct_items,
    ROUND(revenue, 2) AS revenue,
    ROUND(avg_price, 2) AS avg_price,
    ROUND(avg_rating, 2) AS avg_rating
FROM restaurant_stats
ORDER BY revenue DESC
LIMIT 10;
