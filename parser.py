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

    username = parts[1]

    return (
        user_id,
        username,
        line
    )
