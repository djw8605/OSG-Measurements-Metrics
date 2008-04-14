#!/bin/bash

export GRAPHTOOL_ROOT=~/projects/GraphTool
export GRAPHTOOL_USER_ROOT=~/projects/GraphUsers/gratia
export CONFIG_ROOT=$GRAPHTOOL_USER_ROOT/config

export PYTHONPATH=$GRAPHTOOL_USER_ROOT/src:$GRAPHTOOL_ROOT/src:$PYTHONPATH
export PATH=$GRAPHTOOL_USER_ROOT/tools:$PATH

#export TTFPATH=$CMS_ROOT/$CMS_ARCH/external/py2-matplotlib/0.87.7/lib/python2.4/site-packages/matplotlib/mpl-data

# TODO:  Investigate.  Exporting HOME is bound to cause confustion, but there can be strange errors otherwise...
export MATPLOTLIBDATA=$CONFIG_ROOT

