
import math
import sets
import time
import urllib
import urllib2
import datetime
import calendar
import json

from xml.dom.minidom import parse

import cherrypy
from pkg_resources import resource_stream
from auth import Authenticate
from gratia.database.metrics import NormalizationConstants
from wlcg_json_data import WLCGWebUtil

class JOTReporter(Authenticate):


    def uslhc_table(self, month=None, year=None, **kw):
        data = dict(kw)
        self.user_auth(data)
        self.user_roles(data)
        data['cmp'] = cmp
        data['error'] = None

        starttime, endtime, month, year = self.get_times(month, year)
        data['month'] = month
        data['month_name'] = calendar.month_name[month]
        data['year'] = year
        data['title'] = 'USLHC JOT Report for %s %i' % (data['month_name'],
            data['year'])

        info = {\
            'starttime': starttime.strftime('%Y-%m-%d %H:%M:%S'),
            'endtime':   endtime.  strftime('%Y-%m-%d %H:%M:%S'),
            'exclude-vo': 'unknown',
            'exclude-user': 'Sfiligoi',
        }
        cpu_hours = self.globals['GratiaPieQueries'].osg_facility_cpu_hours(\
            **info)[0]
        wall_hours = self.globals['GratiaPieQueries'].osg_facility_hours(\
            **info)[0]

        info['vo'] = 'atlas|cms|alice'
        lhc_cpu_hours = self.globals['GratiaPieQueries'].\
            osg_facility_cpu_hours(**info)[0]
        lhc_wall_hours = self.globals['GratiaPieQueries'].\
            osg_facility_hours(**info)[0]

        associations = self.globals['RSVQueries'].service_to_resource()[0]
        associations = associations.keys()
        new_assoc = {}
        for service, resource in associations:
            new_assoc.setdefault(resource, sets.Set())
            new_assoc[resource].add(service)
        new_assoc.setdefault('GLOW', ['CE'])

        federations = self.globals['RSVQueries'].resource_to_federation()[0]
        federations.setdefault('UTA_SWT2', 'US-SWT2')
        federations.setdefault('SWT2_CPB', 'US-SWT2')
        federations.setdefault('AGLT2', 'US-AGLT2')
        resource_to_remove = []
        for res in federations:
            if 'CE' not in new_assoc.get(res, []):
                resource_to_remove.append(res)
        print "\n\n"
        print new_assoc
        print federations
        for res in resource_to_remove:
            if res in federations:
                del federations[res]

        norms = self.site_normalization_jot(month, year, federations.keys())

        del info['exclude-vo']
        #resource_reliability = self.globals['RSVSummaryQueries'].\
        #    reli_summary_monthly(**info)[0]
        #resource_availability = self.globals['RSVSummaryQueries'].\
        #    avail_summary_monthly(**info)[0]
        gv_data = self.get_gridview(month, year, federations)

	data['mou']={}
        data['reliability'] = {}
        data['availability'] = {}
        data['cpu'] = {}
        data['count'] = {}
        data['wall'] = {}
        data['lhc_cpu'] = {}
        data['lhc_wall'] = {}
        days_in_month =  calendar.monthrange(year, month)[1]
	atlas_pledge, cms_pledge,atlas_dict, cms_dict, alice_pledge, alice_dict=WLCGWebUtil().wlcg_pledges(month, year)
        #data['mou'] = self.pledges(month, year)
	#int(days_in_month*.67*24*val)
        for key in atlas_pledge:
            data['mou'][key] = days_in_month*.67*24*int(atlas_pledge[key]['pledge'])
        for key in cms_pledge:
            data['mou'][key] = days_in_month*.67*24*int(cms_pledge[key]['pledge'])
        for key in alice_pledge:
            data['mou'][key] = days_in_month*.67*24*int(alice_pledge[key]['pledge'])
        for resource, fed in federations.items():
            print "TRACE Resource %s associated with federation %s, resource %s with wall hours %s. Norm factor %s " % (resource, fed, resource, wall_hours.get(resource, 0), norms[resource])
            #data['reliability'].setdefault(fed, 0)
            #data['reliability'][fed] +=resource_reliability.get(resource, {}).\
            #    get(datetime.datetime(year, month, 1, 0, 0, 0), (0, ))[0]
            #data['availability'].setdefault(fed, 0)
            #data['availability'][fed] += resource_availability.get(resource,
            #    {}).get(datetime.datetime(year, month, 1, 0, 0, 0), (0, ))[0]
            data['cpu'].setdefault(fed, 0)
            data['cpu'][fed] += cpu_hours.get(resource, 0)*norms[resource]
            data['count'].setdefault(fed, 0)
            data['count'][fed] += 1
            data['wall'].setdefault(fed, 0)
            data['wall'][fed] += wall_hours.get(resource, 0)*norms[resource]
            data['lhc_cpu'].setdefault(fed, 0)
            data['lhc_cpu'][fed] += lhc_cpu_hours.get(resource, 0)*\
                norms[resource]
            data['lhc_wall'].setdefault(fed, 0)
            data['lhc_wall'][fed] += lhc_wall_hours.get(resource, 0)*\
                norms[resource]
            data['mou'].setdefault(fed, 0)
	    print "TRACE Resource %s associated with federation %s lhc_cpu (%s * %s ) Cumulative  %s "%(resource, fed, lhc_cpu_hours.get(resource, 0), norms[resource], data['lhc_cpu'][fed], )
        data['cms_feds'] = []
        data['atlas_feds'] = []
        data['alice_feds'] = []
        all_feds = sets.Set(federations.values())
        for fed in all_feds:
            # TODO: OIM should provide ownership info.
            if cms_dict.has_key(fed):
                data['cms_feds'].append(fed)
            if atlas_dict.has_key(fed):
                data['atlas_feds'].append(fed)
            if alice_dict.has_key(fed):
                data['alice_feds'].append(fed)
            data['availability'][fed] = gv_data.get(fed, [0, 0])[1]
            data['reliability'][fed] = gv_data.get(fed, [0, 0])[0]
        for key in data['atlas_feds']:
		print "atlas_feds = %s %s "% (key, data['wall'][key])
        data['round'] = round
        return data

    def get_times(self, month, year):
        if month == None:
            month = datetime.datetime.now().month
            if month == 1:
                month = 12
            else:
                month -= 1
        else:
            month = int(month)
        next_month = month % 12 + 1
        if year == None:
            year = datetime.datetime.now().year - int(month == 12)
        else:
            year = int(year)
        next_year = year + int(month == 12)
        starttime = datetime.datetime(year, month, 1, 0, 0, 0)
        endtime = datetime.datetime(next_year, next_month, 1, 0, 0, 0)
        return starttime, endtime, month, year

    def get_apel_data_jot_since201203(self, month, year):
        apel_url = self.metadata.get('apel_url', 'http://gr7x3.fnal.gov:8880/gratia-data/interfaces/apel-lcg/%i-%02i.summary.dat'\
            % (year, month))
        usock = urllib2.urlopen(apel_url)
        data = usock.read()
        usock.close()
        apel_data = []
        datafields = []
        numcells=11
        for i in range(numcells):
            datafields.append(0)
        datafields[0]="ExecutingSite"
        datafields[1]="HS06Factor"
        datafields[2]="LCGUserVO"
        datafields[3]="Njobs"
        datafields[4]="SumCPU"
        datafields[5]="SumWCT"
        datafields[6]="HS06_CPU"
        datafields[7]="HS06_WCT"
        datafields[8]="RecordStart"
        datafields[9]="RecordEnd"
        datafields[10]="MeasurementDate"
        linesrec=data.split('\n')
        for line in linesrec:
            eachfield=line.split('\t')
            count=0
            info = {}
            for field in eachfield:
                if(count<numcells):
                    info[datafields[count]]=field
                count=count+1
            info['month']=month
            info['year']=year
            apel_data.append(info)
        return apel_data


    def get_apel_data_jot(self, month, year):
        if(year >=2012 and month >= 3):
            return self.get_apel_data_jot_since201203(month, year)
        apel_url = self.metadata.get('apel_url', 'http://gratia-osg-prod-reports.opensciencegrid.org/gratia-data/interfaces/apel-lcg/%i-%02i.HS06_OSG_DATA.xml'\
            % (year, month))
        xmldoc = urllib2.urlopen(apel_url)
        dom = parse(xmldoc)
        apel_data = []
        report_time = None
        for rowDom in dom.getElementsByTagName('row'):
            info = {}
            for field in rowDom.getElementsByTagName('field'):
                name = str(field.getAttribute('name'))
                if len(name) == 0:
                    continue
                val = str(field.firstChild.data)
                info[name] = val
                if name == 'MeasurementDate' and report_time == None:
                    report_time = val
            if len(info) == 0:
                for child in rowDom.childNodes:
                    name = str(child.nodeName)
                    if not name or len(name) == 0:
                        continue
                    if child.nodeType == child.TEXT_NODE:
                        continue
                    val = str(child.firstChild.data)
                    info[name] = val
                    if name == 'MeasurementDate' and report_time == None:
                        report_time = val
            apel_data.append(info)
        return apel_data

    def get_gridview(self, month, year, federations):
        url = self.metadata.get('gridview_url', 'http://gridview.cern.ch' \
            '/GRIDVIEW/pi/xml/sam-xml.php')
        params = {\
            'summary_period': 'monthly',
            'value_fields': 'availability,reliability,unknown',
            'start_time': '%i-%i-%iT00:00:00Z' % (year, month, 1),
            'end_time': '%i-%i-%iT00:00:01Z' % (year, month, 1),
            'VO_name[]': 'ops',
            'Region_name': 'OpenScienceGrid',
        }
        full_url = url + '?' + urllib.urlencode(params)
        print "FEDERATION ----- %s",(full_url)
        data = urllib2.urlopen(full_url)
        dom = parse(data)
        gridview_data = {}
        for site_dom in dom.getElementsByTagName('Site'):
            name=site_dom.getAttribute('name')
            name = name.upper()
            if name=="IU_OSG":
                continue
            gridview_data.setdefault(name, [0, 0])
            val = None
            for value_dom in site_dom.getElementsByTagName('availability'):
                try:
                    val = float(str(value_dom.firstChild.data))
                except:
                    continue
            gridview_data[name][1] = val
            val = None
            for value_dom in site_dom.getElementsByTagName('unknown'):
                try: 
                    val = float(str(value_dom.firstChild.data))
                except:
                    continue
            if val != None and gridview_data[name][1] != None and val < \
                    gridview_data[name][1]:
                gridview_data[name][1] += val
            val = None
            for value_dom in site_dom.getElementsByTagName('reliability'):
                try:
                    val = float(str(value_dom.firstChild.data))
                except:
                    continue
            if val != None:
                gridview_data[name][0] = val

        fed_data = {}
        for resource, fed in federations.items():
            print "FED = %s "%(fed)
            for gv_resource, data in gridview_data.items():
              print "FED : %s, gv_resource=%s, resource=%s" %(fed, gv_resource, resource)
              try:
                if gv_resource == resource.upper():
                    val = fed_data.setdefault(fed, [0., 0., 0., 0.])
                    val[2] += 1
                    val[1] += data[1]
                    if data[0] != None and data[0] >= 0:
                        val[0] += data[0]
                        val[3] += 1
              except:
                print "ERROR FED : %s, gv_resource=%s, resource=%s" %(fed, gv_resource, resource)
        results = {}
        for fed, data in fed_data.items():
            if data[3] == 0:
                data[3] = 1
            if data[2] == 0:
                data[2] = 1
            results[fed] = data[0]/data[3], data[1]/data[2]
        return results

    def site_normalization_jot(self, month, year, sites=None):
        apel_data = self.get_apel_data_jot(month, year)
        site_normalization = {}
        norm_total = 0
        wall_total = 0
        for info in apel_data:
            site = info.get('ExecutingSite', 'UNKNOWN')
            try:
                wall = int(info.get('SumWCT', 0))
                norm = float(info.get('HS06Factor', 0))
            except:
                continue
            norm_total += norm
            wall_total += wall
            site_normalization[site] = norm
        norm_avg = norm_total / float(wall_total)
        if sites:
            for site in sites:
                site_normalization.setdefault(site, norm_avg)
        return site_normalization

    def vo_data_2008(self, vos=''):
        specific_vos = sets.Set(["usatlas",  "cms", "cdf",  "dzero", "ligo",
            "engage", "osg"])
        specific_vos.update([i.strip() for i in vos.split(',') if i.strip()])
        starttime = datetime.datetime(2008, 01, 01)
        endtime = datetime.datetime(2009, 01, 01)
        user_counts, _ = self.globals['GratiaPieQueries'].osg_user_count(\
            starttime=starttime, endtime=endtime)
        wall_success, _= self.globals['GratiaBarQueries'].vo_wall_success_rate(\
            starttime=starttime, endtime=endtime)
        wall, _ = self.globals['GratiaBarQueries'].vo_wall_hours(\
            starttime=starttime, endtime=endtime)
        cpu, _ = self.globals['GratiaBarQueries'].vo_cpu_hours(\
            starttime=starttime, endtime=endtime)
        results = 'VO,User Count,Wall Hours,CPU Hours,Wall Success Rate\n'
        all_vos = sets.Set(user_counts.keys())
        all_vos.update(wall_success.keys())
        all_vos.update(wall.keys())
        all_vos.update(cpu.keys())
        other_user_count, total_user_count = 0, 0
        other_wall_success, total_wall_success = 0, 0
        other_wall, total_wall = 0, 0
        other_cpu, total_cpu = 0, 0
        for vo in all_vos:
            total_user_count += user_counts.get(vo, 0)
            total_wall_success += wall_success.get(vo, 0)*wall.get(vo, 0)
            total_wall += wall.get(vo, 0)
            total_cpu += cpu.get(vo, 0)
            if vo in specific_vos:
                wall_success_perc = int(round(wall_success.get(vo, 0)*100))
                results += "%s,%i,%i,%i,%i\n" % (vo, int(user_counts.get(vo,
                0)), int(wall.get(vo, 0)), int(cpu.get(vo, 0)),
                wall_success_perc)
            else:
                other_user_count += user_counts.get(vo, 0)
                other_wall_success += wall_success.get(vo, 0)*wall.get(vo, 0)
                other_wall += wall.get(vo, 0)
                other_cpu += cpu.get(vo, 0)
        other_wall_success /= float(other_wall)
        total_wall_success /= float(total_wall)
        other_wall_success = int(round(other_wall_success*100))
        total_wall_success = int(round(total_wall_success*100))
        results += "Other,%i,%i,%i,%i\n" % (int(other_user_count),
            int(other_wall), int(other_cpu), int(other_wall_success))
        results += "Total,%i,%i,%i,%i\n" % (int(total_user_count),
            int(total_wall), int(total_cpu), int(total_wall_success))
        cherrypy.response.headers['Content-Type'] = "text/plain"
        return results
    vo_data_2008.exposed = True

    def normalized_vo_hours(self, starttime, endtime, vo_list, span):
        vos = '|'.join(vo_list)
        normalization = NormalizationConstants(self.globals['GIPQueries'],
            starttime=starttime, endtime=endtime, span=span)
        hours, _ = self.globals['GratiaBarQueries'].vo_site_wall_hours( \
            starttime=starttime, endtime=endtime, span=span, vos=vos)
        results = {}
        for vo in vo_list:
            results[vo] = 0
            for key, groups in hours.items():
                site, voTmp = key
                if vo != voTmp:
                    continue
                for time, val in groups.items():
                    norm = normalization.getNorm(site, val)
                    results[vo] += norm * val
        hours_per_year = float(365*24)
        for key, val in results.items(): # Return values in CPU-years.
            results[key] = val/hours_per_year
        return results

    def _hep_reporting(self, year=None, month=None, vos=None, span=86400):
        starttime, endtime, month, year = self.get_times(month, year)
        if vos:
            vos = '|'.join(vos.split(','))
        else:
            vos = ['cdf', 'dzero', 'cdms', 'minos', 'minerva', 'miniboone',
                'des', 'auger', 'accelerator', 'ktev', 'mipp', 'nova', 'theory',
                'fermilab', 'cms', 'usatlas', 'sdss']
            vos = '|'.join(vos)
        vo_list = vos.split('|')
        results1 = self.normalized_vo_hours(starttime, endtime, vo_list, span)
        starttime = endtime - datetime.timedelta(365,0)
        results2 = self.normalized_vo_hours(starttime, endtime, vo_list, span)
        return results1, results2

    def hep_reporting_csv(self, year=None, month=None, vos=None):
        info1, info2 = self._hep_reporting(year, month, vos)
        results = 'Normalized Wall Years from last month:\n'
        for vo, hrs in info1.items():
            results += '%s,%.3f\n' % (vo, hrs)
        results += '\nNormalized Wall Years from last year:\n'
        for vo, hrs in info2.items():
            results += '%s,%.3f\n' % (vo, hrs)
        cherrypy.response.headers['Content-Type'] = "text/plain"
        return results
    hep_reporting_csv.exposed = True
 
