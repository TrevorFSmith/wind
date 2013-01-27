from django.contrib import admin
from django import forms
from django.forms.util import ErrorList

from models import *

class BaseMedia:
		css = { "all": ('wind/admin.css', )}

class ServerRegistrationAdmin(admin.ModelAdmin):
	class Media(BaseMedia):
		list_display = ('ip', 'port')
admin.site.register(ServerRegistration, ServerRegistrationAdmin)
