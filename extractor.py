import subprocess
import os

def extract_stream(archive, password=""):

    # detect file name automatically
    filename = os.path.basename(archive)

    if ".txt.7z" in filename:
        target_file = filename.replace(".7z.001", "").replace(".7z", "")
    else:
        target_file = "telegram.txt"

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


import subprocess
import os

def extract_to_disk(archive, password=""):

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

    subprocess.run(cmd, check=True)

    # detect nested .7z
    for f in os.listdir(output_dir):

        if f.endswith(".7z"):

            nested = os.path.join(output_dir, f)

            cmd2 = [
                "7z",
                "x",
                nested,
                "-y",
                f"-o{output_dir}",
                "-bd",
                "-mmt=on"
            ]

            if password:
                cmd2.append(f"-p{password}")

            subprocess.run(cmd2, check=True)

    # find final txt/csv
    for root, dirs, files in os.walk(output_dir):

        for f in files:

            if f.endswith(".txt") or f.endswith(".csv"):
                return os.path.join(root, f)

    return None
