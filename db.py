from concurrent.futures import ThreadPoolExecutor
import clickhouse_connect
from config import CLICKHOUSE_HOST, CLICKHOUSE_DB


# connect directly to database
client = clickhouse_connect.get_client(
    host=CLICKHOUSE_HOST,
    database=CLICKHOUSE_DB
)

# parallel insert workers
executor = ThreadPoolExecutor(max_workers=4)


def setup_database():

    # create database
    client.command(f"CREATE DATABASE IF NOT EXISTS {CLICKHOUSE_DB}")

    # create table
    client.command(f"""
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
                ],
                settings={
                    "async_insert": 1,
                    "wait_for_async_insert": 0
                }
            )

        except Exception as e:
            print("DB ERROR:", e)

    executor.submit(task)
