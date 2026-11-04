"""Builds the one-page dashboard definition on the gold tables and saves it as JSON.

Import online_shop.lvdash.json in Databricks (Dashboards, then Create from file),
or run this script to regenerate it.
"""
import json
import os

DB = "workspace.mustafa_shop"

DATASETS = {
    "kpis": f"""
        SELECT SUM(revenue) AS total_revenue,
               SUM(order_count) AS total_orders,
               SUM(revenue) / SUM(order_count) AS avg_order_value
        FROM {DB}.gold_monthly_sales""",
    "customers": f"""
        SELECT COUNT(*) AS customers
        FROM {DB}.gold_customer_features""",
    # October 2026 is left out because the data stops on the 24th, so it would look like a drop
    "monthly": f"""
        SELECT month, SUM(revenue) AS revenue
        FROM {DB}.gold_monthly_sales
        WHERE month <= '2026-09'
        GROUP BY month""",
    "city": f"""
        SELECT city, SUM(revenue) AS revenue
        FROM {DB}.gold_monthly_sales
        GROUP BY city""",
    "category": f"""
        SELECT category,
               SUM(revenue) AS revenue,
               SUM(revenue) / SUM(order_count) AS avg_order_value
        FROM {DB}.gold_category_mix
        GROUP BY category""",
    # same nine months in both years, because 2026 is not a full year
    "growth": f"""
        SELECT city,
               ROUND((SUM(CASE WHEN month BETWEEN '2026-01' AND '2026-09' THEN revenue END)
                    / SUM(CASE WHEN month BETWEEN '2025-01' AND '2025-09' THEN revenue END) - 1) * 100, 2)
                    AS revenue_growth_pct
        FROM {DB}.gold_monthly_sales
        GROUP BY city
        ORDER BY revenue_growth_pct DESC""",
    "rain": f"""
        SELECT city,
               ROUND(AVG(CASE WHEN is_rainy THEN orders_placed END), 2) AS rainy_day_orders,
               ROUND(AVG(CASE WHEN NOT is_rainy THEN orders_placed END), 2) AS dry_day_orders
        FROM {DB}.gold_city_weather_daily
        GROUP BY city
        ORDER BY city""",
}


def query(dataset, fields):
    return [{
        "name": "main_query",
        "query": {
            "datasetName": dataset,
            "fields": [{"name": f, "expression": f"`{f}`"} for f in fields],
            "disaggregated": True,
        },
    }]


def counter(name, dataset, field, title, x, width):
    return {
        "widget": {
            "name": name,
            "queries": query(dataset, [field]),
            "spec": {
                "version": 2,
                "widgetType": "counter",
                "encodings": {"value": {"fieldName": field, "displayName": title}},
                "frame": {"title": title, "showTitle": True},
            },
        },
        "position": {"x": x, "y": 2, "width": width, "height": 2},
    }


def line_chart(name, dataset, x_field, y_field, title, x_title, y_title, pos):
    return {
        "widget": {
            "name": name,
            "queries": query(dataset, [x_field, y_field]),
            "spec": {
                "version": 3,
                "widgetType": "line",
                "encodings": {
                    "x": {"fieldName": x_field, "scale": {"type": "categorical"}, "displayName": x_title},
                    "y": {"fieldName": y_field, "scale": {"type": "quantitative"}, "displayName": y_title},
                },
                "frame": {"title": title, "showTitle": True},
            },
        },
        "position": pos,
    }


def bar_chart(name, dataset, label_field, value_field, title, label_title, value_title, pos):
    # horizontal bars, largest at the top, so long city names stay readable
    return {
        "widget": {
            "name": name,
            "queries": query(dataset, [label_field, value_field]),
            "spec": {
                "version": 3,
                "widgetType": "bar",
                "encodings": {
                    "x": {"fieldName": value_field, "scale": {"type": "quantitative"}, "displayName": value_title},
                    "y": {"fieldName": label_field, "scale": {"type": "categorical", "sort": {"by": "x-reversed"}},
                          "displayName": label_title},
                },
                "frame": {"title": title, "showTitle": True},
            },
        },
        "position": pos,
    }


def table(name, dataset, columns, title, pos):
    return {
        "widget": {
            "name": name,
            "queries": query(dataset, [c for c, _ in columns]),
            "spec": {
                "version": 2,
                "widgetType": "table",
                "encodings": {"columns": [{"fieldName": c, "displayName": d} for c, d in columns]},
                "frame": {"title": title, "showTitle": True},
            },
        },
        "position": pos,
    }


layout = [
    {
        "widget": {
            "name": "heading",
            "multilineTextboxSpec": {"lines": [
                "## Online Shop Sales\n",
                "Sales exclude cancelled and returned orders. Data runs from January 2025 to 24 October 2026.",
            ]},
        },
        "position": {"x": 0, "y": 0, "width": 6, "height": 2},
    },
    counter("kpi_revenue", "kpis", "total_revenue", "Total revenue", 0, 2),
    counter("kpi_orders", "kpis", "total_orders", "Orders sold", 2, 1),
    counter("kpi_aov", "kpis", "avg_order_value", "Average order value", 3, 2),
    counter("kpi_customers", "customers", "customers", "Customers", 5, 1),
    line_chart("monthly_revenue", "monthly", "month", "revenue", "Revenue by month (to September 2026)",
               "Month", "Revenue", {"x": 0, "y": 4, "width": 6, "height": 5}),
    bar_chart("city_revenue", "city", "city", "revenue", "Revenue by city", "City", "Revenue",
              {"x": 0, "y": 9, "width": 3, "height": 6}),
    bar_chart("category_revenue", "category", "category", "revenue", "Revenue by category", "Category", "Revenue",
              {"x": 3, "y": 9, "width": 3, "height": 6}),
    table("growth_table", "growth", [("city", "City"), ("revenue_growth_pct", "Growth %")],
          "Revenue growth: Jan to Sep 2026 against 2025", {"x": 0, "y": 15, "width": 2, "height": 7}),
    table("rain_table", "rain", [("city", "City"), ("rainy_day_orders", "Rainy day"), ("dry_day_orders", "Dry day")],
          "Average orders per day: rainy and dry", {"x": 2, "y": 15, "width": 2, "height": 7}),
    table("aov_table", "category", [("category", "Category"), ("avg_order_value", "Average order value")],
          "Average order value by category", {"x": 4, "y": 15, "width": 2, "height": 7}),
]

dashboard = {
    "datasets": [
        {"name": name, "displayName": name, "queryLines": [sql.strip()]}
        for name, sql in DATASETS.items()
    ],
    "pages": [{"name": "overview", "displayName": "Overview", "pageType": "PAGE_TYPE_CANVAS", "layout": layout}],
}

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "online_shop.lvdash.json")
with open(path, "w") as f:
    json.dump(dashboard, f, indent=1)
print("wrote", path)
