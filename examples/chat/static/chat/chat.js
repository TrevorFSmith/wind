var chat = chat || {};
chat.views = chat.views || {};

chat.GUEST_NAMES = ['Flower', 'Moon', 'Rouge', 'Manipedi', 'Printer', 'Payroll', 'Flipflop', 'Powder', 'Cheese']
chat.CHANNEL_NAME = 'chatter';

chat.randomGuestName = function(){
	return chat.GUEST_NAMES[Math.floor((Math.random() * chat.GUEST_NAMES.length))];
}

chat.views.PageView = Backbone.View.extend({
	className: 'page-view span12',
	data: {},
	windClient: null,

	initialize: function(){
		_.bindAll(this);
		this.username = 'Guest ' + chat.randomGuestName() + ' ' + chat.randomGuestName() + ' ' + chat.randomGuestName();
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
		if(this.options.sessionKey){
			this.windClient.authenticate();
		} else {
			this.windClient.subscribe(chat.CHANNEL_NAME);
		}
	},
	onTokenSet: function(){
		this.$el.empty();
		this.$el.append(this.inputField);
		this.$el.append(this.sendButton);
		this.$el.append(this.messageDisplay);
		$(this.inputField).focus();
		$(this.sendButton).click(this.sendMessage);
		$(this.inputField).change(this.sendMessage);
		$(this.inputField).focus();
	},
	onAuth: function(success){
		if(!success){
			this.$el.empty();
			this.$el.append($.el.div('Could not auth, dang it.'));
			this.windClient.close();
			return;
		}
		this.username = this.windClient.username;
		this.windClient.subscribe(chat.CHANNEL_NAME);
	},
	onSubscribe: function(channel_id, joined, is_member, is_admin, is_editor){
		if(!joined){
			this.$el.empty();
			this.$el.append($.el.div('Could not subscribe, dang it.'));
			this.windClient.close();
			return;
		}
		this.windClient.sendEvent(new Wind.Events.SetToken(this.options.chatToken));
	},
	onClose: function(){
		console.log("Wind client closed");
		this.$el.empty();
		this.$el.append("The connection has closed.");
	},
	onEvent: function(event){
		switch(event.type){
			case Wind.Events.SendChatter.prototype.eventName:
				$(this.messageDisplay).prepend($.el.div($.el.span(event.username + ': '), event.message));
				break;
			case Wind.Events.TokenSet.prototype.eventName:
				this.onTokenSet();
				break;
			default:
				console.log("Unhandled message", event);
		}
	},
	sendMessage: function(){
		var message = $(this.inputField).val();
		$(this.inputField).val('');
		this.windClient.sendEvent(new Wind.Events.SendChatter(this.username, message));
	}
});
