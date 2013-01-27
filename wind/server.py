"""THIS IS NOT THREAD SAFE AND SHOULD ONLY BE HANDLED IN THE ASYNCORE LOOP"""
import sys
import Queue
import socket
import traceback
import threading
import time, datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.models import AnonymousUser

import events
from websocket.server import WebSocketServer

from handler import to_json
from models import ServerRegistration, SessionKey
from scheduler import discover_tasks, Scheduler

AUTHENTICATED_ACTION = 'ws_authentication'
JOINED_CHANNEL_ACTION = 'ws_joined_channel'
DISCONNECTED_ACTION = 'ws_disconnected'
FAILED_SUBSCRIPTION_ACTION = 'ws_failed_sub'

class WebSocketConnection:
	def __init__(self, server, handler):
		self.server = server
		self.handler = handler

		self.user = None
		self.channel = None
		self.disconnected = False

	def send_event(self, event): self.handler.send_frame(event.to_json())

	def handle_incoming_frame(self, frame_data):
		#print 'Incoming: %s' % repr(frame_data)
		event = events.parse_event_json(frame_data)
		if not event:
			print "Could not read an event from the data: %s" % frame_data
			return

		response_event = None
		if isinstance(event, events.Heartbeat):
			pass # ignore for now, eventually maybe track dead connections?
		elif isinstance(event, events.AuthenticationRequest):
			if event.session_id == settings.WEB_SOCKETS_SECRET:
				self.user = User.objects.filter(is_staff=True)[0]
				response_event = events.AuthenticationResponse(True, self.user.username)
			else:
				user = self.user_from_session_key(event.session_id)
				if user.is_authenticated():
					self.user = user
					response_event = events.AuthenticationResponse(True, user.username)
				else:
					print "Auth failure with session id %s" % event.session_id
					response_event = events.AuthenticationResponse(False)
		elif isinstance(event, events.ServerInfoRequest):
			if not self.user:
				print 'Attemped unauthed info request'
			else:
				response_event = events.ServerInfo({
					'status':'ok',
					'connections':len(self.server.ws_connections),
					'channel count':len(self.server.channels),
					'channels':[key for key in self.server.channels.keys()]
				})
				
		elif isinstance(event, events.ChannelListRequest):
			if self.user:
				response_event = events.ChannelList([channel for channel in self.server.channels])
			else:
				print 'Attempted unauthed channel list request'
				
		elif isinstance(event, events.CreateChannelRequest):
			if self.user:
				# TODO fix this massive race condition
				if not self.server.channels.has_key(event.channel_id):
					if event.class_name:
						try:
							module_name = '.'.join(event.class_name.split('.')[0:-1])
							class_name = event.class_name.split('.')[-1]
							__import__(module_name)
							modu = sys.modules[module_name]
							clz = getattr(modu, class_name)
							if issubclass(clz, events.Channel):
								channel = clz(self.server, event.channel_id, options=event.options)
								self.server.channels[channel.channel_id] = channel
								response_event = events.ChannelCreated(channel.channel_id)
							else:
								print 'Tried to create Channel using a non Channel class:', clz
						except:
							traceback.print_exc()
					else:
						channel = events.Channel(self.server, event.channel_id)
						self.server.channels[channel.channel_id] = channel
						response_event = events.ChannelCreated(channel.channel_id)
				else:
					response_event = events.ChannelExists(channel.channel_id)
					print 'already have that key', event.channel_id
			else:
				print 'Attempted unauthed channel list request'
			
		elif isinstance(event, events.DeleteChannelRequest):
			if self.user:
				# TODO fix this massive race condition
				if self.server.channels.has_key(event.channel_id):
					del(self.server.channels[event.channel_id])
					response_event = events.ChannelDeleted(event.channel_id)
			else:
				print 'Attempted unauthed channel list request'
				
		elif isinstance(event, events.SubscribeRequest):
			if not self.user:
				print 'Attemped unauthed subscribe'
				response_event = events.SubscribeResponse(event.channel_id, False)
			elif self.channel:
				print 'Attempted to subscribe to more than one channel'
				response_event = events.SubscribeResponse(event.channel_id, False)
			elif not self.server.channels.has_key(event.channel_id):
				print 'Attemped subscription to unknown channel: %s' % event.channel_id
				response_event = events.SubscribeResponse(event.channel_id, False)
			else:
				channel = self.server.channels[event.channel_id]
				success, response_event = channel.handle_subscribe_request(self, event)
				if success:
					self.channel = channel

		elif hasattr(event, 'service'):
			try:
				response_event = event.service(self)
			except:
				pass
				traceback.print_exc()
				#print 'error servicing event:', event
		else:
			print "Received unhandled event %s" % event.to_json()

		if response_event:
			#print 'Outgoing: %s' % repr(to_json(response_event))
			self.handler.send_frame(response_event.to_json())

	def user_from_session_key(self, session_key):
		"""Returns a User object if it is associated with a session key, otherwise None"""
		if SessionKey.objects.filter(key=session_key).count() == 0: return AnonymousUser()
		return SessionKey.objects.get(key=session_key).user
			
	def finish(self):
		"""Clean up the connection"""
		if self.disconnected: return
		self.disconnected = True
		self.server.ws_connections.remove(self)
		if self.channel: self.channel.handle_disconnect(self)

	def __unicode__(self):
		return "Connection: %s user: %s channel: %s" % (self.client_address, self.user, self.channel.channel_id)	

class Server:
	"""The handler of WebSockets based communications."""
	def __init__(self):
		self.ws_server = WebSocketServer('0.0.0.0', settings.WEB_SOCKETS_PORT, self.frame_callback, handler_closed_callback=self.handler_closed_callback)
		self.ws_connections = []

		self.registration = None
		
		self.channels = {} # map of channel_id to channel
		events.register_app_events()
		for channel in events.CHANNELS: self.channels[channel.channel_id] = channel

		self.scheduler = Scheduler()
		for task in discover_tasks(): self.scheduler.add_task(task())

	def frame_callback(self, handler, frame_data):
		connection = self.get_or_create_connection(handler)
		try:
			connection.handle_incoming_frame(frame_data)
		except:
			traceback.print_exc()
			connection.finish()

	def handler_closed_callback(self, handler):
		for connection in self.ws_connections:
			if connection.handler == handler:
				connection.finish()
				return
		print 'unknown closed handler', handler
		
	def start(self, run_scheduler=True, run_websocket_server=True):
		if run_scheduler: self.scheduler.start_all_tasks()
		if run_websocket_server: self.ws_server.start()
		
		for registration in ServerRegistration.objects.all(): registration.delete()
		self.registration, created = ServerRegistration.objects.get_or_create(ip=socket.gethostbyname(socket.gethostname()), port=self.ws_server.port)

	def stop(self):
		self.scheduler.stop_all_tasks()
		if self.registration:
			try:
				self.registration.delete()
			except:
				traceback.print_exc()

		self.ws_server.stop()
		
		for con in self.ws_connections:
			try:
				con.handler.close()
			except:
				traceback.print_exc()

	def send_event(self, channel_id, event):
		for connection in self.get_client_connections(channel_id): connection.send_event(event)

	def get_or_create_connection(self, handler):
		for connection in self.ws_connections:
			if connection.handler == handler: return connection
		connection = WebSocketConnection(self, handler)
		self.ws_connections.append(connection)
		return connection

	def get_subscribed_users(self, channel_id):
		users = []
		for connection in self.get_client_connections(channel_id):
			if connection.user != None and connection.user not in users: users.append(connection.user)
		return users

	def get_client_connections(self, channel_id):
		#TODO keep a hashmap of channel_id:connection[] for faster access
		cons = []
		for connection in self.ws_connections:
			if connection.channel and connection.channel.channel_id == channel_id: cons.append(connection)
		return cons

# Copyright 2010,2011,2012 Trevor F. Smith (http://trevor.smith.name/) Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0 Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
