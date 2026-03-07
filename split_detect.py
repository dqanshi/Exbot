def find_archive_start(files):

    for f in files:

        if f.endswith(".001"):
            return f

        if ".part1.rar" in f:
            return f

        if f.endswith(".7z"):
            return f

    return files[0]
