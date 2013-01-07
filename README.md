OSG Measurement and Metrics
===========================

## Building RPM

First, you must build the source distribution:

    $ python setup/setup_Web.py sdist
    $ python setup/setup_Db.py sdist

Then copy the source distributions to the rpm SOURCES directory:

    $ cp dist/*.tar.gz ~/rpmbuild/SOURCES

Then use the rpmbuild command and the provided spec files to build the
package.

    $ rpmbuild -ba OSG-Measurements-Metrics-Db.spec
    $ rpmbuild -ba OSG-Measurements-Metrics-Web.spec



## License

   Copyright 2013 Brian Bockelman

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.




