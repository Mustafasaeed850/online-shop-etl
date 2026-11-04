"""Part 1 extraction as a script, so GitHub Actions can run it every day (bonus task).

Reads PG_URL and MONGO_URL from environment variables. If a secret is missing, that
source is skipped and the log says so, and the weather still runs because it needs no key.
"""
import json
import os
from datetime import date, timedelta

import pandas as pd
import requests

CHUNK_SIZE = 50_000
CITY_COORDS = {
    "Lahore": (31.55, 74.34),
    "Karachi": (24.86, 67.01),
    "Islamabad": (33.68, 73.05),
}

today = date.today().isoformat()
os.makedirs("raw", exist_ok=True)


def extract_postgres(url):
    from sqlalchemy import create_engine, text

    url = url.replace("postgres://", "postgresql://", 1).replace("postgresql://", "postgresql+psycopg2://", 1)
    engine = create_engine(url)

    customers = pd.read_sql_query(text("SELECT * FROM customers"), engine)
    customers.to_parquet(f"raw/customers_{today}.parquet", index=False)
    print(f"customers: {len(customers):,} rows")

    chunks = []
    with engine.connect().execution_options(stream_results=True) as conn:
        query = text("SELECT * FROM orders ORDER BY order_id")
        for chunk in pd.read_sql_query(query, conn, chunksize=CHUNK_SIZE):
            chunks.append(chunk)
    orders = pd.concat(chunks, ignore_index=True)
    orders.to_parquet(f"raw/orders_{today}.parquet", index=False)
    print(f"orders: {len(orders):,} rows in {len(chunks)} chunks")


def extract_mongo(url):
    from pymongo import MongoClient

    client = MongoClient(url, serverSelectionTimeoutMS=15000)
    docs = list(client["shop"]["orders"].find({}, {"_id": 0}))
    with open(f"raw/mongo_orders_{today}.json", "w") as f:
        json.dump(docs, f, default=str)
    print(f"mongo orders: {len(docs):,} documents")


def extract_weather():
    # the archive API runs a few days behind today, so stop a week back
    end_date = (date.today() - timedelta(days=7)).isoformat()
    for city, (lat, lon) in CITY_COORDS.items():
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": "2025-01-01",
            "end_date": end_date,
            "daily": "temperature_2m_max,precipitation_sum",
            "timezone": "Asia/Karachi",
        }
        response = requests.get("https://archive-api.open-meteo.com/v1/archive", params=params, timeout=60)
        response.raise_for_status()
        daily = pd.DataFrame(response.json()["daily"])
        daily.to_csv(f"raw/weather_{city.lower()}_{today}.csv", index=False)
        print(f"weather {city}: {len(daily)} days, up to {end_date}")


if __name__ == "__main__":
    pg_url = os.environ.get("PG_URL")
    mongo_url = os.environ.get("MONGO_URL")

    if pg_url:
        extract_postgres(pg_url)
    else:
        print("PG_URL is not set: skipping PostgreSQL")

    if mongo_url:
        extract_mongo(mongo_url)
    else:
        print("MONGO_URL is not set: skipping MongoDB")

    extract_weather()
    print("Files:", sorted(os.listdir("raw")))
