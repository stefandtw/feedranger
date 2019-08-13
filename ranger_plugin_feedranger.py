# Plug-in based on ranger 1.9.3
#
# This plugin changes ranger's behaviour when in the feedranger directory.

from __future__ import (absolute_import, division, print_function)
import subprocess
import os
import time
from threading import Thread
import ranger.api
from ranger.api import register_linemode
from ranger.api.commands import Command
from ranger.core.linemode import LinemodeBase
from ranger.container.directory import Directory
from ranger.container.file import File
from ranger.gui.widgets.browsercolumn import BrowserColumn


dirrec = ".local/share/feedranger"
dirpath = os.path.join(os.environ["HOME"], dirrec)
configpath = dirpath + "/.config"
fetchbin = "feedranger_fetch"
refresh_timeout = 20
DEVNULL = open(os.devnull, 'w')
 

class feeds_update(Command):

    update_start = -1
    done = None

    def execute(self):
        command = "shell -fp " + fetchbin
        feeds_update.update_start = time.time()
        feeds_update.done = False
        feeds_update.DirectoryRefresh(self.fm).start()
        self.fm.execute_console(command)

    @staticmethod
    def is_updating(dir):
        try:
            if (os.stat(dir.path + '/.fetch_started').st_mtime
                    > os.stat(dir.path + '/.fetch_completed').st_mtime):
                return True
        except:
            pass
        return False

    class DirectoryRefresh(Thread):

        def __init__(self, fm):
            self.fm = fm
            super(feeds_update.DirectoryRefresh, self).__init__()

        def run(self):
            waited = 0
            interval = 0.05
            while not feeds_update.done:
                self.refresh()
                time.sleep(interval)
                waited += interval
                interval *= 1.2
                if waited > refresh_timeout:
                    feeds_update.done = True

        def refresh(self):
            self.fm.execute_console("reload_cwd")


# Settings and signal bindings
def hook_init(fm):
    fm.execute_console("setlocal path={}$ sort feeds".format(dirrec))
    fm.execute_console("setlocal path={}/ sort mtime".format(dirrec))
    fm.execute_console("setlocal path={}/ preview_files false".format(dirrec))
    fm.execute_console("setlocal path={}/ padding_right false".format(dirrec))
    fm.execute_console("default_linemode path={} feeds".format(dirrec))
    fm.execute_console("default_linemode path={}/.+/ mtime".format(dirrec))
    # Call load() to refresh unread count
    fm.signal_bind("cd", lambda signal:
                   signal.new.load() if dirrec in signal.new.path else None)
    fm.signal_bind("move", lambda signal:
                   on_file_focus(signal.new)
                   )
    return HOOK_INIT_OLD(fm)


HOOK_INIT_OLD = ranger.api.hook_init
ranger.api.hook_init = hook_init


def on_file_focus(fsobject):
    if not fsobject:
        return
    path = fsobject.realpath

    if fsobject.is_directory:
        return
    if dirrec not in path:
        return

    if path != getattr(File, "latest_path", ""):
        # Remember path to prevent multiple calls 
        File.latest_path = path
        # Open in firefox, ignoring useless warnings
        subprocess.Popen(["firefox", "-P", "feedranger", path],
                         stderr=DEVNULL,
                         stdout=DEVNULL)
        fsobject.fm.tags.add(path, tag="r")


class FeedsLinemode(LinemodeBase):
    name = "feeds"

    def filetitle(self, file, metadata):
        return file.relative_path

    def infostring(self, file, metadata):
        if isinstance(file, Directory):
            try:
                files = [f for f in os.listdir(file.path)
                         if not f.startswith(".")
                            and (file.path + '/' + f) not in file.fm.tags]
                count = len(files)
                length_s = str(count) if count > 0 else "  "
                updating_s = " ..." if feeds_update.is_updating(file) else ""
                return length_s + updating_s
            except IOError:
                pass

        return super(FeedsLinemode, self).infostring(file, metadata)


register_linemode(FeedsLinemode)


# Right click on directory tags all files as read
# Right click on file removes tag
# TODO: Be less reliant on ranger's implementation details
def custom_click(self, event):
    if event.pressed(3):
        if self.target is None:
            pass
        elif self.target.is_directory:
            index = self.scroll_begin + event.y - self.y
            clicked_file = self.target.files[index]
            if dirrec in clicked_file.path:
                if clicked_file.is_file:
                    self.fm.tags.remove(clicked_file.path)
                elif clicked_file.is_directory:
                    files = [clicked_file.path + "/" + f
                             for f in os.listdir(clicked_file.path)
                             if not f.startswith(".")]
                    self.fm.tag_add(paths=files, tag="r")
                self.fm.execute_console("reload_cwd")
                return True
    CLICK_OLD(self, event)
CLICK_OLD = BrowserColumn.click
BrowserColumn.click = custom_click


def readconfig():
    if os.path.isfile(configpath):
        with open(configpath, "r") as f:
            return [l.strip() for l in f]
    else:
        return []


def readfeednames():
    return [c.split("|", 1)[0] for c in readconfig()]


def sort_by_config(path):
    try:
        return feednames.index(path.relative_path)
    except ValueError:
        return len(feednames)


feednames = readfeednames()
Directory.sort_dict["feeds"] = sort_by_config
