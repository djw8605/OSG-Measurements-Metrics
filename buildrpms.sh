#!/bin/bash

#first build the DB rpm
echo "Building Measurements-Metrics-Db rpm"
rm -rf setup.py setup.cfg
cp setup/setup_Db.py setup.py
cp setup/setup_Db.cfg setup.cfg

python setup.py bdist_rpm

echo "Building Measurements-Metrics-Web rpm"
rm -rf setup.py setup.cfg
cp setup/setup_Web.py setup.py
cp setup/setup_Web.cfg setup.cfg

python setup.py bdist_rpm

rm -rf setup.py setup.cfg

echo done...

