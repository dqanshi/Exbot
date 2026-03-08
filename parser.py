def insert_rows(rows):
    if not rows:
        return

    client.execute(
        "INSERT INTO telegram.users FORMAT TSV",
        "\n".join(r[0] for r in rows)
    )
