from wind.events import Event, ForwardingEvent, Channel, SubscribeResponse

class ChatterChannel(Channel):
	def handle_subscribe_request(self, connection, event):
		connection.chatter_token = None
		return (True, SubscribeResponse(channel_id=self.channel_id, joined=True))

class SetToken(Event):
	'''Used to set which chatter stream the connection is for'''
	def __init__(self, token=None):
		self.token = token

	def service(self, connection):
		connection.chatter_token = self.token
		if self.token:
			connection.send_event(TokenSet(True))
		else:
			connection.send_event(TokenSet(False))

class TokenSet(Event):
	'''Used to acknowledge SetToken'''
	def __init__(self, success=None):
		self.success = success

class SendChatter(ForwardingEvent):
	def __init__(self, message=None, username=None):
		self.message = message
		self.username = username

	def service(self, connection):
		if not connection.channel:
			print 'No channel for SendChatter'
			return
		if not connection.chatter_token:
			print 'No chatter token for SendChatter'
			return
		self.token = connection.chatter_token

		# Only send events to connections with the right chatter_token
		for chatter_connection in connection.server.get_connections('chatter'):
			if chatter_connection.chatter_token != self.token: continue
			chatter_connection.send_event(self)

EVENTS = [SendChatter, SetToken, TokenSet]
CHANNELS = [ChatterChannel(None, 'chatter', 'Chit and chat')]
