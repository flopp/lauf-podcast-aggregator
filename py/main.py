#!/usr/bin/env python

# Copyright 2018 Florian Pigorsch. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import argparse
import os
from aggregator import Aggregator


def main() -> None:
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument(
        "--cache-dir", dest="cache_dir", metavar="DIR", type=str, default=".cache"
    )
    args_parser.add_argument(
        "--export-dir", dest="export_dir", metavar="DIR", type=str, default=".export"
    )
    args_parser.add_argument(
        "--templates-dir",
        dest="templates_dir",
        metavar="DIR",
        type=str,
        default="templates",
    )
    args_parser.add_argument("--base-url", dest="base_url", metavar="URL", type=str)
    args_parser.add_argument(
        "--podcasts-json",
        dest="podcasts_json",
        metavar="FILE",
        type=str,
        default="podcasts.json",
    )
    args_parser.add_argument("--clear-cache", dest="clear_cache", action="store_true")
    args_parser.add_argument("--keep-feeds", dest="keep_feeds", action="store_true")
    args = args_parser.parse_args()

    a = Aggregator(
        podcasts_json=args.podcasts_json,
        cache_dir=args.cache_dir,
        export_dir=args.export_dir,
        templates_dir=args.templates_dir,
        base_url=args.base_url
        if args.base_url
        else "file://{}".format(os.path.abspath(args.export_dir)),
    )
    if args.clear_cache:
        a.clear_cache()
    a.sync(keep_feeds=args.keep_feeds)
    a.export()


if __name__ == "__main__":
    main()
