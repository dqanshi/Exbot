import os
import shutil
import subprocess
from config import DOWNLOAD_DIR

DELETE_PASSWORD="an12if.."

def verify_password(p):
    return p==DELETE_PASSWORD

def wipe_database():

    try:
        subprocess.run([
            "clickhouse-client",
            "--query",
            "TRUNCATE TABLE telegram.users"
        ])
    except Exception as e:
        print("DB wipe error:",e)

def wipe_downloads():

    if not os.path.exists(DOWNLOAD_DIR):
        return

    for f in os.listdir(DOWNLOAD_DIR):

        path=os.path.join(DOWNLOAD_DIR,f)

        try:
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)
        except:
            pass

def full_wipe():

    wipe_database()
    wipe_downloads()
