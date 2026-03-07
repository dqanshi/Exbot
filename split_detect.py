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

    numbers=[]

    for f in files:

        match=re.search(r"\.(\d+)$",f)

        if match:
            numbers.append(int(match.group(1)))

    if not numbers:
        return False

    numbers.sort()

    for i,n in enumerate(numbers,start=1):

        if n!=i:
            return False

    return True
