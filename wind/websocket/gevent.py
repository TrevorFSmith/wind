"""
This Websocket library for Gevent is written and maintained by

  Jeffrey Gelens <jeffrey at noppo.pro>


Contributors:

  Denis Bilenko
  Lon Ingram

The source is available here: https://bitbucket.org/Jeffrey/gevent-websocket

The license for this file is at the bottom of the file.

Edit notes:
March, 2012: I converted this to be used by async_server by removing the socket handling and breaking up the logic into separate methods for handling each bit of incoming data. - TFS

"""
import struct
from errno import EINTR
from socket import error as socket_error

class WebSocketFrame(object):
	"""
	A utility class which encodes and decodes websocket messages.
	"""
	OPCODE_TEXT = 0x1
	OPCODE_BINARY = 0x2
	OPCODE_CLOSE = 0x8
	OPCODE_PING = 0x9
	OPCODE_PONG = 0xA

	def __init__(self):
		self.fin = None
		self.opcode = None
		self.has_mask = None
		self.mask = None
		self.length = None

	def reset(self):
		self.fin = None
		self.opcode = None
		self.has_mask = None
		self.mask = None
		self.length = None

	def handle_header(self, data, enforce_mask=True):
		if len(data) != 2: raise WebSocketError('Incomplete header: %r' % data)

		first_byte, second_byte = struct.unpack('!BB', data)
		self.fin = (first_byte >> 7) & 1
		rsv1 = (first_byte >> 6) & 1
		rsv2 = (first_byte >> 5) & 1
		rsv3 = (first_byte >> 4) & 1
		self.opcode = first_byte & 0xf

		if rsv1 or rsv2 or rsv3: raise WebSocketError('Received frame with non-zero reserved bits: %r' % str(data))
		if self.opcode > 0x7 and self.fin == 0: raise WebSocketError('Received fragmented control frame: %r' % str(data))

		self.has_mask = (second_byte >> 7) & 1
		self.length = (second_byte) & 0x7f
		if self.opcode > 0x7 and self.length > 125: raise FrameTooLargeException("Control frame payload cannot be larger than 125 bytes: %r" % str(data))
		if enforce_mask:
			if not self.has_mask and self.length: raise WebSocketError('Message from client is not masked')
		if self.opcode and not self.fin: raise WebSocketError('Received an opcode in a non-fin frame: %r' % self.opcode)

		# Now return the number of additional bytes we need to read to get the real length
		if self.length < 126: return 0
		if self.length == 126: return 2
		assert self.length == 127, self.length
		return 8

	def handle_length(self, data):
		if len(data) == 2:
			self.length = struct.unpack('!H', data)[0]
		elif len(data) == 8:
			self.length = struct.unpack('!Q', data)[0]
		else:
			raise WebSocketError('Expected data of length 2 or 8: %r' % str(data));

	def handle_mask(self, data):
		if len(data) != 4: raise WebSocketError('Bad mask: %r' % data)
		self.mask = struct.unpack('!BBBB', data)

	def handle_payload(self, data):
		if len(data) != self.length: raise WebSocketError('Expected %s bytes, got %s bytes' % (self.length, len(data)))
		self.payload = bytearray(data)
		if self.has_mask:
			for i in xrange(len(self.payload)):
				self.payload[i] = self.payload[i] ^ self.mask[i % 4]

	@classmethod
	def encode(cls, message, opcode, mask=None):
		header = chr(0x80 | opcode)

		if mask:
			mask_num = 0x80
		else:
			mask_num = 0x0

		if isinstance(message, unicode): message = message.encode('utf-8')
		msg_length = len(message)
		if msg_length < 126:
			header += chr(mask_num | msg_length)
		elif msg_length < (1 << 16):
			header += chr(mask_num | 126) + struct.pack('!H', msg_length)
		elif msg_length < (1 << 63):
			header += chr(mask_num | 127) + struct.pack('!Q', msg_length)
		else:
			raise FrameTooLargeException()

		if mask:
			header += mask
			message_chars = [ord(character) for character in message]
			for i in range(len(message_chars)):
				message_chars[i] = message_chars[i] ^ ord(mask[i % 4])
			message = ''.join([chr(c) for c in message_chars])
		try:
			return (header + message, None)
		except TypeError:
			return (header, message)

	@classmethod
	def encode_text(cls, text):
		if isinstance(text, unicode): return text.encode('utf-8')
		return text

class WebSocketError(socket_error): pass

class FrameTooLargeException(WebSocketError): pass

"""
Copyright (c) 2012, Noppo (Jeffrey Gelens) <http://www.noppo.pro/>
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this list
of conditions and the following disclaimer.
Redistributions in binary form must reproduce the above copyright notice, this
list of conditions and the following disclaimer in the documentation and/or
other materials provided with the distribution.
Neither the name of the Noppo nor the names of its contributors may be
used to endorse or promote products derived from this software without specific
prior written permission.
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""