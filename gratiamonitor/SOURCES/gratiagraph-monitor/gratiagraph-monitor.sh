#!/bin/bash
ADDRESS='http://localhost:8100/gratia'
WGET='/usr/bin/wget'
DATE=`date`
RESTART='/sbin/service GratiaWeb restart'

wget -O /tmp/gratiatemp.txt --tries=3  --timeout=60  $ADDRESS >/dev/null 2>&1
if [ $? -ne 0 ]
then
	echo "$DATE Restarting Gratia Web - Gratia Request Timed Out" 
	$RESTART
fi
