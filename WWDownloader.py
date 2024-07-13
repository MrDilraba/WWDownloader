#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import time
import psutil
import signal
import threading
import json
import wget
import requests
import hashlib
from tqdm import tqdm

# config
MAX_WORKER = 8
TARGET_DIR = "D:/games/WWBeta_1.2"
RESOURCE_URL = "https://pcdownload-wangsu.aki-game.com/pcstarter/prod/game/G152/1.2.0/7hzsDZbvz4PkA59CiCxwfuUuaDN2aW57"

def process_terminate():
    psutil.Process(os.getpid()).terminate()

def mkdir(path):
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except:
            pass

MD5_CHUNK_SIZE = 8192
def md5_sum(file):
    try:
        if not os.path.exists(file):
            return ""
        with open(file, "rb") as f:
            file_hash = hashlib.md5()
            chunk = f.read(MD5_CHUNK_SIZE)
            while chunk:
                file_hash.update(chunk)
                chunk = f.read(MD5_CHUNK_SIZE)
        return file_hash.hexdigest()
    except:
        return ""

def tqdm_update(res, bar, cur, total):
    # check file size
    if total != res["size"]:
        print("\n%s: check file size failed, file size: %d, expect size: %d, file: %s" % (bar.desc, total, res["size"], res["dest"]))
        process_terminate()
    # update bar
    bar.n = cur
    bar.update()

WORKER_LOCK = threading.BoundedSemaphore(MAX_WORKER)
def resource_download(res, i, cnt):
    WORKER_LOCK.acquire()
    try:
        dest = res["dest"]
        url = RESOURCE_URL + "/zip" + dest
        file = TARGET_DIR + dest
        file_hash = md5_sum(file)
        if file_hash == res["md5"]:
            print("%3d/%d: %s exists"%(i + 1, cnt, dest))
        else:
            mkdir(os.path.dirname(file))
            tqdm_bar = tqdm(desc="%3d/%d"%(i + 1, cnt), unit="B", total=res["size"], unit_scale=True)
            wget_callback = lambda c, t, _: tqdm_update(res, tqdm_bar, c, t)
            try:
                wget.download(url, file, wget_callback)
            except:
                try:
                    tqdm_bar.desc += "+"
                    wget.download(url, file, wget_callback)
                except:
                    pass

            # check file md5
            file_hash = md5_sum(file)
            if file_hash != res["md5"]:
                print("\n%s: check file md5 failed, file md5: %s, expect md5: %s, file: %s" % (tqdm_bar.desc, file_hash, res["md5"], file))
                process_terminate()
    finally:
        WORKER_LOCK.release()

def main():
    signal.signal(signal.SIGINT, exit)
    signal.signal(signal.SIGTERM, exit)

    threads = []
    res_url = RESOURCE_URL + "/resource.json"
    res_rsp = requests.get(res_url)
    res_data = json.loads(res_rsp.content)
    res_data["resource"].sort(key = lambda i: i["size"])
    cnt = len(res_data["resource"])
    for i in range(0, cnt):
        res = res_data["resource"][i]
        thread = threading.Thread(target=resource_download, args=[res, i, cnt], daemon=True)
        thread.start()
        threads.append(thread)

    # wait all theads done
    while True:
        done = True
        for thread in threads:
            if(thread.is_alive()):
                done = False
                break
        if done:
            break
        time.sleep(0.5)
    print("\nAll done.")

if __name__ == '__main__':
    try:
        main()
    except:
        pass
