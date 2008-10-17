
import sets
import urllib
import urllib2
import datetime
import calendar

from xml.dom.minidom import parse

from pkg_resources import resource_stream

from auth import Authenticate

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
        }
        cpu_hours = self.globals['GratiaPieQueries'].osg_facility_cpu_hours(\
            **info)[0]
        wall_hours = self.globals['GratiaPieQueries'].osg_facility_hours(\
            **info)[0]

        info['vo'] = 'atlas|cms'
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
        resource_to_remove = []
        for res in federations:
            if 'CE' not in new_assoc.get(res, []):
                resource_to_remove.append(res)
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

        data['reliability'] = {}
        data['availability'] = {}
        data['cpu'] = {}
        data['count'] = {}
        data['wall'] = {}
        data['lhc_cpu'] = {}
        data['lhc_wall'] = {}
        days_in_month =  calendar.monthrange(year, month)[1]
        data['mou'] = self.pledges(month, year)
        for key, val in data['mou'].items():
            data['mou'][key] = int(days_in_month*.6*24*val)
        for resource, fed in federations.items():
            print "Resource %s associated with fed %s." % (resource, fed)
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

        data['cms_feds'] = []
        data['atlas_feds'] = []
        all_feds = sets.Set(federations.values())
        for fed in all_feds:
            # TODO: OIM should provide ownership info.
            if fed.startswith('T2_'):
                data['cms_feds'].append(fed)
            elif fed.startswith('US-'):
                data['atlas_feds'].append(fed)
            data['availability'][fed] = gv_data.get(fed, [0, 0])[1]
            data['reliability'][fed] = gv_data.get(fed, [0, 0])[0]

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

    def pledges(self, month, year):
        lines = resource_stream('gratia.config', 'pledges.csv').read().splitlines()
        pledge_info = {}
        # Pop off the headers
        lines = lines[1:]
        for line in lines:
            fed, pledge07, pledge08, VOMoU, VOaddl, accounting, site \
                = line.split('\t')[:7]
            if accounting != '':
                my_accounting = accounting
            if pledge07 != '':
                my_pledge07 = pledge07
            if pledge08 != '':
                my_pledge08 = pledge08
            fed_pledge = pledge_info.setdefault(accounting, 0)
            if year >= 2008 and month >= 4:
                pledge_info[accounting] = my_pledge08
            else:
                pledge_info[accounting] = my_pledge07
            try:
                pledge_info[accounting] = int(pledge_info[accounting])
            except:
                del pledge_info[accounting]
        return pledge_info

    def get_apel_data_jot(self, month, year):
        apel_url = self.metadata.get('apel_url', 'http://gratia09.fnal.gov:8880/gratia-data/interfaces/apel-lcg/%i-%02i.OSG_DATA.xml'\
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
        url = self.metadata.get('gridview_url', 'http://gridview001.cern.ch/' \
            'GVVAI/js/lib/sam-demo.php')
        params = {\
            'summary_period': 'monthly',
            'value_fields': 'availability,reliability',
            'start_time': '%i-%i-%iT00:00:00Z' % (year, month, 1),
            'end_time': '%i-%i-%iT00:00:01Z' % (year, month, 1),
            'VO_name[]': 'ops',
            'Region_name': 'OpenScienceGrid',
        }
        data = urllib2.urlopen(url + '?' + urllib.urlencode(params))
        dom = parse(data)
        gridview_data = {}
        for site_dom in dom.getElementsByTagName('Site'):
            name=site_dom.getAttribute('name')
            name = name.upper()
            gridview_data.setdefault(name, [0, 0])
            val = None
            for value_dom in site_dom.getElementsByTagName('availability'):
                try:
                    val = float(str(value_dom.firstChild.data))
                except:
                    continue
            if val != None:
                gridview_data[name][1] = val
            for value_dom in site_dom.getElementsByTagName('reliability'):
                try:
                    val = float(str(value_dom.firstChild.data))
                except:
                    continue
            if val != None:
                gridview_data[name][0] = val

        fed_data = {}
        for resource, fed in federations.items():
            for gv_resource, data in gridview_data.items():
                if gv_resource == resource.upper():
                    val = fed_data.setdefault(fed, [0., 0., 0.])
                    val[2] += 1
                    val[1] += data[1]
                    val[0] += data[0]
        results = {}
        for fed, data in fed_data.items():
            results[fed] = data[0]/data[2], data[1]/data[2]
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
                norm = float(info.get('NormFactor', 0))
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


