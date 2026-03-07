import re

def parse_line(line):

    parts=line.strip().split()

    if len(parts)<2:
        return None

    try:
        user_id=int(parts[0])
    except:
        return None

    username=parts[1] if len(parts)>1 else ""
    first_name=parts[2] if len(parts)>2 else ""
    last_name=parts[3] if len(parts)>3 else ""

    phone=""
    status=""

    linked_usernames=[]
    extra_ids=[]

    for p in parts:

        if p.startswith("@"):
            linked_usernames.append(p)

        if p=="recently":
            status="recently"

        if re.fullmatch(r"[0-9]{10,12}",p):
            phone=p

        if re.fullmatch(r"[0-9]{6,}",p):
            try:
                num=int(p)
                if num!=user_id:
                    extra_ids.append(num)
            except:
                pass

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
