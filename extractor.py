import subprocess

def extract_stream(archive,password=""):

    cmd=[
        "7z",
        "x",
        archive,
        "-so",
        "-bsp1",
        "-mmt=on"
    ]

    if password:
        cmd.append(f"-p{password}")

    process=subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    return process
