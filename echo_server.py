import os
import sys
import time
import gevent
import signal
import random
import traceback

from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler

class App(object):

	def handle(self, ws):
		if ws.path == "/echo":
			while True:
				m = ws.receive()
				if m is None: break
				ws.send(m)

	def __call__(self, environ, start_response):
		if environ["PATH_INFO"] in ("/echo",):
			self.handle(environ["wsgi.websocket"])
		else:
			start_response("404 Not Found", [])
			return []

if __name__ == "__main__":
	#gevent.signal(signal.SIGQUIT, gevent.shutdown)
	server = pywsgi.WSGIServer(("", 9000), App(), handler_class=WebSocketHandler)
	try:
		server.serve_forever()
	except KeyboardInterrupt:
		pass