from concurrent.futures import ThreadPoolExecutor
from clickhouse_driver import Client
from config import CLICKHOUSE_HOST, CLICKHOUSE_DB

client = Client(host=CLICKHOUSE_HOST)

executor = ThreadPoolExecutor(max_workers=4)


def setup_database():

    client.execute(f"CREATE DATABASE IF NOT EXISTS {CLICKHOUSE_DB}")

    client.execute(f"""
    CREATE TABLE IF NOT EXISTS {CLICKHOUSE_DB}.users
    (
        user_id UInt64,
        username String,
        first_name String,
        last_name String,
        phone String,
        status String,
        linked_usernames Array(String),
        extra_ids Array(UInt64),
        raw_line String
    )
    ENGINE = MergeTree()
    ORDER BY user_id
    """)


def insert_rows(rows):

    if not rows:
        return

    def task():

        try:

            print(f"[DB] inserting batch {len(rows)}")

            client.execute(
                f"INSERT INTO {CLICKHOUSE_DB}.users VALUES",
                rows,
                types_check=True
            )

            print("[DB] insert success")

        except Exception as e:

            print("DB ERROR:", e)

    executor.submit(task)
