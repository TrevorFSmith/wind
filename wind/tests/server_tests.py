import Queue
import socket
import random
from datetime import datetime, timedelta, date

from django.test import TestCase, TransactionTestCase
from django.test.client import Client
from django.contrib.auth.models import User
from django.core import mail
from django.core.urlresolvers import reverse
from django.core.management import call_command
from django.contrib.auth.models import User

from wind.server import Server
from wind.client import Client as WSClient
from wind.client import EventHandler
from wind.models import ServerRegistration
from wind.events import TestRegistrationEvent, ChannelList, ChannelCreated, ChannelDeleted, Event, Channel, SubscribeResponse, EVENTS, ServiceException, ChannelInfo

class TestBroadcastEvent(Event):
	"""Used only during tests"""
	def __init__(self, message=None):
		self.message = message or ''
		self.serviced = False
		self.username = None
		
	def service(self, connection):
		if not connection.user: raise ServiceException("The connection must be authenticated in order to broadcast.")
		if not connection.channel: raise ServiceException("The connection must be subscribed to a channel in order to broadcast")
		self.serviced = True
		self.username = connection.user.username
		connection.server.send_event(connection.channel.channel_id, self)
		return None

if TestBroadcastEvent not in EVENTS: EVENTS.append(TestBroadcastEvent)

class TestChannel(Channel):
	def __init__(self, channel_id, name=None, options=None):
		super(TestChannel, self).__init__(channel_id, name, options)

	def handle_subscribe_request(self, connection, event):
		if connection.user.username == 'bob':
			return (False, SubscribeResponse(self.channel_id, False))
		else:
			return (True, SubscribeResponse(self.channel_id, True))

	def handle_disconnect(self, connection): pass
	
def send_and_receive(host, port, message, timeout=10, buffer_size=10240):
	"""Sends message to host:port and then receives until the socket is closed."""
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.settimeout(timeout)
	sock.connect((host, port))
	sock.send(message)
	value = sock.recv(buffer_size)
	sock.shutdown(socket.SHUT_RDWR)
	sock.close()
	return value

class ServerTest(TransactionTestCase):
	"""This test must be a TransactionalTestCase because we're accessing the db in multiple threads."""
	
	def setUp(self):
		self.user1 = User.objects.create(username='trevor', is_staff=True, is_superuser=True)
		self.user1.set_password('1234')
		self.user1.save()

		self.user2 = User.objects.create(username='alice')
		self.user2.set_password('1234')
		self.user2.save()

		self.user3 = User.objects.create(username='bob')
		self.user3.set_password('1234')
		self.user3.save()
		
		self.client1 = Client()
		self.client2 = Client()
		self.client3 = Client()
		self.server = Server()
		self.server.start(run_scheduler=False)
		self.assertTrue(TestRegistrationEvent in EVENTS)

	def tearDown(self):
		self.server.stop()

	def test_server_setup(self):
		self.client1.login(username='trevor', password='1234')
		self.client2.login(username='alice', password='1234')
		self.client3.login(username='bob', password='1234')

		self.failUnlessEqual(ServerRegistration.objects.all().count(), 1)
		self.failUnlessEqual(ServerRegistration.objects.all()[0], self.server.registration)

		event_handler = EventHandler()
		client = WSClient(self.user1.session_key, '127.0.0.1', self.server.ws_server.port, '127.0.0.1:8000', event_handler=event_handler.handle_event)
		client.authenticate()
		event = event_handler.events.get(True, 3)
		self.failUnless(event.authenticated)
		self.assertEqual('trevor', event.username)
		self.assertEqual('trevor', client.username)

		event_handler2 = EventHandler()
		client2 = WSClient(self.user2.session_key, '127.0.0.1', self.server.ws_server.port, '127.0.0.1:8000', event_handler=event_handler2.handle_event)
		client2.authenticate()
		event = event_handler2.events.get(True, 3)
		self.failUnless(event.authenticated)
		self.assertEqual('alice', event.username)
		self.assertEqual('alice', client2.username)

		event_handler3 = EventHandler()
		client3 = WSClient(self.user3.session_key, '127.0.0.1', self.server.ws_server.port, '127.0.0.1:8000', event_handler=event_handler3.handle_event)
		client3.authenticate()
		event = event_handler3.events.get(True, 3)
		self.failUnless(event.authenticated)

		client.request_server_info()
		event = event_handler.events.get(True, 3)
		self.failUnless(event.infos)
		self.failUnless(event.infos['status'])
		self.assertEqual(event.infos['status'], 'ok')

		client.list_channels()
		event = event_handler.events.get(True, 3)
		self.failUnless(isinstance(event, ChannelList))
		self.assertEqual(len(event.channels), 1)
		
		client.create_channel('dart.channel')
		event = event_handler.events.get(True, 3)
		self.failUnless(isinstance(event, ChannelCreated))
		self.assertEqual(event.channel_id, 'dart.channel')
		client.list_channels()
		event = event_handler.events.get(True, 3)
		self.assertEqual(len(event.channels), 2)
		self.failUnless('dart.channel' in event.channels)

		client.create_channel('kite.channel', class_name='wind.tests.server_tests.TestChannel')
		event = event_handler.events.get(True, 3)
		self.failUnless(isinstance(event, ChannelCreated))
		self.assertEqual(event.channel_id, 'kite.channel')
		client.list_channels()
		event = event_handler.events.get(True, 3)
		self.assertEqual(len(event.channels), 3)
		self.failUnless('dart.channel' in event.channels)
		self.failUnless('kite.channel' in event.channels)

		client.send_event(TestBroadcastEvent('I love traffic lights.'))
		self.assertRaises(Queue.Empty, event_handler.events.get, True, 3)

		self.assertFalse(client.request_channel_info())

		client.subscribe('kite.channel')
		event = event_handler.events.get(True, 3)
		self.failUnless(isinstance(event, SubscribeResponse))
		self.assertEqual('kite.channel', event.channel_id)
		self.assertTrue(event.joined)

		client3.subscribe('kite.channel')
		event = event_handler3.events.get(True, 3)
		self.failUnless(isinstance(event, SubscribeResponse))
		self.assertEqual('kite.channel', event.channel_id)
		self.assertFalse(event.joined) # This is false because the TestChannel rejects bob

		self.assertTrue(client.request_channel_info())
		event = event_handler.events.get(True, 3)
		self.failUnless(isinstance(event, ChannelInfo))
		self.assertEqual(len(event.usernames), 1)
		self.assertEqual(event.usernames[0], 'trevor', 'Unexpected usernames: %s' % event.usernames)

		client.send_event(TestBroadcastEvent('I love traffic lights.'))
		event = event_handler.events.get(True, 3)
		self.assertEqual(event.message, 'I love traffic lights.')
		self.assertEqual(event.username, 'trevor')
		self.assertRaises(Queue.Empty, event_handler2.events.get, True, 3)
				
		client.delete_channel('dart.channel')
		event = event_handler.events.get(True, 3)
		self.failUnless(isinstance(event, ChannelDeleted))
		self.assertEqual(event.channel_id, 'dart.channel')
		client.list_channels()
		event = event_handler.events.get(True, 3)
		self.assertEqual(len(event.channels), 2)
		self.failIf('dart.channel' in event.channels)
		self.failUnless('kite.channel' in event.channels)
		self.assertEqual('kite.channel', client.channel_id)

		ServerRegistration.objects.broadcast_event(self.user1.session_key, TestBroadcastEvent("Hey, y'all!"), 'kite.channel')
		event = event_handler.events.get(True, 3)
		self.failUnlessEqual(event.message, "Hey, y'all!")
		self.assertRaises(Queue.Empty, event_handler2.events.get, True, 3)

		client2.subscribe('kite.channel')
		event = event_handler2.events.get(True, 3)
		self.failUnless(isinstance(event, SubscribeResponse))
		self.assertEqual('kite.channel', event.channel_id)
		self.assertTrue(event.joined)

		self.assertTrue(client.request_channel_info())
		event = event_handler.events.get(True, 3)
		self.failUnless(isinstance(event, ChannelInfo))
		self.assertEqual(len(event.usernames), 2, event.usernames)
		self.assertTrue('trevor' in event.usernames)
		self.assertTrue('alice' in event.usernames)

		ServerRegistration.objects.broadcast_event(self.user1.session_key, TestBroadcastEvent("Hey, y'all!"), 'kite.channel')
		event = event_handler.events.get(True, 3)
		self.failUnlessEqual(event.message, "Hey, y'all!")
		event = event_handler2.events.get(True, 3)
		self.failUnlessEqual(event.message, "Hey, y'all!")

		client.close()
		client2.close()
		