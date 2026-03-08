import subprocess

def extract_stream(archive, password=""):

    # find internal file name
    list_cmd = ["7z", "l", archive]

    result = subprocess.run(
        list_cmd,
        capture_output=True,
        text=True
    )

    lines = result.stdout.splitlines()

    target_file = None

    for l in lines:
        if ".txt" in l or ".csv" in l:
            target_file = l.split()[-1]
            break

    if not target_file:
        raise Exception("No txt/csv file inside archive")

    cmd = [
        "7z",
        "x",
        archive,
        target_file,
        "-so",
        "-bd",
        "-mmt=on"
    ]

    if password:
        cmd.append(f"-p{password}")

    print("Running:", " ".join(cmd))

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    return process
