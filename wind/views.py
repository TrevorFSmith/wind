import datetime
import calendar
import pprint
import traceback
import random
from urllib import unquote_plus

from django.conf import settings
from django.db.models import Q
from django.template import Context, loader
from django.http import HttpResponse, Http404, HttpResponseServerError, HttpResponseRedirect, HttpResponsePermanentRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib import auth
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.comments.models import Comment
from django.contrib.sites.models import Site
from django.utils.html import strip_tags
import django.contrib.contenttypes.models as content_type_models
from django.template import RequestContext
from django.core.cache import cache
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.template.loader import render_to_string
from django.utils import feedgenerator
from django.core.urlresolvers import reverse
from django.core.files import File

from models import ServerRegistration

@staff_member_required
def index(request): return render_to_response('wind/index.html', { 'server_registrations':ServerRegistration.objects.all() }, context_instance=RequestContext(request))

def test(request):
	if not settings.DEBUG: raise Http404
	alice, created = User.objects.get_or_create(username='alice', is_staff=True)
	if created: alice.set_password('1234')
	bob, created = User.objects.get_or_create(username='bob')
	if created: bob.set_password('1234')

	context = {
		'alice': alice,
		'bob': bob
	}
	return render_to_response('wind/test.html', context, context_instance=RequestContext(request))

def windjs(request):
	from wind.events import EVENTS
	return render_to_response('wind/wind.js', { 'events':EVENTS, 'web_sockets_port':settings.WEB_SOCKETS_PORT }, context_instance=RequestContext(request), mimetype='application/javascript')

# Copyright 2010,2011,2012 Trevor F. Smith (http://trevor.smith.name/) Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0 Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.