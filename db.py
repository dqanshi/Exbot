from clickhouse_driver import Client
from config import CLICKHOUSE_HOST, CLICKHOUSE_DB

client = Client(host=CLICKHOUSE_HOST)


def setup_database():

    client.execute(f"CREATE DATABASE IF NOT EXISTS {CLICKHOUSE_DB}")

    client.execute(f"""
    CREATE TABLE IF NOT EXISTS {CLICKHOUSE_DB}.users
    (
        raw_line String
    )
    ENGINE = MergeTree()
    ORDER BY tuple()
    """)


def insert_rows(rows):

    if not rows:
        return

    try:

        print(f"[DB] inserting batch {len(rows)}")

        client.execute(
            f"INSERT INTO {CLICKHOUSE_DB}.users VALUES",
            rows
        )

        print("[DB] insert success")

    except Exception as e:

        print("DB ERROR:", e)
