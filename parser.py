def parse_line(line):

    line = line.strip()

    if not line:
        return None

    parts = line.split()

    if len(parts) < 2:
        return None

    # user id
    try:
        user_id = int(parts[0])
    except:
        try:
            user_id = int(float(parts[0]))
        except:
            return None

    username = ""
    first_name = ""
    last_name = ""
    phone = ""
    status = ""

    linked_usernames = []
    extra_ids = []

    if len(parts) > 1:
        username = parts[1]

    if len(parts) > 2:
        first_name = parts[2]

    if len(parts) > 3:
        last_name = parts[3]

    for p in parts:

        if p.startswith("@"):
            linked_usernames.append(p)

        elif p.isdigit():

            if len(p) > 9:
                extra_ids.append(int(p))

            elif len(p) >= 10 and len(p) <= 15:
                phone = p

        elif "online" in p or "recent" in p:
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
