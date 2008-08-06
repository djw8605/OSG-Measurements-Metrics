#!/usr/bin/env python

import os
import sys
import urllib
import urllib2
import datetime

from xml.dom.minidom import parse

from graphtool.tools.common import convert_to_datetime, expand_string
from graphtool.graphs.common_graphs import ScatterPlot

gip_url = 'http://t2.unl.edu/gratia/xml/gip_facility'
gratia_url = 'http://t2.unl.edu/gratia/xml/facility_hours_bar_smry'

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

def get_site_gratia(site, start, end):
    info = {'facility': site}
    info['starttime'] = start.strftime('%Y-%m-%d %H:%M:%S')
    info['endtime'] = end.strftime('%Y-%m-%d %H:%M:%S')
    info = urllib.urlencode(info)
    dom = parse(urllib2.urlopen(gratia_url, info))
    return results_parser(dom)

def get_site_gip(site, start, end):
    info = {'facility': site, 'span': 86400}
    info['starttime'] = start.strftime('%Y-%m-%d %H:%M:%S')
    info['endtime'] = end.strftime('%Y-%m-%d %H:%M:%S')
    info = urllib.urlencode(info)
    print gip_url + '?' + info
    dom = parse(urllib2.urlopen(gip_url, info))
    return results_parser(dom) 

def get_sites_data(sites):
    end = datetime.datetime.now()
    start = end - datetime.timedelta(30, 0)
    site = '|'.join(sites)
    gratia_results = get_site_gratia(site, start, end)
    gip_results = get_site_gip(site, start, end)
    results = {}
    for pivot in gratia_results:
        if pivot not in gip_results:
            continue
        pivot_dict = {}
        results[pivot] = pivot_dict
        pivot_gratia_dict = gratia_results[pivot]
        pivot_gip_dict = gip_results[pivot]
        new_pivot_gratia_dict = {}
        new_pivot_gip_dict = {}
        for group, datum in pivot_gratia_dict.items():
            new_pivot_gratia_dict[group.date()] = datum
        for group, datum in pivot_gip_dict.items():
            new_pivot_gip_dict[group.date()] = datum
        for group, datum in new_pivot_gratia_dict.items():
            if group not in new_pivot_gip_dict:
                continue
            pivot_dict[group] = datum, new_pivot_gip_dict[group]
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
        all_gratia = []
        all_gip = []
        for group, data in groups.items():
            all_gratia.append(data[0])
            all_gip.append(data[1])
        max_gratia = max(max(all_gratia), .1)
        max_gip = max(max(all_gip), .1)
        for group, data in groups.items():
            groups[group] = data[0]/max_gratia, data[1]/max_gip
    for pivot, groups in url_results.items():
        results_dict = {}
        results[pivot] = results_dict
        for group, data in groups.items():
            results_dict[data] = .001
    file = open(expand_string('$HOME/tmp/gip_vs_gratia.png',os.environ),'w')
    SP = ScatterPlot()
    metadata = {'title': 'Gratia vs. GIP', \
                'subtitle': 'Sites %s' % ', '.join(sites), \
                'xlabel': 'Gratia reported normalized amount of work', \
                'ylabel': 'GIP reported normalized amount of work', \
                'height': '800', \
               }
    SP(results, file, metadata)
        
if __name__ == '__main__':
    main()

