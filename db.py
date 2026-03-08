from clickhouse_driver import Client
from config import CLICKHOUSE_HOST, CLICKHOUSE_DB
import time

client = None


def connect():
    global client
    client = Client(host=CLICKHOUSE_HOST)
    print("[DB] connected to ClickHouse")


connect()


def get_row_count():
    result = client.execute(f"SELECT count() FROM {CLICKHOUSE_DB}.users")
    return result[0][0]


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

    global client

    if not rows:
        return True

    while True:

        try:

            print(f"[DB] inserting batch {len(rows)}")

            client.execute(
                f"INSERT INTO {CLICKHOUSE_DB}.users VALUES",
                rows
            )

            print("[DB] insert success")

            return True

        except Exception as e:

            print("[DB] connection error:", e)
            print("[DB] reconnecting...")

            time.sleep(2)

            try:
                connect()
            except:
                pass
