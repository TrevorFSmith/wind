from wind.events import Event, Channel, SubscribeResponse

class ChatterChannel(Channel):
	def handle_subscribe_request(self, connection, event):
		print 'Chattering', connection.user
		return (True, SubscribeResponse(channel_id=self.channel_id, joined=True))

	def handle_disconnect(self, connection):
		print 'No longer chattering', connection.user

class SendChatter(Event):
	pass

EVENTS = [SendChatter]
CHANNELS = [ChatterChannel(None, 'chatter', 'Chit and chat')]
