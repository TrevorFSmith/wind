import Queue
import threading
import random
import datetime
import logging
import traceback
import simplejson

from websocket.client import WebSocketClient
import events

class EventHandler:
	"""A handy class for handling incoming events"""
	def __init__(self):
		self.events = Queue.Queue(-1)
	def handle_event(self, event):
		if not isinstance(event, events.Heartbeat):
			self.events.put(event)

class Client:
	IGNORED_EVENTS = [events.Heartbeat, events.ServerInfo, events.ChannelList, events.ChannelCreated, events.ChannelDeleted]
	
	def __init__(self, session_key, ws_host, ws_port, ws_origin, event_handler=None):
		self.session_key = session_key
		self.ws_client = WebSocketClient(ws_host, ws_port, ws_origin)
		self.event_handler = event_handler
		self.username = None

		# These are set once we've subscribed to a channel
		self.channel_id = None
		self.is_member = None
		self.is_editor = None
		self.is_admin = None

		
		self.should_run = True
		self.incoming_event_thread = threading.Thread(target=self.incoming_loop)
		self.incoming_event_thread.start()		

	def incoming_loop(self):
		while self.should_run:
			try:
				message = self.ws_client.receive()
			except:
				self.close()
				return
			if message == None: break
			event = events.parse_event_json(message)
			if event == None:
				event_json = simplejson.loads(message)
				raise Exception('Unknown event type: %s' % event_json['type'])

			if isinstance(event, events.AuthenticationResponse):
				if event.authenticated:
					self.username = event.username
			elif isinstance(event, events.SubscribeResponse):
				if event.joined:
					self.channel_id = event.channel_id
			elif event.__class__ in Client.IGNORED_EVENTS:
				pass # don't care
			else:
				pass
				#print 'Unhandled incoming event: %s' % event

			if self.event_handler: self.event_handler(event)

	def authenticate(self): self.send_event(events.AuthenticationRequest(self.session_key))

	def list_channels(self): self.send_event(events.ChannelListRequest())

	def request_channel_info(self):
		if not self.channel_id: return False
		self.send_event(events.ChannelInfoRequest(self.channel_id))
		return True

	def create_channel(self, channel_id, class_name=None): self.send_event(events.CreateChannelRequest(channel_id, class_name=class_name))

	def delete_channel(self, channel_id): self.send_event(events.DeleteChannelRequest(channel_id))

	def subscribe(self, channel_id): self.send_event(events.SubscribeRequest(channel_id))

	def request_server_info(self): self.send_event(events.ServerInfoRequest())

	def send_event(self, event):
		try:
			self.ws_client.send(event.to_json())
		except:
			self.close()

	def close(self):
		self.should_run = False
		self.ws_client.close()
		if self.event_handler: self.event_handler(None)
