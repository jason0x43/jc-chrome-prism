[Alfred 2][alfred] Workflow for managing Chrome instances
=========================================================

<p align="center">
<img alt="Screenshot" src="https://dl.dropbox.com/s/iy5bfl3bv2u5o62/jc-chrome-prism_screenshot.png" />
</p>

<p align="center">
  <a href="https://dl.dropbox.com/s/xkwm3vlryhacfya/jc-chrome-prism.alfredworkflow"><img src="http://i.imgur.com/E8I5TfU.png" alt="Download"></a>
</p>


This workflow lets you create and manage separate instances of Chrome. Each
instance will have its own cache, settings, extensions, etc. This is handy for
setting up different browser instances for work, testing stuff, whatever.

There is only one command: `prism` (I like to keep things simple).

* By default, you'll see a list of available prisms.
* Type "+" to create a new Prism; you can supply a name (no spaces allowed) and
  description right in the Alfred command line, or dialogs will pop up for you
  to fill in.
* Selecting a prism can do three things:
  * Just pressing enter will load the prism (or just bring it to the front if
    it's already running)
  * Hold Cmd to edit the prism's JSON config file; this will let you add
    command line options for Chrome
  * Hold Option to delete the prism
  * Hold Ctrl to open the prism's app directory in Finder

Installation
------------

The easiest way to install the workflow is to download the
[prepackaged workflow][pkg].  Double-click on the downloaded file, or drag
it into the Alfred Workflows window, and Alfred should install it.

I'm using `weather` as the main command, which is the same as the built-in
weather web search in Alfred. The web search can be disabled in Features &rarr;
Web Search if you don't want it showing up in your weather report.
Alternatively, you can change the `weather` command to something else.

Requirements
------------

The only requirement is Python 2.7+. If you have Lion or Mountain Lion, you're
good.

Credits
-------

The idea for a Chrome instance manager came from [Jeremy Mack][jeremy] (or at
least that's where I got it from). The awesome icon was created by [Ethan
Muller][ethan].

[pkg]: https://dl.dropbox.com/s/xkwm3vlryhacfya/jc-chrome-prism.alfredworkflow
[img]: https://dl.dropbox.com/s/iy5bfl3bv2u5o62/jc-chrome-prism_screenshot.png
[alfred]: http://www.alfredapp.com
[jeremy]: https://github.com/mutewinter
[ethan]: http://dribbble.com/shots/951015-Chrome-Prism-Icon?list=tags&tag=chrome
