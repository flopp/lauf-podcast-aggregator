# Copyright 2018 Florian Pigorsch. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import multiprocessing
import os
import requests


class Downloader:
    def __init__(self, threads, user_agent):
        self._threads = threads
        self._user_agent = user_agent
        self._jobs = []

    def add_job(self, url, target_file, force=False):
        self._jobs.append((url, target_file, force))

    def run(self):
        pool = multiprocessing.Pool(self._threads)
        results = [pool.apply_async(self.download_if_not_exists, j) for j in self._jobs]
        for r in results:
            ok, msg = r.get()
            if not ok:
                print(msg)
        self._jobs = []

    def download_if_not_exists(self, url, target, force):
        if force or not os.path.exists(target):
            try:
                response = requests.get(url, headers={'User-agent': self._user_agent})
                dir = os.path.dirname(target)
                os.makedirs(dir, exist_ok=True)
                with open(target, 'wb') as f:
                    f.write(response.content)
                return True, 'DOWNLOAD: success {0} -> {1}'.format(url, target)
            except IOError as e:
                return False, 'DOWNLOAD: failed {0} {1}'.format(url, e)
        else:
            return True, 'DOWNLOAD: cache hit {0}'.format(target)
