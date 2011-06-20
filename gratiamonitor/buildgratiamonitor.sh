#!/bin/bash

rpmbuild --define "_topdir $PWD" -ba SPECS/gratiagraph-monitor.spec
