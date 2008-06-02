
import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages

setup(name="GratiaStaticGraphs",
      version="0.1",
      author="Brian Bockelman",
      author_email="bbockelm@math.unl.edu",
      url="http://t2.unl.edu/documentation/gratia_graphs",
      description="Static Graph Generator.",

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

      dependency_links = ['http://effbot.org/downloads/Imaging-1.1.6.tar.gz' \
                          '#egg=PIL-1.1.6'],     
      install_requires=["PIL"],

      entry_points={
          'console_scripts': [
              'static_graphs = gratia.tools.static_graphs:main',
          ],
          'setuptools.installation' : [
              'static_graphs = gratia.tools.static_graphs:main',
          ]
      },

      namespace_packages = ['gratia']
      )


