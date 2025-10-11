# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in logistics/__init__.py
from logistics import __version__ as version

setup(
	name='logistics',
	version=version,
	description='Logistics',
	author='www.agilasoft.com',
	author_email='info@agilasoft.com',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
