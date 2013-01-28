import os, sys
import time
import threading
import readline
import cmd
import logging
import traceback
import datetime
import types

class Task(threading.Thread):
	def __init__(self, action, loopdelay, initdelay):
		"""The action is a function which will be called in a new thread every loopdelay microseconds, starting after initdelay microseconds"""
		self._action = action
		self._loopdelay = loopdelay
		self._initdelay = initdelay
		self._running = False
		self.last_alert_datetime = None
		threading.Thread.__init__(self)

	def run(self):
		"""There's no need to override this.  Pass your action in as a function to the __init__."""
		self._running = True
		if self._initdelay: time.sleep(self._initdelay)
		self._runtime = time.time()
		while self._running:
			start = time.time()
			self._action()
			self._runtime += self._loopdelay
			while(time.time() < self._runtime and self._running): time.sleep(1)
	
	def stop(self):
		self._running = False

class Scheduler:
	"""The class which manages starting and stopping of tasks."""
	def __init__(self):
		self._tasks = []
	
	def __repr__(self):
		rep = ''
		for task in self._tasks:
			rep += '%s\n' % `task`
		return rep
	
	def add_task(self, task):
		self._tasks.append(task)
	
	def start_all_tasks(self):
		for task in self._tasks: task.start()
	
	def stop_all_tasks(self):
		for task in self._tasks:
			if task.isAlive():
				task.stop()
				task.join()

def discover_classes(package_name, base_class):
	"""Returns a list of classes in app.module_name which is a subclass of base_class"""
	from django.conf import settings
	results = []
	for app_module_name in settings.INSTALLED_APPS:
		try:
			app = __import__(app_module_name)
			__import__('%s.%s' % (app_module_name, package_name))
			package = sys.modules['%s.%s' % (app_module_name, package_name)]
		except:
			continue
		for key in dir(package):
			attribute = getattr(package, key)
			if (type(attribute) == types.ClassType or type(attribute) == types.TypeType) and issubclass(attribute, base_class) and attribute != base_class and attribute not in results:
				results.append(attribute)
	return results

def discover_tasks(): return discover_classes('tasks', Task)

