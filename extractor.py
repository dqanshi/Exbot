import subprocess
import os


def extract_stream(archive, password=""):

    cmd = [
        "7z",
        "x",
        archive,
        "-so",
        "-bd",
        "-mmt=on"
    ]

    if password:
        cmd.append(f"-p{password}")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    return process


def extract_to_disk(archive, password=""):

    output_dir = "downloads"

    cmd = [
        "7z",
        "x",
        archive,
        "-y",
        f"-o{output_dir}",
        "-mmt=on"
    ]

    if password:
        cmd.append(f"-p{password}")

    subprocess.run(cmd, check=True)

    for f in os.listdir(output_dir):

        if f.endswith(".txt") or f.endswith(".csv"):
            return os.path.join(output_dir, f)

    return None
