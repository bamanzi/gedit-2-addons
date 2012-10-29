# Reopen tabs plugin for Gedit

Saves opened tabs on exit and restores them on next gedit starup.

Forked from Eugene Khorev's @ <http://code.google.com/p/reopen-tabs-gedit-plugin/> and fixes some [issues](http://code.google.com/p/reopen-tabs-gedit-plugin/issues/list).

 - Restores tabs even when gedit was killed. Need testing - please report bugs.

 - Restores only existing files.

 - Doesn't have preferences - when enabled always saves current session. To close gedit without saving current session just hit `Ctrl+Q` or `File` - `Exit`.


## Installation

### Easy

This plugin is a part of [gmate](https://github.com/gmate/gmate). [Install](https://github.com/gmate/gmate#readme) gmate and you are done.

### Manual

1. Download latest source package.
2. Copy `reopen-tabs.gedit-plugin` file and `reopen-tabs` folder to `~/.gnome2/gedit/plugins/` (or `/usr/lib/gedit-2/plugins/` for system-wide installation).
3. Open (restart) Gedit.
4. Go to **Edit** - **Preferences** - **Plugins**.
5. Enable plugin.


## Translation

Currently only `reopen-tabs.gedit-plugin` needs translation. Feel free to contribute.
