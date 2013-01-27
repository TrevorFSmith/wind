import time
import pprint
import simplejson
import datetime
import Queue

from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User
from django.core import mail

from wind.websocket.client import WebSocketClient
from wind.websocket.server import WebSocketServer

def echo_callback(handler, frame_data):
	handler.send_frame(frame_data)

class WebSocketTest(TestCase):
	def setUp(self):
		self.server = WebSocketServer('0.0.0.0', 9888, echo_callback)
		self.server.start()

	def tearDown(self):
		self.server.stop()

	def test_server(self):
		client = WebSocketClient('127.0.0.1', self.server.port, '127.0.0.1:8000')
		message = 'I hope this works'
		client.send(message)
		self.failUnlessEqual(message, client.receive())
		message = 'Does it work twice?'
		client.send(message)
		self.failUnlessEqual(message, client.receive())
		message = unicode('Does unicode like work?')
		client.send(message)
		self.failUnlessEqual(message, client.receive())
		client2 = WebSocketClient('127.0.0.1', self.server.port, '127.0.0.1:8000')
		message = 'I hope this works'
		client2.send(message)
		self.failUnlessEqual(message, client2.receive())
		message = 'Does this still work twice?'
		client.send(message)
		self.failUnlessEqual(message, client.receive())
		message = ''.join([chr(i % 100) for i in range(10000)])
		client.send(message)
		received = client.receive()
		self.failUnlessEqual(message, received, 'The long message is not equal.  Received %s of %s bytes' % (len(received), len(message)))
		client.close()
		message = 'Perhaps it works after the first has closed?'
		client2.send(message)
		self.failUnlessEqual(message, client2.receive())
		client2.close()


# Copyright 2011 Trevor F. Smith (http://trevor.smith.name/) Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0 Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
