var echo = echo || {};
echo.views = echo.views || {};

echo.views.PageView = Backbone.View.extend({
	className: 'page-view span12',
	data: {},
	windClient: null,

	initialize: function(){
		_.bindAll(this);
		this.messageDisplay = $.el.div({'class':'message-display'});
		this.inputField = $.el.input();
		this.sendButton = $.el.button('Send');

		this.$el.append($.el.div('Connecting to ' + this.options.host + '...'));
		this.open();
	},
	open: function(){
		this.windClient = new Wind.Client(this.options.sessionKey);
		this.windClient.openHandler = this.onOpen;
		this.windClient.authenticationHandler = this.onAuth;
		this.windClient.closeHandler = this.onClose;
		this.windClient.appEventHandler = this.onEvent;
		this.windClient.subscriptionHandler = this.onSubscribe;
		this.windClient.open();
	},
	onOpen: function(){
		this.windClient.authenticate();
	},
	onAuth: function(success){
		if(!success){
			this.$el.empty();
			this.$el.append($.el.div('Could not auth, dang it.'));
			this.windClient.close();
			return;
		}
		this.windClient.subscribe('chatter');
	},
	onSubscribe: function(channel_id, joined, is_member, is_admin, is_editor){
		if(!joined){
			this.$el.empty();
			this.$el.append($.el.div('Could not subscribe, dang it.'));
			this.windClient.close();
			return;
		}

		this.$el.empty();
		this.$el.append(this.inputField);
		this.$el.append(this.sendButton);
		this.$el.append(this.messageDisplay);
		$(this.inputField).focus();
		$(this.sendButton).click(this.sendMessage);
		$(this.inputField).change(this.sendMessage);
		$(this.inputField).focus();
	},
	onClose: function(){
		console.log("Wind client closed");
		this.$el.empty();
		this.$el.append("The connection has closed.");
	},
	onEvent: function(event){
		switch(event.type){
			case Wind.Events.EchoResponse.prototype.name:
				$(this.messageDisplay).prepend($.el.div(event.message));
				break;
			default:
				console.log("Unhandled message", event);
		}
	},
	sendMessage: function(){
		var message = $(this.inputField).val();
		$(this.inputField).val('');
		this.windClient.sendEvent(new Wind.Events.EchoRequest(message));
	}
});
