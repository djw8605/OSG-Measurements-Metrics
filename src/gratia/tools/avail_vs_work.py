#!/usr/bin/env python

import os
import sys
import urllib
import urllib2
import datetime

from xml.dom.minidom import parse

from graphtool.tools.common import convert_to_datetime, expand_string
from graphtool.graphs.common_graphs import ScatterPlot

avail_url = 'http://t2.unl.edu/gratia/xml/avail_summary_daily'
work_url = 'http://t2.unl.edu/gratia/xml/facility_hours_bar_smry'

def results_parser(dom):
    data = {}
    pivots = dom.getElementsByTagName('pivot')
    for pivot_dom in pivots:
        pivot = pivot_dom.getAttribute('name')
        pivot_dict = {}
        data[pivot] = pivot_dict
        groups = pivot_dom.getElementsByTagName('group')
        for group_dom in groups:
            group = group_dom.getAttribute('value')
            try:
                group = convert_to_datetime(group)
            except:
                pass
            data_dom = group_dom.getElementsByTagName('d')[0]
            datum = float(str(data_dom.firstChild.data))
            pivot_dict[group] = datum
    return data

def get_site_work(site, start, end):
    info = {'facility': site}
    info['starttime'] = start.strftime('%Y-%m-%d %H:%M:%S')
    info['endtime'] = end.strftime('%Y-%m-%d %H:%M:%S')
    info = urllib.urlencode(info)
    dom = parse(urllib2.urlopen(work_url, info))
    return results_parser(dom)

def get_site_avail(site, start, end):
    info = {'facility': site}
    info['starttime'] = start.strftime('%Y-%m-%d %H:%M:%S')
    info['endtime'] = end.strftime('%Y-%m-%d %H:%M:%S')
    info = urllib.urlencode(info)
    dom = parse(urllib2.urlopen(avail_url, info))
    return results_parser(dom) 

def get_sites_data(sites):
    end = datetime.datetime.now()
    start = end - datetime.timedelta(30, 0)
    site = '|'.join(sites)
    work_results = get_site_work(site, start, end)
    avail_results = get_site_avail(site, start, end)
    results = {}
    for pivot in work_results:
        if pivot not in avail_results:
            continue
        pivot_dict = {}
        results[pivot] = pivot_dict
        pivot_work_dict = work_results[pivot]
        pivot_avail_dict = avail_results[pivot]
        new_pivot_work_dict = {}
        new_pivot_avail_dict = {}
        for group, datum in pivot_work_dict.items():
            new_pivot_work_dict[group.date()] = datum
        for group, datum in pivot_avail_dict.items():
            new_pivot_avail_dict[group.date()] = datum
        for group, datum in new_pivot_work_dict.items():
            if group not in new_pivot_avail_dict:
                continue
            pivot_dict[group] = datum, new_pivot_avail_dict[group]
    return results

def main():
    sites = sys.argv[1:]
    if len(sites) == 0:
        print "Must specify at least one site to plot!"
        sys.exit(1)
    url_results = get_sites_data(sites)
    results = {}
    # Determine the maximum amount of work done:
    for pivot, groups in url_results.items():
        all_work = []
        for group, data in groups.items():
            all_work.append(data[0])
        max_work = max(all_work)
        for group, data in groups.items():
            groups[group] = data[0]/max_work, data[1]
    ugly_points = 0
    bad_points = 0
    points = 0
    for pivot, groups in url_results.items():
        results_dict = {}
        results[pivot] = results_dict
        for group, data in groups.items():
            points += 1
            if data[1] > .01 and data[0] > data[1] + .1:
                ugly_points += 1
            if data[1] < .01 and data[0] > .1:
                bad_points += 1
            results_dict[data] = .001
    print "Good points: %i; Bad points: %i; Ugly points: %i." % (points,
        bad_points, ugly_points)
    file = open(expand_string('$HOME/tmp/avail_vs_work.png',os.environ),'w')
    SP = ScatterPlot()
    metadata = {'title': 'Computation hours vs. RSV Availability', \
                'subtitle': 'Sites %s' % ', '.join(sites), \
                'xlabel': 'Normalized amount of work', \
                'ylabel': 'RSV availability', \
               }
    SP(results, file, metadata)
        
if __name__ == '__main__':
    main()

