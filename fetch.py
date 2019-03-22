#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
import calendar
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from xml.sax.saxutils import escape, quoteattr
import feedparser
import _strptime


if sys.version_info.major < 3:
    import sys
    reload(sys)
    sys.setdefaultencoding('utf8')


os.chdir(os.path.join(os.environ["HOME"], ".local/share/feedranger"))
DEVNULL = open(os.devnull, 'w')


def fromfile(name, dir):
    path = dir + name
    if os.path.isfile(path):
        with open(path, "r") as f:
            return f.read().strip()
    else:
        return None


def tofile(name, string, dir):
    path = dir + name
    if string:
        with open(path, "w") as f:
            print(string, file=f)
    elif os.path.isfile(path):
        os.remove(path)


class Fetcher():
    fetched_count = 0
    feed_count = None
    time_format = "%Y-%m-%d %H:%M:%S UTC"

    def __init__(self, name, commands, redirect=False):
        try:
            now = time.gmtime()
            self.feedname = name
            self.dir = name + "/"
            if not os.path.exists(self.dir):
                os.makedirs(self.dir)
            tofile(".fetch_started", time.strftime(self.time_format, now),
                   self.dir)
            for command in commands:
                if command.startswith("url:"):
                    try:
                        UrlCommand(self.dir, command.split("url:", 1)[1], redirect)
                    except FeedParseException:
                        return
                elif command.startswith("shellcondition:"):
                    try:
                        ShellConditionCommand(self.dir, command.split("shellcondition:", 1)[1])
                    except ConditionFailed:
                        return
                elif command.startswith("shell:"):
                    ShellCommand(self.dir, command.split("shell:", 1)[1])

            tofile(".fetch_completed", time.strftime(self.time_format, now),
                   self.dir)
        finally:
            # Set mtime on directory so ranger refreshes its view
            os.utime(self.dir, None)
            Fetcher.fetched_count += 1
            print("({}/{}) {}".format(Fetcher.fetched_count,
                                      Fetcher.feed_count, self.dir))

class ShellCommand():
    def __init__(self, dir, cmd):
        self.dir = dir
        self.cmd = cmd
        subprocess.Popen(self.cmd,
                         shell=True,
                         cwd=self.dir,
                         stderr=DEVNULL,
                         stdout=DEVNULL)


class ConditionFailed(Exception):
    pass


class ShellConditionCommand():
    def __init__(self, dir, cmd):
        self.dir = dir
        self.cmd = cmd
        process = subprocess.Popen(self.cmd,
                         shell=True,
                         cwd=self.dir,
                         stderr=DEVNULL,
                         stdout=DEVNULL)
        process.wait()
        if process.returncode != 0:
            print("{}: Exit code {} returned by {}"
                  .format(self.dir, process.returncode, self.cmd))
            raise ConditionFailed


class UrlCommand():
    time_format = Fetcher.time_format
    def __init__(self, dir, url, redirect=False):
        self.feedname = dir
        self.dir = dir + "/"
        self.feedurl = url
        self.redirect = redirect
        self.parse()

    def parse(self):

        def create_entry_filename(feedentry):
            title = feedentry.get("title", "")
            filename = (title[:97] + "...") if len(title) > 100 else title
            # Files can't have / in their name
            filename = filename.replace("/", "⁄")
            # Remove dots to prevent file extension analysis
            filename = filename.replace(".", "．")
            return filename

        def create_entry_html(feedentry, feed):
            title = feedentry.get("title", "")
            link = feedentry.get("link", "missing from feed")
            content_objs = feedentry.get("content", [])
            if len(content_objs) == 0 and hasattr(feedentry, "summary_detail"):
                content_objs.append(feedentry.summary_detail)
            if len(content_objs) > 1:
                types = set(map(lambda c:c.type, content_objs))
                if "text/html" in types and "text/plain" in types:
                    content_objs = [c for c in content_objs if c.type ==
                                    "text/html"]
            output = (
"""<html>
    <head>
        <title>{}</title>
        <meta charset="utf-8"/>
        {}
    </head>
    <body>
        <p>
            ||||| {}
        </p>
{}
        <p>
            ||||| <a href={}>link</a>
            {}
            ||||| <a href={}>feed</a>
        </p>
    </body>
</html>"""
            ).format(
                escape(title),
                create_entry_html_redirect(feedentry),
                escape(title),
                "\n".join([o.value for o in content_objs]) \
                    if not self.redirect else "",
                quoteattr(link),
                create_entry_html_enclosure(feedentry),
                quoteattr(feed.href)
            )
            return output

        def create_entry_html_redirect(feedentry):
            if not self.redirect or not hasattr(feedentry, "link"):
                return ""
            output_redirect = '<meta http-equiv="refresh" content="0;url={}"/>' \
                .format(
                    escape(feedentry.link)
                )
            return output_redirect

        def create_entry_html_enclosure(feedentry):
            enclosures = feedentry.get("enclosures", [])
            if len(enclosures) == 0:
                return ""
            href = enclosures[0].get("href", "missing from feed")
            href_attr = quoteattr(href)
            name = escape(href.split("/")[-1])
            type = escape(enclosures[0].get("type", "unknown type"))
            length_str = enclosures[0].get("length", "")
            try:
                mib = int(length_str) / float(1<<20)
            except ValueError:
                mib = None
            output_enclosure = "||||| <a href={}>{}</a> ({}{})" \
                .format(
                    href_attr,
                    name,
                    type,
                    ", {:1.4g} MiB".format(mib) if mib is not None else ""
                )
            return output_enclosure

        http_last_modified = fromfile(".http_last_modified", self.dir)
        http_etag = fromfile(".http_etag", self.dir)
        fetch_completed_s = fromfile(".fetch_completed", self.dir)
        fetch_completed = time.strptime(fetch_completed_s, self.time_format
                                     ) if fetch_completed_s else None
        now = time.gmtime()
        # Set mtime on directory so ranger refreshes its view
        os.utime(self.dir, None)

        feed = feedparser.parse(self.feedurl,
                                   modified=http_last_modified,
                                   etag=http_etag)

        status = feed.get("status")
        if status == 301:
            print("warning(", self.feedname, "): 301 Moved Permanently")
        if hasattr(feed, "bozo_exception"):
            print("error(", self.feedname, "):", feed.bozo_exception)
            print(feed)
            raise FeedParseException
        if feed.status == 304:
            return

        for feedentry in feed.entries:
            date = (feedentry.get("published_parsed",
                    feedentry.get("created_parsed",
                    feedentry.get("updated_parsed",
                    now))))
            if fetch_completed and fetch_completed > date:
                continue
            timestamp = calendar.timegm(date)
            filename = create_entry_filename(feedentry)
            output = create_entry_html(feedentry, feed)
            tofile(filename, output, self.dir)
            os.utime(self.dir + filename, (timestamp, timestamp))

        tofile(".http_last_modified", feed.get("modified"), self.dir)
        tofile(".http_etag", feed.get("etag"), self.dir)


class FeedParseException(Exception):
    pass


def readconfig():
    path = ".config"
    if os.path.isfile(path):
        with open(path, "r") as f:
            return [l.strip() for l in f if "|" in l]
    else:
        return []


config = readconfig()
executor = ThreadPoolExecutor(max_workers=10)
futures = []
Fetcher.feed_count = len(config)

for c in config:
    split = c.split("|")
    name = split[0]
    commands = split[1:]
    redirect = "(redirect)" in name
    futures.append(executor.submit(Fetcher, name, commands, redirect))

for f in as_completed(futures):
    # Print standard output of future executions
    f.result()

