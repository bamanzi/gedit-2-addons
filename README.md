# Collection of plugins, templates, themes for Gedit-2 #

Here are some nice plugins and themes I collected for Gedit-2.  

The goals of this repo:

* collection plugins, templates & themes for [Gedit-2](https://projects.gnome.org/gedit/)
* make sure them work on Pluma, [the MATE desktop](http://mate-desktop.org/)) fork
* make most of them work on [Gedit-2 for Windows](https://live.gnome.org/Gedit/Windows)
* make gedit a lightweight Python editor


## Installtion ##

* for gedit-2: put this repo into `~/.gnome2/gedit/`
* for pluma:   put this repo into `~/.config/pluma/`
* for gedit-2 for windows: put this repo into %APPDATA%/gedit/
  (on Windows XP, %APPDATA% should be `C:\Documents and Settings\<username>\Application Data\`,
   on Windows Vista & 7, %APPDATA% should be `C:\Users\<username>\AppData\Roaming\`.)
  and move contents in _windows to gedit install dir
  
## Some Useful Links ##

* [Gedit/Plugins - GNOME Live!](https://live.gnome.org/Gedit/Plugins) Plugin List on gnome.org
* [GeditPlugins - GNOME Live!](https://live.gnome.org/GeditPlugins) Plugins in package gedit-plugins
* [gmate/gmate](https://github.com/gmate/gmate/) some gedit
  improvements to make it more similar to TextMate. The package
  contain code snippets, plugins, and an automatic registration of
  rails-related files.
* [aubergene/gedit-mate](https://github.com/aubergene/gedit-mate) Gedit set of plugins, color shemes, snippets.
* [ltoth/gedit-conf](https://github.com/ltoth/gedit-conf/) Gedit configuration files and plugins
  
## Other Requirements ##

* python-gnome2 or python-mate required by most plugins
* python-webkit & python-markdown required by plugin **Markdown Preview**
* rabbitvcs-core required by plugin **RabbitVCS**
* python-mysqldb required by plugin **gSqlClient**

