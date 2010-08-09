
from setuptools import setup, find_packages

setup(name="AccountingView",
      version="0.2.3",
      author="Brian Bockelman",
      author_email="bbockelm@math.unl.edu",
      url="http://t2.unl.edu/documentation/gratia_graphs",
      description="Python-based Gratia Viewer.",

      package_dir={"": "src"},
      packages=find_packages("src"),
      include_package_data=True,

      classifiers = [
          'Development Status :: 2 - Pre-Alpha',
          'Intended Audience :: Developers',
          'Programming Language :: Python',
          'Natural Language :: English',
          'Operating System :: POSIX'
      ],
     
      entry_points={
          'console_scripts': [
              'gratia_basic_web_dev = gratia.tools.gratia_basic_web_dev:main',
              'gratia_basic_web = gratia.tools.gratia_basic_web:main',
              'static_graphs = gratia.tools.static_graphs:main',
              'make_daemon_gratia = gratia.other.make_daemon:main',
          ],
          'setuptools.installation' : [
              'eggsecutable = gratia.tools.gratia_web:main'
          ]
      },

      data_files=[
          ('/etc/init.d', ['config/GratiaBasicWeb']),
          ('/etc/', ['config/DBParam_basic.xml.rpmnew']),
      ],

      namespace_packages = ['gratia']
      )


