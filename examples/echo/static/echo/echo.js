var echo = echo || {};
echo.views = echo.views || {};

echo.views.PageView = Backbone.View.extend({
	className: 'page-view span12',
	data: {},
	socket: null,

	initialize: function(){
		_.bindAll(this);
		this.messageDisplay = $.el.ul();
		this.inputField = $.el.input();
		this.sendButton = $.el.button('Send');

		this.$el.append($.el.div('Connecting to ' + this.options.host + '...'));
		this.open();
	},

	open: function(){
		try {
			this.socket = new WebSocket("ws://" + this.options.host + "/echo");
		} catch (e) {
			this.socket = new MozWebSocket("ws://" + this.options.host + "/echo");
		}
		this.socket.onopen = this.onOpen;
		this.socket.onmessage = this.onMessage;
		this.socket.onclose = this.onClose;
	},

	onOpen: function(){
		console.log("Socket opened", arguments);
		this.$el.empty();
		this.$el.append(this.inputField);
		this.$el.append(this.sendButton);
		this.$el.append(this.messageDisplay);

		$(this.sendButton).click(this.sendMessage);
		$(this.inputField).change(this.sendMessage);
		$(this.inputField).focus();
	},
	sendMessage: function(){
		var message = $(this.inputField).val();
		$(this.inputField).val('');
		this.socket.send(message);
	},
	onClose: function(){
		console.log("Socket closed", arguments);
		this.$el.empty();
		this.$el.append("The WebSocket connection has closed.");
	},

	onMessage: function(e){
		console.log("Received message", e);
		this.messageDisplay.append($.el.li(e.data));
	},

	render: function(){
		return this;
	},
});
