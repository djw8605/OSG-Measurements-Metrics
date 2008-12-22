
import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages

setup(name="OSG-Gratia-Viewer",
      version="0.1",
      author="Brian Bockelman",
      author_email="bbockelm@math.unl.edu",
      url="http://t2.unl.edu/documentation/gratia_graphs",
      description="Python-based GIP Analyzer.",

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
     
      #setup_requires=["MySQL-python>1.2.0"],
      #install_requires=["pysqlite", "MySQL-python>1.2.0", "graphtool"],

      entry_points={
          'console_scripts': [
              'gip_count = gratia.tools.gip_count:main',
              'gip_record = gratia.tools.gip_record:main',
              'site_normalization = gratia.tools.site_normalization:main',
          ],
          'setuptools.installation' : [
              'eggsecutable = gratia.tools.gip_count:main'
          ]
      },

      namespace_packages = ['gratia', 'gratia.tools', 'gratia.gip']
      )


