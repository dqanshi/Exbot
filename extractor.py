import subprocess

def extract_stream(archive, password=""):

    cmd = [
        "7z",
        "e",          # extract files only
        archive,
        "-so",        # stream output
        "-bd",        # disable progress
        "-bsp1",      # progress to stderr
        "-mmt=on"     # multi-thread
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
