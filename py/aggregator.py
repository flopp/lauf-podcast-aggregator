# Copyright 2018 Florian Pigorsch. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import datetime
import jinja2
import json
import os
import re
import shutil
from typing import Any, Dict, List, Optional
from podcastparser import parse as podcastparser_parse  # type: ignore
from downloader import Downloader
from imagescaler import ImageScaler


class Aggregator:
    def __init__(
        self,
        podcasts_json: str,
        cache_dir: str,
        export_dir: str,
        templates_dir: str,
        base_url: str,
    ) -> None:
        self._downloader = Downloader(
            4, "Lauf Podcast Aggregator, https://lauf-podcasts.flopp.net/"
        )
        self._imagescaler = ImageScaler(4)
        self._podcasts_json_file = podcasts_json
        self._cache_dir = cache_dir
        self._export_dir = export_dir
        self._base_url = base_url
        self._podcasts: List[Dict[str, Any]] = []
        self._jinja = jinja2.Environment(
            loader=jinja2.FileSystemLoader(templates_dir), autoescape=True
        )
        self._jinja.filters["timestamp2date"] = self.format_date
        self._jinja.filters["timestamp2datetime"] = self.format_datetime
        self._jinja.filters["formatseconds"] = self.format_seconds
        self._jinja.globals["now"] = datetime.datetime.now().timestamp()
        self._jinja.globals["base_url"] = base_url

    def format_date(self, value: Optional[float]) -> str:
        if value is None:
            return "n/a"
        d = datetime.datetime.fromtimestamp(value)
        return d.strftime("%F")

    def format_datetime(self, value: Optional[float]) -> str:
        if value is None:
            return "n/a"
        d = datetime.datetime.fromtimestamp(value)
        return d.strftime("%F %T")

    def format_seconds(self, value: Optional[int]) -> str:
        if value is None:
            return "n/a"
        if value == 0:
            return "n/a"
        d = datetime.timedelta(seconds=value)
        return str(d)

    def clear_cache(self) -> None:
        if os.path.isdir(self._cache_dir):
            shutil.rmtree(self._cache_dir)

    def sync(self, keep_feeds: bool = False) -> None:
        with open(self._podcasts_json_file, "r") as f:
            self._podcasts = json.load(f)
        # filter podcasts without title or feed url
        self._podcasts = [p for p in self._podcasts if ("title" in p) and ("feed" in p)]
        for podcast in self._podcasts:
            title = podcast["title"]
            feed_url = podcast["feed"]
            sanitized_title = self.sanitize(title)
            podcast["sanitized_title"] = sanitized_title
            dir = "{}/{}".format(self._cache_dir, sanitized_title)
            podcast["raw_dir"] = dir
            feed_file = "{}/feed".format(dir)
            podcast["feed_file"] = feed_file
            os.makedirs(dir, exist_ok=True)
            self._downloader.add_job(feed_url, feed_file, force=(not keep_feeds))
        self._downloader.run()
        # filter podcasts with non-existent feed file
        self._podcasts = [p for p in self._podcasts if os.path.exists(p["feed_file"])]
        for podcast in self._podcasts:
            podcast["skip"] = False
            feed_url = podcast["feed"]
            feed_file = podcast["feed_file"]
            try:
                with open(feed_file, "r") as f:
                    podcast["data"] = podcastparser_parse(feed_url, f)
            except Exception:
                podcast["skip"] = True
                continue
            # determine latest publish date
            last_publish = None
            for episode in podcast["data"]["episodes"]:
                if not last_publish or episode["published"] > last_publish:
                    last_publish = episode["published"]
            podcast["last_publish"] = last_publish
            if last_publish is None:
                print("no last publish date: {}".format(podcast["title"]))
            # format descriptions
            podcast["data"]["description_formatted"] = self.format_description(
                podcast["data"]["description"]
            )
            for episode in podcast["data"]["episodes"]:
                episode["description_formatted"] = self.format_description(
                    episode["description"]
                )
            # determine cover image
            cover_url = None
            if "cover_url" in podcast:
                cover_url = podcast["cover_url"]
            if not cover_url and ("cover_url" in podcast["data"]):
                cover_url = podcast["data"]["cover_url"]
            if cover_url:
                dir = "{}/{}".format(self._cache_dir, podcast["sanitized_title"])
                cover_file = "{}/cover".format(dir)
                self._downloader.add_job(cover_url, cover_file)
        self._downloader.run()
        # filter podcasts with skip attribute
        self._podcasts = [p for p in self._podcasts if not p["skip"]]
        # sort by reversed 'last_publish' timestamp
        self._podcasts.sort(
            key=lambda x: -x["last_publish"] if x["last_publish"] is not None else 0
        )

    def format_description(self, description: str) -> str:
        re_newline = re.compile(r"(\n)")
        re_divider = re.compile(r"((?:---+)|(?:\*\*\*+)|(?:\+\+\++))")
        re_link = re.compile(r"(https?://[A-Za-z0-9/.=\?&_\-]+)")
        s = description
        s = re_newline.sub(r"<br />", s)
        s = re_divider.sub(r"<br />\1<br />", s)
        s = re_link.sub(r'<a href="\1" rel="nofollow" target="_blank">\1</a>', s)
        return s

    def export(self) -> None:
        for podcast in self._podcasts:
            self._imagescaler.add_job(
                "{}/{}/cover".format(self._cache_dir, podcast["sanitized_title"]),
                "{}/{}/cover.jpg".format(self._export_dir, podcast["sanitized_title"]),
                512,
            )
        self._imagescaler.run()
        self.export_info()
        self.export_impressum()
        self.export_index()
        self.export_sitemap()
        for podcast in self._podcasts:
            self.export_podcast(podcast)
        self._imagescaler.run()

    def export_info(self) -> None:
        os.makedirs(self._export_dir, exist_ok=True)
        with open("{}/info.html".format(self._export_dir), "w") as f:
            template = self._jinja.get_template("info.html")
            f.write(template.render())

    def export_impressum(self) -> None:
        os.makedirs(self._export_dir, exist_ok=True)
        with open("{}/impressum.html".format(self._export_dir), "w") as f:
            template = self._jinja.get_template("impressum.html")
            f.write(template.render())

    def export_index(self) -> None:
        os.makedirs(self._export_dir, exist_ok=True)
        with open("{}/index.html".format(self._export_dir), "w") as f:
            template = self._jinja.get_template("index.html")
            f.write(template.render(podcasts=self._podcasts))

    def export_sitemap(self) -> None:
        os.makedirs(self._export_dir, exist_ok=True)
        with open("{}/sitemap.xml".format(self._export_dir), "w") as f:
            template = self._jinja.get_template("sitemap.xml")
            f.write(template.render(podcasts=self._podcasts))

    def export_podcast(self, podcast: Dict[str, Any]) -> None:
        dir = "{}/{}".format(self._export_dir, podcast["sanitized_title"])
        os.makedirs(dir, exist_ok=True)
        with open("{}/index.html".format(dir), "w") as f:
            template = self._jinja.get_template("podcast.html")
            f.write(
                template.render(podcast=podcast, episodes=podcast["data"]["episodes"])
            )

    def sanitize(self, s: str) -> str:
        return re.sub(r"\W+", "-", s).lower()
