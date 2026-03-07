from concurrent.futures import ThreadPoolExecutor
import clickhouse_connect
from config import CLICKHOUSE_HOST,CLICKHOUSE_DB

client=clickhouse_connect.get_client(
    host=CLICKHOUSE_HOST,
    database=CLICKHOUSE_DB
)

executor=ThreadPoolExecutor(max_workers=4)

def insert_rows(rows):

    if not rows:
        return

    def task():

        try:
            client.insert(
                "users",
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
            print("DB ERROR:",e)

    executor.submit(task)
