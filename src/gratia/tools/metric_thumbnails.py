
import sys
import time
import urllib
import urllib2
import datetime

from xml.dom.minidom import parse

from atlas_statistics import dostats as do_atlas_stats

vo_hours = 'http://t2.unl.edu/gratia/xml/osg_vo_hours'
vo_count = 'http://t2.unl.edu/gratia/xml/osg_vo_count'

cms_transfers = 'http://t2.unl.edu/phedex/xml/quantity_cumulative'
datasvc_cms_transfers_prod = 'http://cmsweb.cern.ch/phedex/datasvc/json/prod/transferhistory'
datasvc_cms_transfers_debug = 'http://cmsweb.cern.ch/phedex/datasvc/json/debug/transferhistory'

CMS_owned = ['USCMS-FNAL', 'GLOW', 'Purdue', 'CIT_CMS_T2', 'Nebraska', 'MIT_CMS', 'UCSDT2', 'UFlorida']
ATLAS_owned = ['BNL_ATLAS_1', 'MWT2_UC', 'AGLT2', 'WT2', 'MWT2_IU', 'BU_ATLAS_Tier2', 'UTA_SWT2', 'OU_OCHEP_SWT2', 'SWT2_CPB', 'IU_OSG', 'UC_ATLAS_MWT2', 'OU_OSCER_ATLAS', 'UTA_DPCC']

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

def simple_results_parser(dom):
    data = {}
    pivots = dom.getElementsByTagName('pivot')
    for pivot_dom in pivots:
        pivot = pivot_dom.getAttribute('name')
        data_dom = pivot_dom.getElementsByTagName('d')[0]
        datum = float(str(data_dom.firstChild.data))
        data[pivot] = datum
    return data

def do_cms_stats(now):
    next_year = now.year + int(now.month == 12)
    next_month = (now.month % 12) + 1
    end = datetime.datetime(next_year, next_month, 1)
    info_dict = {'from_node': 'US', 'link': 'src', 'span': '86400'}
    info_dict['starttime'] = now.strftime('%Y-%m-%d %H:%M:%S')
    info_dict['endtime'] = end.strftime('%Y-%m-%d %H:%M:%S')
    info = urllib.urlencode(info_dict)
    url = cms_transfers + '?' + info
    from_data = results_parser(parse(urllib2.urlopen(url)))
    last_time = max(from_data.values()[0].keys())
    from_total = sum([from_data[i][last_time] for i in from_data])
    info_dict['link'] = 'dest'
    info_dict['to_node'] = 'US'
    del info_dict['from_node']
    info = urllib.urlencode(info_dict)
    url = cms_transfers + '?' + info
    to_data = results_parser(parse(urllib2.urlopen(url)))
    last_time = max(to_data.values()[0].keys())
    to_total = sum([to_data[i][last_time] for i in to_data])
    print "\tFrom US sites: %.3f PB" % (from_total/1000)
    print "\tTo US sites: %.3f PB" % (to_total/1000)

def sum_phedex_transferhistory_pb(results):
    results = eval(results, {'null': None}, {})
    results = results['phedex']
    total = 0
    for link_data in results['link']:
        for data in link_data['transfer']:
            total += int(data['done_bytes'])
    return total / 1000.**5

def do_cms_stats(now):
    next_year = now.year + int(now.month == 12)
    next_month = (now.month % 12) + 1
    end = datetime.datetime(next_year, next_month, 1)
    info_dict = {'from': 'T%_US_%', 'binwidth': '86400'}
    info_dict['starttime'] = now.strftime('%Y-%m-%d %H:%M:%S')
    info_dict['endtime'] = end.strftime('%Y-%m-%d %H:%M:%S')
    info = urllib.urlencode(info_dict)
    # From US sites; prod
    url = datasvc_cms_transfers_prod + '?' + info
    results = urllib2.urlopen(url).read()
    from_total = sum_phedex_transferhistory_pb(results)
    # debug
    url = datasvc_cms_transfers_debug + '?' + info
    results = urllib2.urlopen(url).read()
    from_total += sum_phedex_transferhistory_pb(results)

    # To US sites; prod
    info_dict['to'] = 'T%_US_%'
    del info_dict['from']
    info = urllib.urlencode(info_dict)
    url = datasvc_cms_transfers_prod + '?' + info
    results = urllib2.urlopen(url).read()
    to_total = sum_phedex_transferhistory_pb(results)
    # debug
    url = datasvc_cms_transfers_debug + '?' + info
    results = urllib2.urlopen(url).read()
    to_total = sum_phedex_transferhistory_pb(results)

    print "\tFrom US sites: %.3f PB" % from_total
    print "\tTo US sites: %.3f PB" % to_total


def dojobstats(now):
    next_year = now.year + int(now.month == 12)
    next_month = (now.month % 12) + 1
    end = datetime.datetime(next_year, next_month, 1)
    print "Job Statistics for %s to %s." % (now.strftime('%Y-%m-%d'),
        end.strftime('%Y-%m-%d'))
    start = now.strftime('%Y-%m-%d %H:%M:%S')
    end_str = end.strftime('%Y-%m-%d %H:%M:%S')
    info_dict = {'starttime': start, 'endtime': end_str, 'vo': 'cms|atlas'}
    info = urllib.urlencode(info_dict)
    url = vo_count + '?' + info
    cnt_data = simple_results_parser(parse(urllib2.urlopen(url)))

    url = vo_hours + '?' + info
    hours_data = simple_results_parser(parse(urllib2.urlopen(url)))

    six_months_prior = ((now.month-6) % 12)+1
    six_months_prior_year = now.year - int(six_months_prior > now.month)
    six_months = datetime.datetime(six_months_prior_year, six_months_prior, 1)
    info_dict['starttime'] = six_months.strftime('%Y-%m-%d %H:%M:%S')
    info = urllib.urlencode(info_dict)
    url = vo_hours + '?' + info
    six_months_hours_data = simple_results_parser(parse(urllib2.urlopen(url)))

    hours_in_month = 24*float((end - now).days)

    info_dict['starttime'] = start
    owned_sites = {}
    info_dict['vo'] = 'atlas'
    info_dict['facility'] = '|'.join(ATLAS_owned)
    info = urllib.urlencode(info_dict)
    url = vo_hours + '?' + info
    atotal_hours = simple_results_parser(parse(urllib2.urlopen(url)))['usatlas']
    owned_sites['usatlas'] = 100*atotal_hours/float(hours_data['usatlas'])
    info_dict['vo'] = 'cms'
    info_dict['facility'] = '|'.join(CMS_owned)
    info = urllib.urlencode(info_dict)
    url = vo_hours + '?' + info
    ctotal_hours = simple_results_parser(parse(urllib2.urlopen(url)))['cms']
    owned_sites['cms'] = 100*ctotal_hours/float(hours_data['cms'])

    owned_data = {}
    del info_dict['vo']
    info_dict['facility'] = '|'.join(ATLAS_owned)
    info = urllib.urlencode(info_dict)
    url = vo_hours + '?' + info
    total_hours = sum(simple_results_parser(parse(urllib2.urlopen(url)))\
        .values())
    owned_data['usatlas'] = 100*(1 - atotal_hours/float(total_hours))
    info_dict['facility'] = '|'.join(CMS_owned)
    info = urllib.urlencode(info_dict)
    url = vo_hours + '?' + info
    total_hours = sum(simple_results_parser(parse(urllib2.urlopen(url)))\
        .values())
    owned_data['cms'] = 100*(1 - ctotal_hours/float(total_hours))

    print "\tCMS total wall hours: %i" % hours_data['cms']
    print "\tATLAS total wall hours: %i" % hours_data['usatlas']
    print "\tCMS 6 months total wall hours: %i" % six_months_hours_data['cms']
    print "\tATLAS 6 months total wall hours: %i" % \
        six_months_hours_data['usatlas']
    print "\tCMS job count: %i" % cnt_data['cms']
    print "\tATLAS job count: %i" % cnt_data['usatlas']
    print "\t%% non-CMS work on CMS sites: %i" % owned_data['cms']
    print "\t%% non-ATLAS work on ATLAS sites: %i" % \
        owned_data['usatlas']
    print "\tCMS %% wall time on owned sites: %.2f" % owned_sites['cms']
    print "\tATLAS %% wall time on owned sites: %.2f" % owned_sites['usatlas']
    print "\tCMS Average # of CPUs used: %i" % \
        (hours_data['cms']/hours_in_month)
    print "\tATLAS Average # of CPUs used: %i" % \
        (hours_data['usatlas']/hours_in_month)
    
def main():
    if len(sys.argv) != 3:
        print "Usage: atlas_statistics.py <start> <end>"
        print "where <start> and <end> are of the form <year>-<month>."
        print "Example: atlas_statistics.py 2008-01 2008-08"
        sys.exit(1)
    start, end = sys.argv[1:]
    start = time.strptime(start, '%Y-%m')
    end = time.strptime(end, '%Y-%m')
    start = datetime.datetime(*start[:3])
    end = datetime.datetime(*end[:3])
    cur = start
    while cur <= end:
       dojobstats(cur)
       do_cms_stats(cur)
       do_atlas_stats(cur)
       next_year = cur.year + int(cur.month == 12)
       next_month = (cur.month % 12) + 1
       cur = datetime.datetime(next_year, next_month, 1)


if __name__ == '__main__':
    main()

