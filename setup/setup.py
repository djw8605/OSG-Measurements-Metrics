
import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages

setup(name="OSG-Gratia-Viewer",
      version="0.1",
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
     
      #setup_requires=["MySQL-python>1.2.0"],
      dependency_links = ['http://effbot.org/downloads/Imaging-1.1.6.tar.gz'
                          '#egg=PIL-1.1.6'],
      #install_requires=["PIL", "setuptools"],

      entry_points={
          'console_scripts': [
              'gip_count = gratia.tools.gip_count:main',
              'gip_record = gratia.tools.gip_record:main',
              'gratia_web_dev = gratia.tools.gratia_web_dev:main',
              'gratia_web = gratia.tools.gratia_web:main',
              'gridscan_download = gratia.tools.gridscan_download:main',
              'static_graphs = gratia.tools.static_graphs:main',
              'site_normalization = gratia.tools.site_normalization:main',
              'gip_subcluster_record = gratia.tools.gip_subcluster_record:main',
              'gratia_voms_query = gratia.tools.gratia_voms_query:main',
              'wlcg_pledge_email = gratia.tools.wlcg_pledge_email:main',
              'cms_summary = gratia.summary.dashboard_slurp:main',
              'ligo_summary = gratia.summary.ligo_query:main',
              'make_daemon_gratia = gratia.other.make_daemon:main',
              'rsv_calc = gratia.tools.rsv_calc:main',
              'metric_thumbnails = gratia.tools.metric_thumbnails:main',
          ],
          'setuptools.installation' : [
              'eggsecutable = gratia.tools.gratia_web:main'
          ]
      },

      data_files=[('/etc/init.d', ['config/GratiaWeb']),
          ('/etc/', ['config/wlcg_email.conf.rpmnew',
                     'config/DBParam.xml.rpmnew']),
          ('/usr/share/GratiaWeb/', ['config/gip_schema',
                                     'config/registration_schema']),
          ('/etc/cron.d/', ['config/gratia_data.cron']),
      ],

      namespace_packages = ['gratia']
      )


