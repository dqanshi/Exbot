import os
import re


def find_archive_start(files):

    if not files:
        return None

    for f in files:

        name = os.path.basename(f)

        if name.endswith(".001"):
            return f

        if ".part1.rar" in name:
            return f

        if name.endswith(".7z") or name.endswith(".rar"):
            return f

    return files[0]
