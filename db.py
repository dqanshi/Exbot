from concurrent.futures import ThreadPoolExecutor
import clickhouse_connect
from config import CLICKHOUSE_HOST, CLICKHOUSE_DB


# connect without selecting DB first
client = clickhouse_connect.get_client(host=CLICKHOUSE_HOST)

executor = ThreadPoolExecutor(max_workers=4)


def setup_database():

    # create database
    client.command(f"CREATE DATABASE IF NOT EXISTS {CLICKHOUSE_DB}")

    # create table
    client.command(f"""
    CREATE TABLE IF NOT EXISTS {CLICKHOUSE_DB}.users
    (
        user_id UInt64,

        username LowCardinality(String),
        first_name String CODEC(ZSTD(3)),
        last_name String CODEC(ZSTD(3)),

        phone String CODEC(ZSTD(3)),
        status LowCardinality(String),

        linked_usernames Array(String) CODEC(ZSTD(3)),
        extra_ids Array(UInt64),

        raw_line String CODEC(ZSTD(5))
    )
    ENGINE = MergeTree()
    ORDER BY user_id
    """)


def insert_rows(rows):

    if not rows:
        return

    def task():

        try:
            client.insert(
                f"{CLICKHOUSE_DB}.users",
                rows,
                column_names=[
                    "user_id",
                    "username",
                    "first_name",
                    "last_name",
                    "phone",
                    "status",
                    "linked_usernames",
                    "extra_ids",
                    "raw_line"
                ]
            )

        except Exception as e:
            print("DB ERROR:", e)

    executor.submit(task)
