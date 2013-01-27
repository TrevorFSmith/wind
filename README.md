# Wind

A WebSocket event system for Django

# Notes
## 2013-01-27

The WebSocket spec changed (again!) and it looks like [gevent-websocket](https://bitbucket.org/Jeffrey/gevent-websocket/overview) has enough momentum that it makes more sense for me to rip out the low level WebSocket support and just make Wind into a high level event system for Django.

This is also a good opportunity to move Wind out of [Blank Slate](https://github.com/TrevorFSmith/blank_slate/) so that projects don't need to commit to that lifestyle to use Wind.

So, I'm creating a [Wind repo on Github](https://github.com/TrevorFSmith/wind/).


