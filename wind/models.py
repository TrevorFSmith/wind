import os
import re
import time
import uuid
import urllib
import random
import logging
import calendar
import traceback
import unicodedata
from datetime import datetime, timedelta, date

from django.db import models
from django.db.models import Q
from django.conf import settings
from django.db.models import signals
from django.dispatch import dispatcher
from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.db.models.signals import post_save
from django.utils.encoding import force_unicode
from django.template.loader import render_to_string

from handler import to_json

def generate_key():
	key = uuid.uuid4().hex
	try:
		while SessionKey.objects.filter(key=key).count() > 0:
			key = uuid.uuid4().hex
	except:
		pass # This fails during DB setup
	return key

class SessionKey(models.Model):
	"""Stores a key used to authenticate a User in a wind session."""
	user = models.ForeignKey(User, unique=True, )
	key = models.CharField(max_length=128, blank=False, default=generate_key, unique=True)

	def reset_key(self):
		self.key = generate_key()
		self.save()

class ServerRegistrationManager(models.Manager):
	def broadcast_event(self, session_key, event, channel_id=None, wait_for_responses=False):
		if not wait_for_responses:
			for reg in self.all(): reg.send_event(session_key, event, channel_id, wait_for_responses)
			return None
		responses = []
		for reg in self.all(): responses.append(reg.send_event(session_key, event, channel_id, wait_for_responses))
		return responses
	
	@property
	def first_server(self):
		if len(self.all()) == 0: return None
		return self.all()[0]

class ServerRegistration(models.Model):
	"""A server's address in this cluster"""
	ip = models.IPAddressField()
	port = models.IntegerField()
	
	objects = ServerRegistrationManager()

	def send_event(self, session_key, event, channel_id=None, wait_for_response=False):
		event_handler = EventHandler()
		client = Client(session_key, self.ip, self.port, '%s:80' % self.ip, event_handler.handle_event)
		client.authenticate()
		in_event = event_handler.events.get(True, 10)
		if not in_event.authenticated: raise Exception('Could not authenticate against the server', in_event)
		if channel_id:
			client.subscribe(channel_id)
			in_event = event_handler.events.get(True, 10)
			if not in_event.joined: raise Exception('Could not join the channel %s', channel_id)
		client.send_event(event)
		if not wait_for_response:
			client.close()
			return
		in_event = event_handler.events.get(True, 10)
		client.close()
		return in_event

	@property
	def origin(self): return 'http://%s:%s/' % (self.ip, self.port)

	def fetch_pool_info(self):
		try:
			event_handler = EventHandler()
			client = Client(settings.WEB_SOCKETS_SECRET, self.ip, self.port, '%s:80' % self.ip, event_handler.handle_event)
			client.authenticate()
			event = event_handler.events.get(True, 10)
			if not event.authenticated: raise Exception('Could not authenticate against the server')
			client.request_server_info()
			event = event_handler.events.get(True, 10)
			client.close()
			return event.infos
		except:
			traceback.print_exc()
			return []

def key_from_user(user): return SessionKey.objects.get(user=user).key
User.session_key = property(key_from_user)

def create_session_key(sender, instance, created, **kwargs):
	if created: SessionKey.objects.create(user=instance)
post_save.connect(create_session_key, sender=User)

# Copyright 2010,2011,2012 Trevor F. Smith (http://trevor.smith.name/) Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0 Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.