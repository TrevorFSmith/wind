"""This is a websocket client which uses the async_chat library.
	It is not thread safe and is generally harder to use than the client in wind.websocket.client.
"""

import asyncore
import socket
from asynchat import async_chat
import contrib
import traceback

from server import parse_headers, CRLF, DOUBLE_CRLF, START_BYTE, END_BYTE

class WebSocketClient(async_chat):
	def __init__(self, host, port, origin, frame_handler, protocol='0.01', resource='/'):
		async_chat.__init__(self)
		self.host = host
		self.port = port
		self.origin = origin
		self.frame_handler = frame_handler
		self.protocol = protocol
		self.resource = resource
		self.buffer_size = 8192

		self.read_buffer = []

		self.current_read_handler = self.process_headers
		self.set_terminator(DOUBLE_CRLF)
		
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.connect((self.host, self.port))

	def send_frame(self, data):
		"""THIS IS NOT THREAD SAFE"""
		self.push(START_BYTE + data + END_BYTE)

	def collect_incoming_data(self, data):
		self.read_buffer.append(data)
		
	def found_terminator(self):
		self.current_read_handler()
	
	def reset_input(self): del self.read_buffer[:]

	def input_as_string(self): return ''.join(self.read_buffer)

	def handle_connect(self):
		try:
			self.push(self.generate_request_headers())
		except:
			traceback.print_exc()
			raise

	def process_headers(self):
		try:
			self.headers = parse_headers(self.input_as_string())
			self.reset_input()
			self.current_read_handler = self.process_challenge_response
			self.set_terminator(16)
		except:
			traceback.print_exc()
			raise

	def process_challenge_response(self):
		#TODO actually validate the challenge response
		self.reset_input()
		self.current_read_handler = self.process_frame
		self.set_terminator(END_BYTE)

	def process_frame(self):
		try:
			data = self.input_as_string()[1:]
			self.reset_input()
			self.frame_handler(data)
		except:
			traceback.print_exc()
			raise

	def generate_request_headers(self):
		security = contrib.generate_request_security()
		headers = [
			"GET %s HTTP/1.1" % self.resource,
			"Host: %s:%s" % (self.host, self.port),
			"Connection: Upgrade",
			"Sec-WebSocket-Key1: %s" % security[0][1],
			"Sec-WebSocket-Key2: %s" % security[1][1],
			"Sec-WebSocket-Protocol: %s" % self.protocol,
			"Upgrade: WebSocket",
			"Origin: %s" % self.origin
		]
		return '%s%s%s' % (CRLF.join(headers), DOUBLE_CRLF, security[2])


	def handle_close(self):  self.close()

	def handle_expt(self): self.handle_error()

	def handle_error(self):
		traceback.print_exc()
		self.handle_close()

