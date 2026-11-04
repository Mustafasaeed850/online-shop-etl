-- The main Spark SQL queries from Notebooks 2 and 3, collected in one place.
-- The notebooks are what actually run them. Schema: workspace.mustafa_shop


-- Part 4: second load. Update the order if the order_id exists, insert it if not.
-- order_updates is a temporary view of fact_orders_incremental.parquet.
MERGE INTO workspace.mustafa_shop.fact_orders AS t
USING order_updates AS u
ON t.order_id = u.order_id
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;


-- Part 4: table history.
DESCRIBE HISTORY workspace.mustafa_shop.fact_orders;


-- Part 4: time travel, version 0 against the current version.
SELECT 'version 0' AS version, COUNT(*) AS row_count
FROM workspace.mustafa_shop.fact_orders VERSION AS OF 0
UNION ALL
SELECT 'current', COUNT(*)
FROM workspace.mustafa_shop.fact_orders;


-- Part 5: gold_category_mix, revenue share of each category by month.
-- sold_orders is a temporary view without cancelled and returned orders.
WITH monthly AS (
    SELECT month, category, SUM(amount) AS revenue, COUNT(*) AS order_count
    FROM sold_orders
    GROUP BY month, category
)
SELECT month,
       category,
       ROUND(revenue, 2) AS revenue,
       order_count,
       ROUND(revenue / SUM(revenue) OVER (PARTITION BY month), 4) AS revenue_share
FROM monthly
ORDER BY month, category;


-- Part 5, Question 1: revenue and orders for the same nine months of each year.
SELECT city,
       ROUND(SUM(CASE WHEN month BETWEEN '2025-01' AND '2025-09' THEN revenue END), 0) AS revenue_2025,
       ROUND(SUM(CASE WHEN month BETWEEN '2026-01' AND '2026-09' THEN revenue END), 0) AS revenue_2026,
       SUM(CASE WHEN month BETWEEN '2025-01' AND '2025-09' THEN order_count END) AS orders_2025,
       SUM(CASE WHEN month BETWEEN '2026-01' AND '2026-09' THEN order_count END) AS orders_2026
FROM workspace.mustafa_shop.gold_monthly_sales
GROUP BY city;


-- Part 5, Question 2: average orders per day on rainy and dry days.
SELECT city,
       is_rainy,
       COUNT(*) AS days,
       ROUND(AVG(orders_placed), 2) AS avg_orders_per_day,
       ROUND(STDDEV(orders_placed), 2) AS std_dev
FROM workspace.mustafa_shop.gold_city_weather_daily
GROUP BY city, is_rainy
ORDER BY city, is_rainy;


-- Part 5, Question 3: average order value by category.
SELECT category,
       ROUND(SUM(revenue), 0) AS revenue,
       SUM(order_count) AS order_count,
       ROUND(SUM(revenue) / SUM(order_count), 2) AS avg_order_value
FROM workspace.mustafa_shop.gold_category_mix
GROUP BY category
ORDER BY avg_order_value DESC;
