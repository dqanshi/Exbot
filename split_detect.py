import os
import re


def is_split_archive(name):

    return bool(re.search(r"\.7z\.\d+$|\.part\d+\.rar$", name))


def get_base_name(name):

    if ".7z." in name:
        return name.split(".7z.")[0]

    if ".part" in name:
        return name.split(".part")[0]

    return name


def all_parts_present(files):

    numbers = []

    for f in files:

        name = os.path.basename(f)

        match = re.search(r"\.(\d+)$", name)

        if match:
            numbers.append(int(match.group(1)))

    if not numbers:
        return False

    numbers.sort()

    for i, n in enumerate(numbers, start=1):

        if n != i:
            return False

    return True


def find_archive_start(files):
    """
    Detect first archive file in split archives
    """

    if not files:
        return None

    for f in files:

        name = os.path.basename(f)

        # 7z split archives
        if name.endswith(".001"):
            return f

        # rar split archives
        if ".part1.rar" in name:
            return f

        # normal archive
        if name.endswith(".7z") or name.endswith(".rar"):
            return f

    return files[0]
