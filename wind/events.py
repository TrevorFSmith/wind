"""
The hydration code assumes that these event objects have only string attributes and has a no-param __init__.
"""
import json
import Queue
import types, traceback, sys
from datetime import datetime

from handler import to_json, from_json

class Channel(object):
	"""
	Information used in subscribing to and routing events.
	You can create custom channels by extending Channel and then in the CreateChannelRequest use the class_name parameter to indicate which Channel class to use.
	"""
	def __init__(self, server, channel_id, name=None, options=None):
		self.server = server
		self.channel_id = channel_id
		self.name = name
		self.options = options # channel specific information which the channel creator wants to link to the channel

	def handle_subscribe_request(self, connection, event):
		"""
		Override this to define a custom subscription policy.
		The default is to allow anyone to join the channel.
		Returns a tuple: (<true if subscribed>, <SubscribeResponse event>)
		"""
		return (True, SubscribeResponse(channel_id=self.channel_id, joined=True))

	def handle_disconnect(self, connection):
		"""
		Override this if you need to do any cleanup when a connection is removed.
		"""
		return

	def send_event(self, event): self.server.send_event(self.channel_id, event)

	def __repr__(self): return self.name or self.channel_id

class ServiceException(Exception):
	"""An exception which may be thrown if serviced in a bad state, eg a broadcast for a connection which is not subscribed to any channels"""
	pass

class Event(object):
	"""
	The base class which all events extend.
	Server side events may implement the service(self, connection) method
	"""
	def from_json(self, json_string):
		return from_json(self, json_string)
	def to_json(self):
		self.type = self.__class__.__name__
		return to_json(self)
	@classmethod
	def dict(cls):
		return cls().__dict__
	@classmethod
	def event_name(cls):
		return cls.__name__

class ForwardingEvent(Event):
	"""An event which, when received by the server, is broadcast to all listeners on the channel"""
	def service(self, connection):
		if connection.channel:
			connection.channel.send_event(self)
		else:
			print 'Received a forwarding event for a connection with no channel:'
			print '\t', connection, self.to_json()

class AuthenticationRequest(Event):
	"""An authentication request from a new WebSocket connection."""
	def __init__(self, session_id=None):
		self.session_id = session_id

class AuthenticationResponse(Event):
	"""An authentication response from the Server"""
	def __init__(self, authenticated=False, username=None):
		self.authenticated = authenticated
		self.username = username

class SubscribeRequest(Event):
	def __init__(self, channel_id=None):
		self.channel_id = channel_id

class SubscribeResponse(Event):
	"""A response indicating whether a SubscribeRequest is successful."""
	def __init__(self, channel_id=None, joined=False):
		self.channel_id = channel_id
		self.joined = joined

class ChannelListRequest(Event):
	"""Used to request the list of channels available to the authenticated client."""
	pass

class ChannelList(Event):
	"""A list of available channels"""
	def __init__(self, channels=None):
		self.channels = channels or [] # an array of channel_ids 

class ChannelInfo(Event):
	def __init__(self, channel_id=None, usernames=None):
		self.channel_id = None
		self.usernames = usernames or [] #an array of usernames
		
class ChannelInfoRequest(Event):
	"""Used to request information about a channel."""
	def __init__(self, channel_id=None):
		self.channel_id = channel_id
	def service(self, connection):
		usernames = [user.username for user in connection.server.get_subscribed_users(self.channel_id)]
		connection.send_event(ChannelInfo(self.channel_id, usernames))
		
class ChannelList(Event):
	"""A list of available channels"""
	def __init__(self, channels=None):
		self.channels = channels or [] # an array of channel_ids 

class CreateChannelRequest(Event):
	def __init__(self, channel_id=None, class_name=None, options=None):
		self.channel_id = channel_id
		self.class_name = class_name
		self.options = options

class ChannelCreated(Event):
	def __init__(self, channel_id=None):
		self.channel_id = channel_id # None if the channel was not created

class ChannelExists(Event):
	def __init__(self, channel_id=None):
		self.channel_id = channel_id

class DeleteChannelRequest(Event):
	def __init__(self, channel_id=None):
		self.channel_id = channel_id

class ChannelDeleted(Event):
	def __init__(self, channel_id=None):
		self.channel_id = channel_id # None if the channel was not created

class Heartbeat(Event):
	"""A heartbeat event, used to test that the connection is alive and the remote client is not hung."""
	def __init__(self):
		self.time = datetime.now()

class ServerInfoRequest(Event):
	"""Used to request stats information about the server."""
	pass

class ServerInfo(Event):
	"""Information about the server which can be fetched from afar."""
	def __init__(self, infos=None):
		"""Infos MUST be maps of simple python types"""
		if not infos: infos = []
		self.infos = infos

class TestRegistrationEvent(Event):
	"""
	This is used in server_tests to test whether register_app_events autodetects events
	DO NOT ADD IT TO events.EVENTS
	"""
	pass

class EchoRequest(Event):
	def __init__(self, message=None):
		self.message = message

	def service(self, connection):
		if not connection.channel: raise ServiceException("Must be subscribed to a channel in order to echo")
		connection.send_event(EchoResponse(self.message))

class EchoResponse(Event):
	def __init__(self, message=None):
		self.message = message

EVENTS = [Heartbeat, AuthenticationRequest, AuthenticationResponse, SubscribeRequest, SubscribeResponse, ServerInfoRequest, ServerInfo, ChannelListRequest, ChannelList, CreateChannelRequest, ChannelCreated, DeleteChannelRequest, ChannelDeleted, EchoRequest, EchoResponse]
CHANNELS = [Channel(None, 'server_announcements', 'Messages from the Server')]

def register_app_events():
	"""Register all of the classes which subclass wind.events.Event in the installed apps' 'events' modules."""
	from django.conf import settings
	for app_module_name in settings.INSTALLED_APPS:
		try:
			app = __import__(app_module_name)
			__import__('%s.events' % app_module_name)
			events = sys.modules['%s.events' % app_module_name]
		except:
			continue
		for key in dir(events):
			attribute = getattr(events, key)
			if type(attribute) == types.TypeType and issubclass(attribute, Event) and attribute != Event:
				if attribute not in EVENTS: EVENTS.append(attribute)
			if hasattr(events, 'CHANNELS'):
				channels = getattr(events, 'CHANNELS')
				for channel in channels:
					if not channel in CHANNELS: CHANNELS.append(channel)
			if hasattr(events, 'channels'):
				channels = getattr(events, 'channels')()
				for channel in channels:
					if not channel in CHANNELS: CHANNELS.append(channel)

class EventHandler:
	"""A handy class for handling incoming events"""
	def __init__(self):
		self.events = Queue.Queue(-1)
	def handle_event(self, event):
		if not isinstance(event, Heartbeat):
			self.events.put(event)

def parse_event_json(json_string):
	try:
		json_data = json.loads(json_string)
		if not 'type' in json_data: raise Exception('No type in JSON');
	except:
		print 'failed to parse json: %s' % len(json_string), json_string
		raise
	for class_object in EVENTS:
		if json_data['type'] == str(class_object.__name__):
			event = class_object()
			event.from_json(json_string)
			return event
	return None

def smart_str(value, default=None):
	if value is None: return default
	if hasattr(value, '__unicode__'): return value.__unicode__()
	return str(value)

# Copyright 2010,2011,2012 Trevor F. Smith (http://trevor.smith.name/) Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0 Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
