"""A library for the service of WebSockets (http://dev.w3.org/html5/websockets/) based connections"""

import socket
import threading
import sys
import time
import re
import traceback
import struct
import hashlib
import Queue

from server import CRLF, DOUBLE_CRLF, START_BYTE, END_BYTE
from gevent import WebSocketFrame

def parse_request_header(header):
	"""Breaks up the header lines of the WebSocket request into a dictionary"""
	lines = [token.strip() for token in header.split('\r')[1:]]
	result = {}
	for line in lines:
		if len(line) == 0: break
		key, value = line.split(' ', 1)
		result[key[:len(key) - 1]] = value
	return result

def receive_web_socket_message(socket):
		data = socket.recv(2)
		frame = WebSocketFrame()
		try:
			to_read = frame.handle_header(data[:2], enforce_mask=False)
		except:
			reraise()
		if to_read > 0:
			data = socket.recv(to_read)
			frame.handle_length(data)
		payload = socket.recv(frame.length)
		while len(payload) < frame.length:
			buf = socket.recv(frame.length - len(payload))
			if not buf: raise Exception('Could not read the websocket payload')
			payload += buf
		
		if len(payload) == 0: return None
		return payload

MAX_HEADER_LENGTH = 8192

class WebSocketClient:
	def __init__(self, host, port, origin, protocol='sample', version='0.1'):
		self.host = host
		self.port = port
		self.origin = origin
		self.protocol = protocol
		self.version = version
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.socket.connect((self.host, self.port))
		self.socket.send(self.generate_request_headers())
		self.response_headers = self.receive_request_header()
		self.closed = False

	def receive_request_header(self):
		data = ''
		while len(data) <= MAX_HEADER_LENGTH and not data.endswith('\r\n\r\n'): data += self.socket.recv(1)
		return parse_request_header(data)
		
	def receive(self):
		try:
			return receive_web_socket_message(self.socket)
		except:
			if not self.closed: raise
			
	def send(self, message, opcode=WebSocketFrame.OPCODE_TEXT):
		header, message = WebSocketFrame.encode(message, opcode, '1234')
		self.socket.send(header)
		if message: self.socket.send(message)

	def close(self):
		if self.closed: return
		self.closed = True
		try:
			self.socket.shutdown(socket.SHUT_RDWR)
			self.socket.close()
		except:
			pass # don't care

	def generate_request_headers(self):
		headers = [
			"GET / HTTP/1.1",
			"Host: %s:%s" % (self.host, self.port),
			"Upgrade: WebSocket",
			"Connection: Upgrade",
			"Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==",
			"Origin: %s" % self.origin,
			"Sec-WebSocket-Protocol: %s" % self.protocol,
			"Sec-WebSocket-Version: %s" % self.version,
		]
		return '%s%s' % (CRLF.join(headers), DOUBLE_CRLF)
