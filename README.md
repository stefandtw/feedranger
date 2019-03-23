![example](example.gif)


Goals
=====

* fast navigation
* extensible in both UI and feed sources


A feed is a directory, an entry is a file
=========================================

By default, feeds are stored in `~/.local/share/feedranger`. Every feed gets one subdirectory. Every feed entry is stored as a single HTML file. Name and date of these files are taken from the original feed.


Ranger as a UI
==============

Ranger is great at navigating files in various ways. It's more than suitable to navigate beween HTML files of feed entries. What's missing is a way to quickly render HTML. Terminal browsers like w3m are an option, but they can't handle the same variety of content as the popular mainstream browsers can. For that reason, feedranger opens the HTML files in a Firefox window.

Most important UI features:

* New command `:feeds_update` to fetch all feeds
* Inside the main directory, feeds display their number of unread entries
* Instantly display selected feed entry files in Firefox
* Selected files are automatically tagged as read via ranger tags
* Since this is merely a plug-in, all of your ranger customization options still apply
* Mouse support: Right click a feed directory to mark all entries as read. Right click an entry to mark it as unread. To mark all entries in the current directory as read, you can also map this to a key: `eval fm.tag_add([f.path for f in fm.thisdir.files], tag="r")`


The config file
===============

Edit `~/.local/share/feedranger/.config` and follow its examples. The file is located next to the feed directories to provide quick access to it. If you prefer to have it in `~/.config`, you can replace it with a symlink.


Extend using shell commands
===========================

Command types
-------------

There are two command types to integrate feed-specific shell commands.

1) shellcondition

Executes a shell command. If the exit code is zero, continue. If it is non-zero, stop.

Example: `My Feed|shellcondition:test ! $(find .fetch_completed -mmin -60)|url:http://myfeed`

This example will execute `test ! $(find .fetch_completed -mmin -60)` before fetching from a url. This specific shell command checks if there is a `.fetch_completed` file younger than 60 minutes. Since this file is automatically generated by feedranger, the command can prevent a feed to be fetched more often than necessary.

2) shell

Executes a shell command. The exit code is ignored.

Example: `My Feed|url:http://myfeed|shell:rm *{F,f}ootball*|shell:rm *{W,w}eather*`

This example deletes entries that have football or weather in their names. The commands are executed in the order they are specified.

Some ideas as to what shell commands could do
---------------------------------------------

* Prevent certain feeds to be fetched to often
* Delete entries you don't care about, either by file name or content
* Provide your own feed source instead of a normal RSS/Atom feed
  * Place a shell script in the specific feed's directory and call it in your .config
  * The script simply needs to create new files which will be treated as feed entries
  * The files may be text, html or whatever your browser can handle
* Post-process entries
* Delete old entries before fetching new ones


Installation
============

* `git clone https://github.com/stefandtw/feedranger.git`
* `cd feedranger`
* `install -Dm644 example.config ~/.local/share/feedranger/.config`
* `install -Dm644 ranger_plugin_feedranger.py ~/.config/ranger/plugins/`
* `sudo install fetch.py /usr/bin/feedranger_fetch`
* `vim ~/.local/share/feedranger/.config` to set up your feeds
* `sudo pip install feedparser`
* if using python 2.7: `sudo pip install futures`
* `firefox -P feedranger` (To create a separate firefox profile. If a dialog pops up, you may have to create the profile in there. Then select the feedranger profile to start Firefox.)
* In Firefox, about:config, set to 1: `browser.link.open_newwindow.override.external`
* In Firefox, about:config, set to true: `browser.tabs.loadDivertedInBackground`

In ranger, cd to `~/.local/share/feedranger` and call `:feeds_update`


Dependencies
============

* [ranger](https://github.com/ranger/ranger)
* [feedparser](https://pypi.org/project/feedparser/)
* firefox
* Python 3.1+, or Python 2.7 with [futures](https://pypi.org/project/futures/)

