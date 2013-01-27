
window['Wind'] = {};

Wind.WebSocketsPort = {{ web_sockets_port }};
Wind.ServerAnnouncementsChannelID = 'server_announcements';

Wind.stringify = function(hydrateObj){
	var data = { 'type': hydrateObj.type }
	for(var key in hydrateObj){
		if(key == 'type' || key == 'toJSON') continue;
		data[key] = hydrateObj[key];
	}
	return JSON.stringify(data);
}

Wind.Events = {}

{% for event in events %}

Wind.Events.{{ event.event_name }} = function({% for attr in event.dict %}_{{ attr }}{% if not forloop.last %}, {% endif %}{% endfor %}){
	var self = this;
	self.type = '{{ event.event_name }}';
	{% for attr in event.dict %}self.{{ attr }} = _{{ attr }};
	{% endfor %}
	self.toJSON = function(){ return Wind.stringify(self); }
}
{% endfor %}

Wind.Events.rehydrateEvent = function(jsonData){
	event_func = null;
	for(var key in Wind.Events){
		if(key == jsonData['type']){
			event_func = Wind.Events[key];
			break;
		}
	}
	if(event_func == null){
		console.log('Tried to rehydrate an unknown event: ' + JSON.stringify(jsonData));
		return null;
	}
	var spaciblo_event = new event_func(); // we'll just let all the parameters be undefined for the moment
	for(var key in jsonData){
		spaciblo_event[key] = jsonData[key];
	}
	return spaciblo_event;
}

Wind.WebSocketClient = function(_ws_port, _ws_host, _message_handler_function){
	var self = this;
	self.socket = null;
	self.ws_port = _ws_port;
	self.ws_host = _ws_host;
	self.message_handler_function = _message_handler_function;
	
	self.onopen = function() { }
	self.onclose = function() { }
	self.onmessage = function(message) {
		self.message_handler_function(message.data);
	}
	
	self.open = function(){
		try {
			self.socket = new WebSocket("ws://" + self.ws_host + ":" + self.ws_port + "/");
			self.socket.onopen = self.onopen;
			self.socket.onclose = self.onclose;
			self.socket.onmessage = self.onmessage;
		} catch (error) {
			console.log('Err ' + error)
		}
	}
	
	self.send = function(message){
		try {
			self.socket.send(message);
		} catch (error) {
			console.log('Err ' + error, self);
		}
	}
	
	self.close = function(){
		self.socket.close()
	}
}

Wind.Client = function() {
	var self = this;
	
	self.username = null;
	self.channelID = null;
	self.finished_auth = false;
	self.heartbeatTimeout = null;
	self.heartbeatFrequency = 55000;
	
	// set these to receive callbacks on various events
	self.open_handler = function() {}
	self.close_handler = function(){}
	self.authentication_handler = function(successful) {}
	self.subscription_handler = function(channel_id, subscribed, is_member, is_admin, is_editor) {}
	self.app_event_handler = function(event){ console.log("An unhandled event: ", message); }

	self.handle_message = function(message) {
		var event = Wind.Events.rehydrateEvent(JSON.parse(message));
		switch(event.type) {
			case 'Heartbeat':
				break;
			case 'AuthenticationResponse':
				if(event.authenticated){
					self.username = event.username;
				} else {
					self.username = null;
				}
				self.finished_auth = true;
				self.authentication_handler(self.username != null);
				break;
			case 'SubscribeResponse':
				if(event.joined) self.channelID = event.channel_id;
				self.subscription_handler(event.channel_id, event.joined, event.is_member, event.is_admin, event.is_editor);
				break;
			default:
				self.app_event_handler(event);
		}
	}

	self.ws_client = new Wind.WebSocketClient(Wind.WebSocketsPort, document.location.hostname, self.handle_message);
	self.open = function() {
		self.ws_client.onopen = self.__open;
		self.ws_client.onclose = self.__close;
		self.ws_client.onerror = function(err) { console.log('Error', err); };
		self.ws_client.open();
	}

	self.sendEvent = function(event){
		self.ws_client.send(event.toJSON());
	}

	self.authenticate = function() {
		if(!window.windSessionKey){
			console.log("No wind session key");
			return false;
		}
		self.sendEvent(new Wind.Events.AuthenticationRequest(window.windSessionKey));
		return true;
	}
	
	self.subscribe = function(channelID){
		self.sendEvent(new Wind.Events.SubscribeRequest(channelID));
	}
	
	self.sendHeartbeat = function(){
		self.sendEvent(new Wind.Events.Heartbeat());
		setTimeout(function(){ self.sendHeartbeat(); }, self.heartbeatFrequency);
	}
	

	self.close = function() {
		self.ws_client.close();
	}
	
	self.__open = function(){
		if(self.heartbeatTime == null) self.heartbeatTimeout = setTimeout(function(){ self.sendHeartbeat(); }, self.heartbeatFrequency);
		self.open_handler();
	}
	self.__close = function(){
		if(self.heartbeatTimeout != null){
			clearTimeout(self.heartbeatTimeout);
			self.heartbeatTimeout = null;
		}
		self.close_handler();
	}
	
}

Wind.escapeHTML = function(xml){
	if(xml == null || xml.length == 0){
		return xml;
	}
    return xml.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&apos;");
}

Wind.unescapeHTML = function(xml){
    return xml.replace(/&apos;/g,"'").replace(/&quot;/g,"\"").replace(/&gt;/g,">").replace(/&lt;/g,"<").replace(/&amp;/g,"&");
}

// sets up all the url parameters in a dictionary
Wind.parseLocationParameters = function(){
    	var paramPhrases = location.search.substring(1, location.search.length).split("&");
    	var paramDict = new Object();
    	for(var i=0; i < paramPhrases.length; i++){
    		paramDict[paramPhrases[i].split("=")[0]] = paramPhrases[i].split("=")[1];
	}
	return paramDict;
}

Wind.locationParameters = Wind.parseLocationParameters();

