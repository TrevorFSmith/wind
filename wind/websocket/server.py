import os
import re
import gevent
import struct
import hashlib
import traceback
import threading
import traceback
from datetime import datetime

from geventwebsocket.handler import WebSocketHandler

class WebSocketServerHandler(object):
	def __init__(self, web_socket, server):
		self.web_socket = web_socket
		self.server = server
	
	def handle(self):
		while True:
			message = self.web_socket.receive()
			if message is None: break
			this.server.frame_callback(message)
		self.server.remove_handler(self)

class WebSockerServer(object):
	'''
	A WSGI callable for handling WebSocket connections
	'''
	def __init__(self, host, port, frame_callback, handler_closed_callback=None):
		self.host = host
		self.port = port
		self.frame_callback = frame_callback
		self.handler_closed_callback = handler_closed_callback

		self.stopped = False
		self.handlers = []

	def __call__(self, environ, start_response):
		'''The WSGI callable implementation'''
		handler = WebSocketServerHandler()
		self.handlers[self.handlers.length] = handler
		handler.handle(environ['wsgi.websocket'])
		return []

	def start(self):
		if self.thread: return
		self.thread = threading.Thread(target = asyncore.loop)
		self.thread.start()

	def stop(self):
		if self.stopped: return
		self.stopped = True
		self.close()
		for handler in self.handlers: handler.close()
	
	def remove_handler(self, handler):
		self.handlers.remove(handler)
		if self.handler_closed_callback: self.handler_closed_callback(handler)

# Copyright 2011 Trevor F. Smith (http://trevor.smith.name/) Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0 Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
