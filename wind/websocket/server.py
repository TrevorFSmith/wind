import asyncore, asynchat, socket, sys
from datetime import datetime
import re
import traceback
import struct
import hashlib
import threading
import traceback
from hashlib import sha1
from base64 import b64encode
from gevent import WebSocketFrame, WebSocketError

WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

CRLF = '\x0D\x0A'
DOUBLE_CRLF = CRLF+CRLF
START_BYTE = '\x00'
END_BYTE = '\xff'

def parse_headers(header):
	"""Breaks up the header lines of the WebSocket request into a dictionary"""
	result = {}
	lines = [token.strip() for token in header.split('\r')]
	request_line = lines[0].split(' ')
	lines = lines[1:]
	result['method'] = request_line[0]
	result['path'] = request_line[1]
	for line in lines:
		if len(line) == 0: break
		key, value = line.split(' ', 1)
		key = key[:len(key) - 1]
		result[key.lower()] = value
	return result

class WebSocketServerHandler(asynchat.async_chat):
	def __init__(self, sock, addr, server):
		asynchat.async_chat.__init__(self, sock=sock)
		self.addr = addr
		self.server = server
		self.ibuffer = []
		self.current_handler = self.process_headers
		self.set_terminator(DOUBLE_CRLF)
		self.headers = None
		
		self.frame = WebSocketFrame() # The current message frame.  This instance is reused for each frame.
		self.message = bytearray() # The message so far.

	def collect_incoming_data(self, data):
		self.ibuffer.append(data)
		#print 'WS COLLECTED %s' % repr(self.ibuffer[-1])

	def found_terminator(self): self.current_handler()
	
	def process_headers(self):
		try:
			self.headers = parse_headers(self.input_as_string())
			self.reset_input()

			#print 'WS processing headers', self.headers

			web_socket_key = self.headers["sec-websocket-key"]
			web_socket_accept = b64encode(sha1(web_socket_key + WEBSOCKET_GUID).digest())

			location = self.headers["origin"][7:]
			if location.find(':') != -1: location = location[0:location.find(':'):]

			self.push('HTTP/1.1 101 Switching Protocols' + CRLF)
			self.push('Upgrade: websocket' + CRLF)
			self.push('Connection: Upgrade' + CRLF)
			self.push('Sec-WebSocket-Origin: ' + self.headers["origin"] + CRLF)
			self.push(('Sec-WebSocket-Location: ws://%s:%s/' % (location,self.server.port)) + CRLF)
			self.push(('Sec-WebSocket-Protocol: %s' % self.server.protocol) + CRLF)
			self.push(('Sec-WebSocket-Accept: %s' % web_socket_accept) + DOUBLE_CRLF)

			self.current_handler = self.handle_frame_header
			self.set_terminator(2)
		except:
			#print 'Error in process headers'
			traceback.print_exc()
			reraise()

	def handle_frame_header(self):
		try:
			#print 'Handling frame header'
			self.frame.reset()
			to_read = self.frame.handle_header(self.input_as_string())
			self.reset_input()
			if to_read > 0:
				self.current_handler = self.handle_length
				self.set_terminator(to_read)
			else:
				self.current_handler = self.handle_mask
				self.set_terminator(4)
		except:
			#print 'Error in frame header'
			traceback.print_exc()
			reraise()

	def handle_length(self):
		#print 'Handling length', self.frame.fin, self.frame.opcode
		self.frame.handle_length(self.input_as_string())
		self.reset_input()
		self.current_handler = self.handle_mask
		self.set_terminator(4)

	def handle_mask(self):
		#print 'Handling mask', self.frame.length
		self.frame.handle_mask(self.input_as_string())
		self.reset_input()
		if self.frame.length > 0:
			self.current_handler = self.handle_payload
			self.set_terminator(self.frame.length)
			return
		self.check_opcode()

	def handle_payload(self):
		#print 'Handling payload'
		self.frame.handle_payload(self.input_as_string())
		self.reset_input()
		self.check_opcode()

	def check_opcode(self):
		#print 'Checking opcode', self.frame.opcode, self.frame.payload
		try:
			if self.frame.opcode in (WebSocketFrame.OPCODE_TEXT, WebSocketFrame.OPCODE_BINARY):
				self.message.extend(self.frame.payload)

				if self.frame.fin:
					self.server.frame_callback(self, '%s' % self.message)
					self.message = bytearray()

				self.current_handler = self.handle_frame_header
				self.set_terminator(2)
				return

			if self.frame.opcode == WebSocketFrame.OPCODE_CLOSE:
				self.send_close()
				return
			elif self.frame.opcode == WebSocketFrame.OPCODE_PING:
				self.send_frame(self.frame.payload, opcode=WebSocketFrame.OPCODE_PONG)
				return
			elif self.frame.opcode == WebSocketFrame.OPCODE_PONG:
				return
			else:
				#self._close()  # XXX should send proper reason?
				raise WebSocketError("Unexpected opcode=%r" % (f_opcode, ))
		except:
			traceback.print_exc()
			reraise()
		self.current_handler = self.handle_frame_header
		self.set_terminator(2)

	def send_close(self, code=1000, message=''):
		message = WebSocketFrame.encode_text(message)
		self.send_frame(struct.pack('!H%ds' % len(message), code, message), opcode=WebSocketFrame.OPCODE_CLOSE)

	def send_frame(self, data, opcode=WebSocketFrame.OPCODE_TEXT):
		header, message = WebSocketFrame.encode(data, opcode)
		self.push(header)
		if message: self.push(message)

	def reset_input(self): del self.ibuffer[:]

	def input_as_string(self): return ''.join(self.ibuffer)

	def handle_error(self): self.handle_close()

	def handle_close(self):
		self.discard_buffers()
		self.cleanup()
		self.close()

	def cleanup(self): self.server.remove_handler(self)

class WebSocketServer(asyncore.dispatcher):
	def __init__(self, host, port, frame_callback, protocol=0.1, handler_closed_callback=None):
		asyncore.dispatcher.__init__(self)
		self.host = host
		self.port = port
		self.frame_callback = frame_callback
		self.handler_closed_callback = handler_closed_callback
		self.protocol = protocol

		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.set_reuse_addr()
		self.bind((self.host, self.port))
		self.listen(1)
		self.stopped = False
		self.handlers = []
		self.thread = None
		
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

	def handle_accept(self):
		pair = self.accept()
		if not self.stopped and pair is not None:
			sock, addr = pair
			self.handlers.append(WebSocketServerHandler(sock, addr, self))

# Copyright 2011 Trevor F. Smith (http://trevor.smith.name/) Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0 Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
