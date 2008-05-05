
import sys
import urllib2
import calendar
import datetime
from xml.dom.minidom import parse
            
import cherrypy 
from pkg_resources import resource_stream

from graphtool.base.xml_config import XmlConfig
from auth import Authenticate

def gratia_interval(year, month):
    info = {}
    info['starttime'] = datetime.datetime(year, month, 1, 0, 0, 0)
    last_day = calendar.monthrange(year, month)[1]
    info['endtime'] = datetime.datetime(year, month, last_day, 23, 59, 59)
    return info

class WLCGReporter(Authenticate):

    def add_effort(self, site_info, site, VOMoU, apel_data, gratia_data):
        if 'wlcgNormWCT' not in site_info:
            site_info['wlcgNormWCT'] = 0
        if 'voNormWCT' not in site_info:
            site_info['voNormWCT'] = 0
        if 'totalNormWCT' not in site_info:
            site_info['totalNormWCT'] = 0
        norm = None
        for row in apel_data:
            if str(row['ExecutingSite']) != site:
                continue
            norm = float(row['NormFactor'])
            if row['LCGUserVO'].find(VOMoU) >= 0:
                site_info['voNormWCT'] += int(row['NormSumWCT'])
            site_info['wlcgNormWCT'] += int(row['NormSumWCT'])
            site_info['norm'] = norm
        if norm:
            site_info['totalNormWCT'] += int(norm * gratia_data.get(site, 0))
               

    def t2_pledges(self, apel_data, year, month):
        # Get Gratia data
        gratia_data = self.globals['GratiaPieQueries'].osg_facility_hours( \
            **gratia_interval(year, month))[0]
        lines = resource_stream('gratia.config', 'pledges.csv').read().split('\r')
        pledge_info = {}
        last_day = calendar.monthrange(year, month)[1]
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
            site = site.replace("Uflorida", "UFlorida")
            if site[:6] == "Purdue" and site.find("Lear") < 0:
                site = "Purdue-RCAC"
            if site[:6] == 'Purdue' and site.find("Lear") >= 0:
                site = "Purdue-Lear"
            if site[:8] == "UFlorida" and site != "UFlorida-IHEPA" and site != "UFlorida-PG":
                site = "UFlorida-HPC"
            vo_info = pledge_info.get(VOMoU, {})
            pledge_info[VOMoU] = vo_info
            site_info = vo_info.get(my_accounting, {})
            vo_info[my_accounting] = site_info
            site_info['pledge07'] = my_pledge07
            site_info['pledge08'] = my_pledge08
            if year >= 2008 and month >= 4:
                site_info['pledge'] = my_pledge08
            else:
                site_info['pledge'] = my_pledge07
            site_info['efficiency'] = .6
            site_info['days_in_month'] = last_day
            self.add_effort(site_info, site, VOMoU, apel_data, gratia_data)
            sites = site_info.get('sites', [])
            site_info['sites'] = sites
            if site not in sites:
                sites.append(site)
        for vo, vo_info in pledge_info.items():
            refined_vo_info = {}
            for site, site_info in vo_info.items():
                if site_info['totalNormWCT'] != 0:
                    refined_vo_info[site] = site_info
            pledge_info[vo] = refined_vo_info
        return pledge_info

    def site_normalization(self):
        data = {}
        apel_data, reporting_time = self.get_apel_data()
        # Determine all the WLCG sites:
        wlcg_sites = []
        for row in apel_data:
            if row['ExecutingSite'] not in wlcg_sites:
                wlcg_sites.append(row['ExecutingSite'])
        #print wlcg_sites
        data['subclusters'], data['time_list'] = self.gratia_data()

        # Determine site normalization:
        site_norm = {}
        data['site_norm'] = site_norm
        tmp_norm = {}
        report_time = None
        for key, val in data['subclusters'].items():
            if report_time == None:
                report_time = val[0]
            site = key[0]
            if site not in wlcg_sites:
                #print site
                continue
            info = tmp_norm.get(site, [])
            tmp_norm[site] = info
            info.append((val[2], val[3]))
        data['gip_report_time'] = report_time
        for site, info in tmp_norm.items():
            total_cores = 0
            total_si2k = 0
            for cores, si2k in info:
                total_cores += cores
                total_si2k += si2k*cores
            gipnorm = int(total_si2k / total_cores)
            site_norm[site] = gipnorm
            #print site

        #Output data:
        strng = '# GIP Report time: %s\n' % report_time
        for site, info in site_norm.items():
            strng += '%s %i\n' % (site, info)
        cherrypy.response.headers['Content-Type'] = 'text/plain'
        return strng
    site_normalization.exposed = True

    def gratia_data(self, timestamp=None):
        if timestamp==None:
            subclusters = self.globals['GIPQueries'].subcluster_latest()[0]
        else:
            subclusters = self.globals['GIPQueries'].subcluster(timestamp=timestamp)[0]
        time_list = self.globals['GIPQueries'].subcluster_times()
        return subclusters, time_list

    def get_apel_data(self, year=datetime.datetime.now().year, month=datetime.datetime.now().month):
        year = int(year)
        month = int(month)
        apel_url = self.metadata.get('apel_url', 'http://home.fnal.gov/~weigand/apel-wlcg/%i-%02i.xml' % (year, month))
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
        return apel_data, report_time

    def apel_data(self, gip_time=None, year=datetime.datetime.now().year, 
            month=datetime.datetime.now().month, **kw):
        data = dict(kw)
        self.user_auth(data)
        self.user_roles(data)
        year = int(year)
        month = int(month)
        try:
            apel_data, report_time = self.get_apel_data(year, month)
            data['error'] = False
        except (KeyboardInterrupt, SystemExit):
            raise 
        except Exception, e:
            print >> sys.stderr, "Exception occurred while APEL data: %s" % str(e)
            data['title'] = "WLCG Reporting Info Error."
            data['error'] = True
            data['error_message'] = 'An error occurred when retrieving the data.'
            raise e
            return data
        data['apel'] = apel_data
        data['year'] = year
        data['month'] = month 
        data['month_name'] = calendar.month_name[month]
        data['report_time'] = report_time
        
        def key_sorter(key1, key2):
            if key1 < key2:
                return -1
            if key1 == key2:
                return 0
            return 1
        data['key_sorter'] = key_sorter
        apel_data.sort(key_sorter)
        # Add in the GIP data
        data['subclusters'], data['time_list'] = self.gratia_data(timestamp=gip_time)

        # Determine all the WLCG sites:
        wlcg_sites = []
        wlcg_norm = {}
        data['wlcg_sites'] = wlcg_sites
        for row in apel_data:
            if row['ExecutingSite'] not in wlcg_sites:
                wlcg_sites.append(row['ExecutingSite'])
                wlcg_norm[row['ExecutingSite']] = row['NormFactor']

        # Determine site normalization:
        site_norm = {}
        data['site_norm'] = site_norm
        tmp_norm = {}
        report_time = None
        for key, val in data['subclusters'].items():
            if report_time == None:
                report_time = val[0]
            site = key[0]
            if site not in wlcg_sites:
                continue
            info = tmp_norm.get(site, [])
            tmp_norm[site] = info
            info.append((val[2], val[3]))
        data['gip_report_time'] = report_time
        for site, info in tmp_norm.items():
            total_cores = 0
            total_si2k = 0
            for cores, si2k in info:
                total_cores += cores
                total_si2k += si2k*cores
            gipnorm = int(total_si2k / total_cores) / 1000.
            wlcgnorm = float(wlcg_norm[site])
            diff = int((gipnorm - wlcgnorm)/wlcgnorm * 100)
            site_norm[site] = (gipnorm, wlcgnorm, diff, int(total_si2k/1000.))

        # Remove non-WLCG sites from the GIP data.
        new_subclusters = {}
        for key, val in data['subclusters'].items():
            if key[0] in wlcg_sites:
                new_subclusters[key] = val
        data['subclusters'] = new_subclusters

        # Add in the pledge data
        data['pledge'] = self.t2_pledges(apel_data, year, month)
       
        # Determine site summary table.  Shows number of subclusters,
        # site name, and WLCG accounting name
        summary = {}
        for site in wlcg_sites:
            sum_info = summary.get(site, {})
            summary[site] = sum_info
            for key, val in data['subclusters'].items():
                 if key[0] == site:
                     num_subclusters = sum_info.get('subclusters', 0)
                     sum_info['subclusters'] = num_subclusters + 1
            for vo_key, vo_val in data['pledge'].items():
                for key, val in vo_val.items():
                    if site in val['sites']:
                        sum_info['accounting'] = key
                        if 'actual' not in val:
                            val['actual'] = 0
                        val['actual'] += site_norm.get(site, (0, 0, 0, 0))[3]
            if 'subclusters' not in sum_info:
                sum_info['subclusters'] = 0
            if 'accounting' not in sum_info:
                sum_info['accounting'] = "UNKNOWN"
        data['summary'] = summary

        data['title'] = "Reported WLCG data for %s %i" % \
            (calendar.month_name[month], year)
        if year >= 2008 and month >= 4:
            data['pledge_year'] = '2008'
        else:
            data['pledge_year'] = '2007'

        # Site availability hours
        rsv_data = self.get_rsv_data(apel_data, year, month)
        data['avail'] = self.get_ksi2k_availability(data['pledge'], rsv_data)
        print data['avail']
        return data

    def pledge_table(self, year=datetime.datetime.now().year, \
            month=datetime.datetime.now().month):
        apel_data, report_time = self.get_apel_data(year, month)
        pledges = self.t2_pledges(apel_data, year, month)
        cherrypy.response.headers['Content-Type'] = 'text/plain'
        info = {"report_time": report_time, "apel_data": apel_data,
            "pledges": pledges}
        return str(info)
    pledge_table.exposed = True

    def get_wlcg_sites(self, apel_data):
        wlcg_sites = []
        for row in apel_data:
            if row['ExecutingSite'] not in wlcg_sites:
                wlcg_sites.append(row['ExecutingSite'])
        return wlcg_sites

    def get_rsv_data(self, apel_data, 
            year=datetime.datetime.now().year, \
            month=datetime.datetime.now().month, **kw):
        wlcg_sites = get_wlcg_sites(apel_data)
        daterange = gratia_interval(year, month)
        cur = daterange['starttime']
        end = min(daterange['endtime'], datetime.datetime.today())
        data = {}
        oneday = datetime.timedelta(1, 0)
        for site in wlcg_sites:
            data[site] = {}
        while cur <= end:
            for site in wlcg_sites:
                data[site][cur] = 1.0
            cur += oneday
        return data

    def parse_ownership(data, vo):
        r = re.compile("(\w+):([0-9]+)")
        m = r.findall(data)
        if m == None:
            raise Exception("Unable to determine site ownership.")
        for grouping in m:
            sponsor, perc = grouping
            if sponsor.lower().find(vo) >= 0:
                return float(perc)/100.

    def _avg(self, values):
        return sum(values) / float(len(values))

    def get_ksi2k_availability(self, pledge_data, rsv_data):
        info = gratia_interval(year, month)
        gip_data, dummy = self.globals['GIPQueries'].subcluster_interval(info)
        cur = info['starttime']
        end = min(info['endtime'], datetime.datetime.today())
        wlcg_sites = get_wlcg_sites(apel_data)
        data = {}
        gip_smry = {}
        oneday = datetime.timedelta(1, 0)
        errors = {}
        for site in wlcg_sites:
            data[site] = {}
            gip_smry[site] = {}
            if site not in rsv_data:
                errors[site] = "RSV data not available.  "
            else:
                errors[site] = ""
        while cur <= end:
            for site in wlcg_sites:
                gip_smry[site][cur] = 0
            cur += oneday
        for key, val in gip_data.items():
            site = key[0]
            if site in pledge_data['atlas']
                pledge_vo = 'atlas'
            elif site in pledge_data['cms']
                pledge_vo = 'cms'
            else:
                pledge_vo = None
            try:
                ownership_perc = parse_ownership(gip_data[site][4], pledge_vo)
            except:
                errors[site] += "Unabe to determine site ownership.  "
                continue
            gip_data[site][val[0]] += ownership_perc*val[2]*val[3]
        for site in wlcg_sites:
            pledge_val = pledge_data['atlas'].get(site, {}).get('pledge', 0) + \
                pledge_data['cms'].get(site, {}).get('pledge', 0)
            if site not in gip_data:
                errors[site] += "GIP data not available."
                continue
            gip_val = max(gip_data[site].values())
            if abs(gip_val-pledge_val)/float(pledge_val) > .5:
                errors[site] += "Suspect GIP data."
        cur = info['starttime']
        while cur <= end:
            for site in in wlcg_sites:
                gip_val = gip_data.get(site, {})
                data[site][cur] = rsv_data.get(site, {}).get(cur, 0) * \
                    gip_val.get(cur, self._avg(gip_val.values()))
            cur += oneday
        return data, errors

