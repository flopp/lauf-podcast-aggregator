# Copyright 2018 Florian Pigorsch. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import multiprocessing
import os
from PIL import Image, ImageFilter


class ImageScaler:
    def __init__(self, threads):
        self._threads = threads
        self._jobs = []
        self._blur_filters = {}

    def add_job(self, source_file, target_file, max_dim):
        blur_size = int(max_dim/16)
        if blur_size not in self._blur_filters:
            self._blur_filters[blur_size] = ImageFilter.GaussianBlur(blur_size)
        self._jobs.append((source_file, target_file, max_dim))

    def run(self):
        pool = multiprocessing.Pool(self._threads)
        results = [pool.apply_async(self._execute_scale_job, j) for j in self._jobs]
        for r in results:
            ok, msg = r.get()
            if not ok:
                print(msg)
        self._jobs = []

    def _execute_scale_job(self, source_file, target_file, max_dim):
        if os.path.exists(target_file):
            return True, "SCALING: cache hit {0}".format(target_file)
        if not os.path.exists(source_file):
            return False, "SCALING: failed; source missing {0}".format(source_file)
        dir = os.path.dirname(target_file)
        os.makedirs(dir, exist_ok=True)
        return self._scale_image(source_file, target_file, max_dim)

    def _scale_image(self, source_file, target_file, max_dim):
        blur_size = int(max_dim/16)
        assert(blur_size in self._blur_filters)
        # noinspection PyBroadException
        try:
            with open(source_file, "rb") as f:
                image = Image.open(f)
                (w, h) = image.size
                if min(w, h) == 0:
                    return False, 'SCALING: failed; empty image {0}'.format(source_file)

                image_rgb = Image.new('RGB', (w, h))
                image_rgb.paste(image, (0, 0))
                image = image_rgb

                small_w, small_h = max_dim, max_dim
                big_w, big_h = max_dim, max_dim
                if w >= h:
                    small_h = int((h * max_dim) / w)
                    big_w = int((w * max_dim) / h)
                else:
                    small_w = int((w * max_dim) / h)
                    big_h = int((h * max_dim) / w)

                image_small = image.resize((small_w, small_h), Image.ANTIALIAS)
                image_big = image.resize((big_w, big_h), Image.ANTIALIAS)\
                    .filter(self._blur_filters[blur_size])
                base = Image.new('RGB', (max_dim, max_dim))
                base.paste(image_big, (int((max_dim - big_w)/2), int((max_dim - big_h)/2)))
                base.paste(image_small, (int((max_dim - small_w)/2), int((max_dim - small_h)/2)))
                base.save(target_file)
                return True, 'SCALING: success {0} -> {1}'.format(source_file, target_file)
        except IOError:
            return False, 'SCALING: failed {0}'.format(source_file)
        except Exception as e:
            return False, 'SCALING: failed2 {0}; exception: {1}'.format(source_file, e)
