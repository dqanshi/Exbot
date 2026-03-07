def parse_line(line):

    line = line.strip()

    if not line:
        return None

    parts = line.split()

    if len(parts) < 2:
        return None

    try:
        user_id = int(float(parts[0]))
    except:
        return None

    username = parts[1] if len(parts) > 1 else ""
    first_name = parts[2] if len(parts) > 2 else ""
    last_name = parts[3] if len(parts) > 3 else ""

    phone = ""
    status = ""

    linked_usernames = []
    extra_ids = []

    for p in parts:

        if p.startswith("@"):
            linked_usernames.append(p)

        elif p.isdigit() and len(p) > 6:
            extra_ids.append(int(p))

        elif "recent" in p or "online" in p:
            status = p

    return (
        user_id,
        username,
        first_name,
        last_name,
        phone,
        status,
        linked_usernames,
        extra_ids,
        line
    )
