-- 06_churn.sql
-- BUSINESS QUESTION: Which restaurants have gone inactive?
-- DEFINITION: A restaurant is flagged inactive if it has no record in the
-- 90 days before the latest OrderDate in the dataset.
-- The Swiggy file has no CustomerID, so outlet recency replaces customer churn.
-- The same 90-day window technique is used.

WITH bounds AS (
    SELECT MAX(date(OrderDate)) AS max_date FROM orders
),
last_seen AS (
    SELECT
        Restaurant,
        City,
        MAX(date(OrderDate)) AS last_date,
        COUNT(*) AS lifetime_records,
        SUM(Revenue) AS lifetime_revenue
    FROM orders
    GROUP BY Restaurant, City
)
SELECT
    Restaurant,
    City,
    last_date AS last_seen_date,
    CAST(julianday((SELECT max_date FROM bounds)) - julianday(last_date) AS INTEGER) AS days_since_last,
    lifetime_records,
    ROUND(lifetime_revenue, 2) AS lifetime_revenue,
    CASE
        WHEN last_date < date((SELECT max_date FROM bounds), '-90 days')
        THEN 'inactive' ELSE 'active'
    END AS status
FROM last_seen
ORDER BY days_since_last DESC;

-- Inactivity rate (one number for the README):
-- WITH bounds AS (SELECT MAX(date(OrderDate)) AS max_date FROM orders),
-- last_seen AS (SELECT Restaurant, City, MAX(date(OrderDate)) AS last_date FROM orders GROUP BY Restaurant, City)
-- SELECT
--   COUNT(*) AS total_outlets,
--   SUM(CASE WHEN last_date < date((SELECT max_date FROM bounds), '-90 days') THEN 1 ELSE 0 END) AS inactive,
--   ROUND(100.0 * SUM(CASE WHEN last_date < date((SELECT max_date FROM bounds), '-90 days') THEN 1 ELSE 0 END) / COUNT(*), 2) AS inactive_pct
-- FROM last_seen;
