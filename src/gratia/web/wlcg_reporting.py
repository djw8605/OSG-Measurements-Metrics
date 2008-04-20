
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
            if site[:8] == "UFlorida" and site != "UFlorida-IHEPA" and site != "UFlorida-PG":
                site = "UFlorida-HPC"
            vo_info = pledge_info.get(VOMoU, {})
            pledge_info[VOMoU] = vo_info
            site_info = vo_info.get(my_accounting, {})
            vo_info[my_accounting] = site_info
            site_info['pledge07'] = my_pledge07
            site_info['pledge08'] = my_pledge08
            site_info['efficiency'] = .6
            site_info['days_in_month'] = last_day
            self.add_effort(site_info, site, VOMoU, apel_data, gratia_data)
            #print my_accounting, site, site_info
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
            apel_data.append(info)
        #print apel_data
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
            site_norm[site] = (gipnorm, wlcgnorm, diff)

        # Remove non-WLCG sites from the GIP data.
        new_subclusters = {}
        for key, val in data['subclusters'].items():
            if key[0] in wlcg_sites:
                new_subclusters[key] = val
        data['subclusters'] = new_subclusters

        # Add in the pledge data
        data['pledge'] = self.t2_pledges(apel_data, year, month)
        
        data['title'] = "Reported WLCG data for %s %i" % (calendar.month_name[month], year)
        return data

    def pledge_table(self, year=datetime.datetime.now().year, month=datetime.datetime.now().month):
        apel_data, report_time = self.get_apel_data(year, month)
        pledges = self.t2_pledges(apel_data, year, month)
        cherrypy.response.headers['Content-Type'] = 'text/plain'
        info = {"report_time": report_time, "apel_data": apel_data,
            "pledges": pledges}
        return str(info)
    pledge_table.exposed = True

