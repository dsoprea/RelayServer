from setuptools import setup, find_packages
import sys, os

version = '1.0.0'

setup(name='relayserver',
      version=version,
      description="A relay-server to defeat NATs, with pools.",
      long_description="""\
A service that that acts as a single proxy between many individual clients and many instances of a server. As both the clients and the servers adapters initiate their connections to the relay server, this solution defeats NAT.""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='relay-server nat network client server',
      author='Dustin Oprea',
      author_email='myselfasunder@gmail.com',
      url='https://github.com/dsoprea/RelayServer',
      license='LGPL',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
