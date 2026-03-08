import subprocess
import os
import time

def debug(msg):
    print(f"[DEBUG {time.strftime('%H:%M:%S')}] {msg}")


def extract_stream(archive, password=""):

    debug(f"Starting stream extraction for: {archive}")

    cmd = [
        "7z",
        "x",
        archive,
        "-so",
        "-bd",
        "-mmt=2"
    ]

    if password:
        cmd.append(f"-p{password}")

    debug("Command: " + " ".join(cmd))

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=None,
        text=True,
        bufsize=1
    )

    debug("7z process started")

    return process
