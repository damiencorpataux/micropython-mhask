from setuptools import setup
import sdist_upip

setup(name='mhask',
      version='0.0.0',
      description="Micropython HTTP Asynchronous Service like Flask",
      long_description=open('README.md').read(),
      long_description_content_type="text/markdown",
      url='https://github.com/damiencorpataux/micropython-mhask',
      author='Damien Corpataux',
      # author_email='',
      license='MIT',
      cmdclass={'sdist': sdist_upip.sdist},
      packages=['mhask'],
      install_requires=['micropython-uasyncio', 'micropython-ulogging'])
