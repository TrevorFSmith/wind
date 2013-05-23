function runWindTests(){
	asyncTest('Channel subscriptions', function(){
		// This tests that alice (a staff account) can create and subscribe to the testChannelClass
		// It also tests that bob cannot because of the testChannelClass's custom subscription python code
		var testChannelClass = 'wind.events.TestChannel';
		var aliceWindClient = null;
		var bobWindClient = null;
		var readyForClose = false;
		var testChannelId = 'test_channel_' + (new Date().getTime());
		function createCallback(clients){
			ok(clients.length == 2, 'Received wind clients: ' + clients);
			aliceWindClient = clients[0];
			ok(aliceWindClient.username == 'alice')
			aliceWindClient.appEventHandler = aliceEventHandler;
			aliceWindClient.closeHandler = function(){
				ok(readyForClose, 'Alice\'s client closed');
				start();
			}
			aliceWindClient.subscriptionHandler = function(channel_id, joined, is_member, is_admin, is_editor){
				ok(joined, 'Alice joined channel ' + channel_id);
				bobWindClient.subscribe(testChannelId);
			}

			bobWindClient = clients[1];
			ok(bobWindClient.username == 'bob');
			bobWindClient.closeHandler = function(){
				ok(readyForClose, 'Bob\'s client closed');
				aliceWindClient.close();
			}
			bobWindClient.subscriptionHandler = function(channel_id, joined, is_member, is_admin, is_editor){
				ok(joined == false, 'Bob was refused subscription to the private channel ' + channel_id);
				readyForClose = true;
				bobWindClient.close();
			}
			aliceWindClient.sendEvent(new Wind.Events.CreateChannelRequest(testChannelClass, testChannelId));
		}
		function aliceEventHandler(event){
			switch(event.type){
				case Wind.Events.ChannelCreated.prototype.name:
					ok(event.channel_id, 'Test channel created')
					aliceWindClient.subscribe(testChannelId);
					break;
				default:
					console.log('Unhandled event', event);
			}
		}
		createAndSubscribe([aliceSession, bobSession], null, createCallback, true);
	});

	asyncTest('Open and close', function(){
		var windClient = new Wind.Client(aliceSession);
		windClient.openHandler = handleOpen;
		windClient.closeHandler = handleClose;
		windClient.authenticationHandler = handleAuthentication;
		windClient.subscriptionHandler = handleSubscription;
		windClient.appEventHandler = appEventHandler;
		windClient.open();

		function handleOpen(){
			windClient.authenticate();
		}

		var readyForClose = false;
		function handleClose(){
			ok(readyForClose, "Closed at the appropriate time.");
			start();
		}

		function handleAuthentication(success){
			ok(success, 'Authenticated');
			windClient.createChannel(null, 'test_channel');
			windClient.subscribe('test_channel');
		};

		function handleSubscription(channel_id, joined, is_member, is_admin, is_editor){
			ok(joined, 'Joined channel ' + channel_id);
			readyForClose = true;
			windClient.close();
		}

		function appEventHandler(event){
			switch(event.type) {
				case 'ChannelExists':
				case 'ChannelCreated':
					break;
				default:
					console.log("Unhandled event", event);
			}
		}
	});

	asyncTest('Echo messaging', function(){
		// This test creates two clients for alice (who is staff) and bob, both subscribed to a test channel
		// Then alice sends an echo request, 'Foo', then bob sends 'Bar', then alice sends 'Terminal'
		// This test ensures that each client only gets their own echos.

		var windClient = null;
		var bobWindClient = null;
		var echoMessage = 'Foo';
		var bobEchoMessage = 'Bar';
		var terminalMessage = 'Terminal';
		var readyForClose = false;
		function createCallback(clients){
			ok(clients.length == 2, 'Received wind clients: ' + clients);
			windClient = clients[0];
			windClient.appEventHandler = appEventHandler;

			bobWindClient = clients[1];
			bobWindClient.appEventHandler = bobEventHandler;

			windClient.sendEvent(new Wind.Events.EchoRequest(echoMessage));
			windClient.closeHandler = function(){
				ok(readyForClose, 'Ready for close');
				start();
			}
		}
		function appEventHandler(event){
			switch(event.type){
				case Wind.Events.EchoResponse.prototype.name:
					ok(event, 'Received echo response');
					if(event.message == echoMessage){
						bobWindClient.sendEvent(new Wind.Events.EchoRequest(bobEchoMessage));
						return;
					} else if(event.message == terminalMessage){
						readyForClose = true;
						windClient.close();
						return;
					} else {
						ok(false, 'Received unknown echo: ' + event.message);
					}
					break;
				default:
					console.log('Unhandled event', event);
			}
		}
		function bobEventHandler(event){
			switch(event.type){
				case Wind.Events.EchoResponse.prototype.name:
					ok(event, 'Received echo response');
					ok(event.message == bobEchoMessage, 'Bob received appropriate echo: ' + echoMessage);
					windClient.sendEvent(new Wind.Events.EchoRequest(terminalMessage));
					break;
				default:
					console.log('Unhandled event', event);
			}
		}
		createAndSubscribe([aliceSession, bobSession], 'test_messaging', createCallback, true);
	});
}

function createAndSubscribe(sessionKeyArray, channelId, callback, createChannel){
	// Create a client for each session key in sessionKeyArray
	// If channelId is not null, subscribe each client to channelId
	// Then call callback with an array of clients
	// If createChannel is true, the first sessionKey must be for a staff account, or the channel creation will fail
	var results = [];
	function subscribeCallback(client){
		results[results.length] = client;
		if(sessionKeyArray.length == results.length){
			callback(results);
			return;
		}
		createAndSubscribeOne(sessionKeyArray[results.length], channelId, subscribeCallback, false);
	}
	createAndSubscribeOne(sessionKeyArray[0], channelId, subscribeCallback, createChannel);
}

function createAndSubscribeOne(sessionKey, channelId, callback, createChannel){
	// Creates a Wind.Client, opens a connection
	// If channelId is not null, attempt to subscribe
	var windClient = new Wind.Client(sessionKey);

	function resetClientHandlers(){
		windClient.openHandler = function() { };
		windClient.closeHandler = function(){ console.log('Closed')};
		windClient.appEventHandler = function(){ console.log("Unhandled event", event); }
		windClient.subscriptionHandler = function(){ };
	}

	windClient.openHandler = function() {
		windClient.authenticate();
	};

	windClient.closeHandler = function(){
		ok(false, 'Should not have closed.');
	}			

	windClient.appEventHandler = function(event){
		switch(event.type) {
			case 'ChannelExists':
			case 'ChannelCreated':
				break;
			default:
				console.log("Unhandled event", event);
		}
	}

	windClient.authenticationHandler = function(success){
		ok(success, 'Authenticated: ' + windClient.username);
		if(channelId == null){
			resetClientHandlers();
			callback(windClient);
			return;
		}
		if(createChannel){
			windClient.createChannel(null, channelId);
		}
		windClient.subscribe(channelId);
	};

	windClient.subscriptionHandler = function(channel_id, joined, is_member, is_admin, is_editor){
		ok(joined, 'Joined channel ' + channel_id);
		resetClientHandlers();
		callback(windClient);
	};
	windClient.open();
}
