from clickhouse_driver import Client
from config import CLICKHOUSE_HOST, CLICKHOUSE_DB
import time

client = None


def connect():
    global client
    client = Client(host=CLICKHOUSE_HOST)
    print("[DB] connected to ClickHouse")


connect()


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
        return

    while True:

        try:

            print(f"[DB] inserting batch {len(rows)}")

            client.execute(
                f"INSERT INTO {CLICKHOUSE_DB}.users VALUES",
                rows
            )

            print("[DB] insert success")

            break

        except Exception as e:

            print("[DB] connection error:", e)
            print("[DB] reconnecting...")

            time.sleep(5)

            try:
                connect()
            except:
                pass
