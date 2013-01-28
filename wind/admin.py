from django.contrib import admin
from django import forms
from django.forms.util import ErrorList

from models import ServerRegistration

class ServerRegistrationAdmin(admin.ModelAdmin):
	list_display = ('ip', 'port')
admin.site.register(ServerRegistration, ServerRegistrationAdmin)
