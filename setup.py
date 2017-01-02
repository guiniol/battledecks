from setuptools import setup

setup(name='Battle Decks',
      version='1.0',
      description='OpenShift App',
      author='Guillaume Brogi',
      author_email='gui-gui@netcourrier.com',
      url='http://www.python.org/sigs/distutils-sig/',
      install_requires=[
          'Flask>=0.11',
          'Flask-SQLAlchemy==2.1',
          'SQLAlchemy==1.1.4',
          'Requests==2.12.4',
          'lxml==3.4.4',
          'future==0.16.0',
          ],
     )
