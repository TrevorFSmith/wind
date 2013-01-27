import os
import sys
import time
import ConfigParser

from django.template.defaultfilters import slugify
from django.core.management.base import BaseCommand, CommandError
from django.core.files import File

class Command(BaseCommand):
	"""Runs the Wind event server."""
	help = "Runs the Wind event server."
	requires_model_validation = True

	def handle(self, *labels, **options):
		from wind.server import Server
		server = Server()
		server.start()
		try:
			while True: time.sleep(10000000)
		except (KeyboardInterrupt, SystemExit):
			server.stop()
			sys.exit()

# Copyright 2010,2011,2012 Trevor F. Smith (http://trevor.smith.name/) Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0 Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
