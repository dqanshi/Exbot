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
        "-mmt=on"
    ]

    if password:
        cmd.append(f"-p{password}")

    debug("Command: " + " ".join(cmd))

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    debug("7z process started")

    return process


def extract_to_disk(archive, password=""):

    debug("Fallback extraction to disk started")

    output_dir = "downloads/extracted"
    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        "7z",
        "x",
        archive,
        "-y",
        f"-o{output_dir}",
        "-bd",
        "-mmt=on"
    ]

    if password:
        cmd.append(f"-p{password}")

    debug("Running: " + " ".join(cmd))

    subprocess.run(cmd, check=True)

    debug("First extraction finished")

    for root, dirs, files in os.walk(output_dir):
        for f in files:
            if f.endswith(".txt") or f.endswith(".csv"):
                path = os.path.join(root, f)
                debug(f"Dataset detected: {path}")
                return path

    debug("No dataset found after extraction")

    return None
