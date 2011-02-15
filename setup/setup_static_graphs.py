
from distutils.core import setup

setup(name="GratiaStaticGraphs",
      version="0.3",
      author="Brian Bockelman",
      author_email="bbockelm@cse.unl.edu",
      url="http://t2.unl.edu/documentation/gratia_graphs",
      description="Static Graph Generator.",

      package_dir={"": "src"},
      packages=["gratia", "gratia.tools", "gratia.graphs"],

      data_files=[("/etc/cron.d", ["config/GratiaStaticGraphs.cron"]),
                  ("/usr/bin", ["config/static_graphs"]),
                  ("/etc", ["config/osg_graphs.conf"]),
                 ]

      )


