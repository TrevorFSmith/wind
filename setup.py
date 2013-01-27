import os
from setuptools import setup, find_packages

def read(fname): return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
	name = "wind",
	version = "0.0.1",
	author = "Trevor F. Smith",
	author_email = "subs@trevor.smith.name",
	description = "A WebSocket event system for Django.",
	license = "apache2.0",
	keywords = "django websockets events python",
	url = "https://github.com/TrevorFSmith/wind",
	packages = find_packages(
		exclude=[]
	),
	include_package_data = True,
	long_description=read('README.md'),
	classifiers=[
		"Development Status :: 3 - Alpha",
		"Topic :: Utilities",
		"License :: OSI Approved :: Apache 2.0",
	],
	scripts = [],
	install_requires=['django','south',],
)