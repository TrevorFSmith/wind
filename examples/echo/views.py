import datetime
import traceback

from django.db.models import Q
from django.contrib import auth
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.template import RequestContext
from django.contrib.auth.models import User
from django.template import Context, loader
from django.contrib.sites.models import Site
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, Http404, HttpResponseServerError, HttpResponseRedirect, HttpResponsePermanentRedirect

def index(request): return render_to_response('echo/index.html', { }, context_instance=RequestContext(request))
