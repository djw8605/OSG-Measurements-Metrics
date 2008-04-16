
import os
import urllib
import urllib2
import re
import sys
import types
import calendar
import datetime

import cherrypy
from xml.dom.minidom import parse

from gratia.database.query_handler import displayName
from image_map import ImageMap
from auth import Authenticate
from navigate import Navigation

class Gratia(ImageMap, Navigation):

    def __init__(self, *args, **kw):
        super(Gratia, self).__init__(*args, **kw)
        self.main = self.template('main.tmpl')(self.main)
        self.overview = self.template('overview.tmpl')(self.overview)
        self.vo_overview = self.template('vo_overview.tmpl')(self.vo_overview)
        self.vo_opp = self.template('vo_opp.tmpl')(self.vo_opp)
        self.vo_opp2 = self.template('vo_opp2.tmpl')(self.vo_opp2)
        self.vo_exitcode = self.template('vo_exitcode.tmpl')(self.vo_exitcode)
        self.site_owner = self.template('site_owner.tmpl')(self.site_owner)
        self.site = self.template('site.tmpl')(self.site)
        self.vo = self.template('vo.tmpl')(self.vo)
        self.bysite = self.template('bysite.tmpl')(self.bysite)
        self.byvo = self.template('byvo.tmpl')(self.byvo)
        self.monbyvo = self.template('monbyvo.tmpl')(self.monbyvo)
        self.monbysite = self.template('monbysite.tmpl')(self.monbysite)
        self.wlcg_reporting = self.template('wlcg_reporting.tmpl')(self.apel_data)
        self._cp_config ={}
        self.index = self.overview

    def assign_blank(self, dict, *args):
        for arg in args:
            if arg not in dict:
                dict[arg] = ''

    def copy_if_present(self, to_dict, from_dict, *args):
        for arg in args:
            if arg in from_dict and from_dict[arg] != '':
                to_dict[arg] = from_dict[arg]

    def refine(self, data, filter_dict, facility=True, vo=True, dn=True,\
            hours=True):
        relTime = data.get('relativetime', False)
        data['supports_hours'] = hours
        data['refine_vo'] = vo
        data['refine_facility'] = facility
        data['refine_dn'] = dn
        if relTime:
            if relTime == 'absolute':
                data['relTime'] = 'absolute'
                starttime = data.get('starttime', None)
                if starttime != None and starttime.strip() != '':
                    filter_dict['starttime'] = starttime
                endtime = data.get('endtime', None)
                if endtime != None and endtime.strip() != '':
                    filter_dict['endtime'] = endtime
            else:
                data['relTime'] = relTime
                interval = int(relTime)
                filter_dict['starttime'] = 'time.time()-%i' % interval
                filter_dict['endtime'] = 'time.time()'
                if interval < 4*86400:
                    filter_dict['span'] = 3600
                elif interval < 30*86400: 
                    filter_dict['span'] = 86400
                else:
                    filter_dict['span'] = 86400*7
        else:
            data['relTime'] = 'absolute'

        self.copy_if_present(filter_dict, data, 'facility', 'vo', \
            'exclude-facility', 'exclude-vo', 'user', 'user', 'exclude-dn', \
            'set')
        data['query_kw'] = dict(filter_dict)
        data['filter_url'] = urllib.urlencode(filter_dict)
        self.assign_blank(filter_dict, 'facility', 'vo', 'exclude-vo', \
            'exclude-facility', 'exclude-dn', 'user')
        data['filter_dict'] = filter_dict
        if data['filter_url'] != '': 
            data['filter_url'] = '?' + data['filter_url']
        data['refine'] = self.getTemplateFilename('refine.tmpl')
        data['refine_error'] = None

    def main(self, *args, **kw):
        data = dict(kw)
        data['given_kw'] = dict(kw)
        self.focus(kw, data, 'main', 'facility', ['facility', 'vo', 'both'])
        filter_dict = {}
        # Do user auth:
        self.user_auth(data)
        self.user_roles(data)

        # Handle the refine variables
        self.refine(data, filter_dict, dn=False)
        token = self.start_image_maps()
        # Generate image maps:
        if data['focus']['value'] == 'facility' or \
                data['focus']['value'] == 'both':
            self.image_map(token, data, 'GratiaBarQueries', 
                           'facility_transfer_rate', 'main', 'facility')
                           
            self.image_map(token, data, 'GratiaBarQueries', 
                           'facility_quality', 'main', 'facility')
                           
            self.image_map(token, data, 'GratiaBarQueries',
                           'facility_transfer_volume', 'main', 'facility')
        else:
            self.image_map(token, data, 'GratiaBarQueries', 'vo_transfer_rate',
                           'main', 'vo')
            self.image_map(token, data, 'GratiaBarQueries', 'vo_quality',
                           'main', 'vo')
            self.image_map(token, data, 'GratiaBarQueries', 
                           'vo_transfer_volume', 'main', 'vo')
                           
        self.finish_image_maps(token)

        if data['is_authenticated']:
            data['title'] = "OSG Storage Main for %s" % data['name']
        else:
            data['title'] = "OSG Storage Main"
        return data

    def bysite(self, *args, **kw):
        data = dict(kw)
        data['given_kw'] = dict(kw)
        self.user_auth(data)
        filter_dict = {}

        # Handle the refine variables
        self.refine(data, filter_dict, dn=False, hours=False)
        token = self.start_image_maps()
        # Generate image maps:
        self.image_map(token, data, 'GratiaBarQueries',
                           'facility_hours_bar_smry', 'site', 'facility')
        self.image_map(token, data, 'GratiaPieQueries',
            'osg_facility_hours', 'site', 'facility')
        self.image_map(token, data, 'GratiaPieQueries',
            'osg_facility_count', 'site', 'facility')

        self.finish_image_maps(token)

        if data['is_authenticated']:
            data['title'] = "OSG Job Accounting Information By Site for %s" % \
                data['name']
        else:
            data['title'] = "OSG Job Accounting Information By Site"
        return data

    def monbysite(self, *args, **kw):
        data = dict(kw)
        data['given_kw'] = dict(kw)
        self.user_auth(data)
        filter_dict = {}

        # Handle the refine variables
        self.refine(data, filter_dict, dn=False, hours=False)
        token = self.start_image_maps()
        # Generate image maps:
        self.image_map(token, data, 'GIPQueries',
            'gip_facility', 'site', 'facility')
        self.image_map(token, data, 'GIPQueries',
            'gip_facility_pie', 'site', 'facility')
        self.image_map(token, data, 'GIPQueries',
            'gip_free_cpu_realtime', 'site', 'facility')
        self.image_map(token, data, 'GIPQueries',
            'gip_free_cpus_history', 'site', 'facility')
        self.image_map(token, data, 'GIPQueries',
            'gip_facility_waiting', 'site', 'facility')
        self.image_map(token, data, 'GIPQueries',
            'gip_facility_waiting_pie', 'site', 'facility')

        self.finish_image_maps(token)

        if data['is_authenticated']:
            data['title'] = "OSG Monitoring Information By Site for %s" % \
                data['name']
        else:
            data['title'] = "OSG Monitoring Information By Site"
        return data

    def byvo(self, *args, **kw):
        data = dict(kw)
        data['given_kw'] = dict(kw)
        self.user_auth(data)
        filter_dict = {}

        # Handle the refine variables
        self.refine(data, filter_dict, dn=False, hours=False)
        token = self.start_image_maps()
        # Generate image maps:
        self.image_map(token, data, 'GratiaBarQueries',
                           'vo_hours_bar_smry', 'vo', 'vo')
        self.image_map(token, data, 'GratiaPieQueries',
            'osg_vo_hours', 'vo', 'vo')
        self.image_map(token, data, 'GratiaPieQueries',
            'osg_vo_count', 'vo', 'vo')

        self.finish_image_maps(token)

        if data['is_authenticated']:
            data['title'] = "OSG Job Accounting Information By VO for %s" % data['name']
        else:
            data['title'] = "OSG Job Accounting Information By VO"
        return data

    def monbyvo(self, *args, **kw):
        data = dict(kw)
        data['given_kw'] = dict(kw)
        self.user_auth(data)
        filter_dict = {}
        
        # Handle the refine variables
        self.refine(data, filter_dict, dn=False, hours=False)
        token = self.start_image_maps()
        # Generate image maps:
        self.image_map(token, data, 'GIPQueries',
            'gip_vo', 'site', 'facility')
        self.image_map(token, data, 'GIPQueries',
            'gip_vo_pie', 'site', 'facility')
        self.image_map(token, data, 'GIPQueries',
            'gip_vo_waiting', 'site', 'facility')
        self.image_map(token, data, 'GIPQueries',
            'gip_vo_waiting_pie', 'site', 'facility')

        self.finish_image_maps(token)
        if data['is_authenticated']:
            data['title'] = "OSG Monitoring Information By VO for %s" % \
                data['name']
        else:
            data['title'] = "OSG Monitoring Accounting Information By VO"
        return data

    def focus(self, kw, data, page, default, values):
        focus_kw = dict(kw)
        focus = data.get('focus', default)
        def change_focus(view, base_url):
            base_url = base_url + '/' + page
            if view==data['focus']:
                return None
            focus_kw['focus'] = view
            query = urllib.urlencode(focus_kw)
            if len(query) > 0:
                query = '?' + query
            return base_url + query
        data['change_focus'] = change_focus
        focus = {'value': focus, 'change': change_focus}
        focus['tmpl'] = self.getTemplateFilename('focus.tmpl')
        focus['values'] = values
        data['focus'] = focus

    def site_owner(self, *args, **kw):
        data = dict(kw)
        data['given_kw'] = kw
        filter_dict = {}
        data['facility'] = data.get('facility', None)
        self.focus(kw, data, 'site_owner', 'user', ['user', 'vo', 'both'])

        #User auth
        self.user_auth(data)
        self.user_roles(data)

        #Handle refine
        self.refine(data, filter_dict, facility=False)

        token = self.start_image_maps()
        #Generate image maps
        if data['focus']['value'] == 'user' or data['focus']['value'] == 'both':
            #self.image_map(token, data, 'GratiaSiteBarQueries', \
            #    'site_user_job_quality', 'site_owner', 'user')
            self.image_map(token, data, 'GratiaSiteBarQueries', 
                'site_user_job_hours', 'site_owner', 'user')
            self.image_map(token, data, 'GratiaSiteBarQueries', 
                'site_user_transfer_quality', 'site_owner', 'user')
            self.image_map(token, data, 'GratiaSiteBarQueries', 
                'site_user_transfer_rate', 'site_owner', 'user')
        if data['focus']['value'] == 'vo' or data['focus']['value'] == 'both':
            self.image_map(token, data, 'GratiaSiteBarQueries', 
                 'site_vo_job_quality', 'site_owner', 'user')
            self.image_map(token, data, 'GratiaSiteBarQueries', 
                 'site_vo_job_hours', 'site_owner', 'user')
            self.image_map(token, data, 'GratiaSiteBarQueries', 
                'site_vo_transfer_quality', 'site_owner', 'user')
            self.image_map(token, data, 'GratiaSiteBarQueries', 
                'site_vo_transfer_rate', 'site_owner', 'user')
        self.finish_image_maps(token)

        #Empty transfer list for now
        #transfers, metadata = self.globals['GratiaSiteBarQueries'].\
        #    site_table(data['query_kw'])
        transfers = []
        for transfer in transfers:
            transfer['name'] = displayName(transfer['name'])
            transfer['transfer_rate'] = to_mb(transfer['transfer_rate']) + \
                ' MB/s'
            transfer['bytes_transferred'] = to_mb( \
                transfer['bytes_transferred']) + ' MB'
        data['transfers'] = transfers

        # External data
        external = {}
        data['external'] = external
        external['GridScan'] = self.fetch_gridscan(data.get('facility'))[0][:2]
        external['GIP Validator'] = self.gip_validation(data['facility'])[0][:2]
        return data

    def site(self, *args, **kw):
        data = dict(kw)
        data['given_kw'] = kw
        filter_dict = {}
        data['facility'] = data.get('facility', None)
        if data['facility']:
            data['facility'] = urllib.unquote(data['facility'])

        # Leave early if no facility specified.
        if data['facility'] == None:
            data['title'] = 'No facility specified!'
            data['image_maps'] = None
            return data

        #User auth
        self.user_auth(data)

        #Handle refine
        self.refine(data, filter_dict, facility=False, hours=False)

        token = self.start_image_maps()
        #Generate image maps
        self.image_map(token, data, 'GratiaPieQueries',
            'osg_vo_hours', 'site', 'vo')
        self.image_map(token, data, 'GratiaPieQueries',
            'osg_vo_count', 'site', 'vo')
        self.image_map(token, data, 'GratiaBarQueries',
            'vo_hours_bar_smry', 'site', 'vo')
        self.image_map(token, data, 'GratiaCumulativeQueries',
            'vo_success_cumulative_smry', 'site', 'vo')
        self.finish_image_maps(token)

        external = {}
        data['external'] = external
        external['GridScan'] = self.fetch_gridscan(data['facility'])
        external['GIP Validator'] = self.gip_validation(data['facility'])
        data['title'] = 'Site Information'
        return data

    def vo(self, *args, **kw):
        data = dict(kw)
        data['given_kw'] = kw
        filter_dict = {} 
        data['vo'] = data.get('vo', None)
        if data['vo']:
            data['vo'] = urllib.unquote(data['vo'])
            
        # Leave early if no vo specified.
        if data['vo'] == None:
            data['title'] = 'No VO specified!'
            data['image_maps'] = None
            return data
            
        #User auth
        self.user_auth(data)
        #Handle refine
        self.refine(data, filter_dict, facility=False, hours=False)

        token = self.start_image_maps()
        #Generate image maps
        self.image_map(token, data, 'GratiaPieQueries',
            'osg_facility_hours', 'site', 'vo')
        self.image_map(token, data, 'GratiaPieQueries',
            'osg_facility_count', 'site', 'vo')
        self.image_map(token, data, 'GratiaBarQueries',
            'facility_hours_bar_smry', 'site', 'vo')
        self.image_map(token, data, 'GratiaBarQueries',
            'vo_opp_hours_bar2', 'site', 'vo')
        self.image_map(token, data, 'GratiaCumulativeQueries',
            'facility_success_cumulative_smry', 'site', 'vo')
        self.finish_image_maps(token)

        data['title'] = 'VO Information'
        return data

    def fetch_gridscan(self, site):
        doc = urllib2.urlopen('http://scan.grid.iu.edu/cgi-bin/show_results?grid=1')
        in_row = False
        in_font = False
        link_re = re.compile('HREF="(.*?)"')
        site_re2 = re.compile(site)
        site_re = re.compile('<A HREF="(.*?)">(.*)</A>')
        link = "#"
        status = "Unknown"
        info = []
        for line in doc.readlines():
            m = site_re.search(line)
            if m and site_re2.search(m.groups()[1]):
                fac = m.groups()[1]
                in_row = True
            if not in_row:
                continue
            if line.find('HREF') >= 0:
                m = link_re.search(line)
                if m:
                    link = m.groups()[0]
            if line.startswith("<FONT"):
                in_font = True
                continue
            if in_font:
                status = line.strip()
                info.append((status, "http://scan.grid.iu.edu" + link, fac))
                status = "Unknown"
                in_font = False
                in_row = False
        return info

    def gip_validation(self, site):
        doc = urllib2.urlopen('http://gip-validate.grid.iu.edu/production')
        row_re = re.compile("<td valign='middle'>(.*)</td>")
        row_re2 = re.compile(site)
        info_re = re.compile("<td height='30' bgcolor='(.*?)'><a href='(.*?)'>")
        in_row = False
        result = "Unknown"
        link = "#"
        info = []
        my_facs = []
        for line in doc.readlines():
            m = row_re.search(line)
            if m:
                m2 = row_re2.search(m.groups()[0])
                if m2:
                    fac = m.groups()[0]
                    in_row = True
                    continue
                else:
                    in_row = False
                    continue
            if in_row:
                m = info_re.search(line)
                if m:
                    color, link = m.groups()
                    if color == 'green':
                        result = "PASS"
                    elif color == 'red':
                        result = "FAIL"
                    elif color == "black":
                        result = "Not Reporting"
                    else:
                        result = "Unknown"
                if fac not in my_facs:
                    my_facs.append(fac)
                    info.append((result, "http://gip-validate.grid.iu.edu/production/" + link,
                        fac))
        return info

    def vo_owner(self, *args, **kw):
        return "We're sorry, but the VO owner page has not been written."
    vo_owner.exposed = True

    def user(self, *args, **kw):
        return "We're sorry, but the user details page has not been written."
    user.exposed = True

    def overview(self, *args, **kw):
        data = dict(kw)
        self.user_auth(data)
        data['title'] = "OSG overview page"
        data['static_url'] = self.metadata.get('static_url', '/store/gratia')
        return data

    def get_variable_values(self, url):
        retval = []
        try:
            xmldoc = urllib2.urlopen(url)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception, e:
            print >> sys.stderr, "Exception occurred while getting variable values: %s" % str(e)
            return retval
        dom = parse(xmldoc)
        for pivot in dom.getElementsByTagName('pivot'):
            pivot_str = pivot.getAttribute('name')
            if len(pivot_str) > 0:
                retval.append(pivot_str)
        return retval

    def get_vo_list(self, vos_url, registered_vos_url, keep_vos):
        vos = self.get_variable_values(vos_url)
        info = urllib2.urlopen(registered_vos_url)
        reg_vos = []
        for line in info.readlines():
            line = line.strip()
            if len(line) == 0:
                continue
            reg_vos.append(line.split('<')[0].lower())
        retval = []
        for vo in vos:
            if vo in keep_vos or vo.lower() in reg_vos:
                retval.append(vo)
        for vo in keep_vos:
            if vo not in retval:
                retval.append(vo)
        return retval

    def vo_overview(self, *args, **kw):
        data = dict(kw)
        self.user_auth(data)
        vos_url = self.metadata.get('vos_url', '/gratia/xml/vo_corrected_table')
        registered_vos_url = self.metadata.get('registered_vos_url', \
            'http://www.grid.iu.edu/osg-includes/vo_txt.php')
        keep_vos = [i.strip() for i in self.metadata.get('keep_vos', \
            '').split(',') if len(i.strip()) > 0]
        if kw.get('filter', 'true').lower() == 'false':
            vos = self.get_variable_values(vos_url)
        else:
            vos = self.get_vo_list(vos_url, registered_vos_url, keep_vos)
        data['vos'] = vos
        data['current_vo'] = kw.get('vo', None)
        data['static_url'] = self.metadata.get('static_url', '/store/gratia')
        return data

    def vo_opp(self, *args, **kw):
        data = dict(kw)
        self.user_auth(data)
        vos_url = self.metadata.get('vos_url', '/gratia/xml/vo_corrected_table')
        registered_vos_url = self.metadata.get('registered_vos_url', \
            'http://www.grid.iu.edu/osg-includes/vo_txt.php')
        keep_vos = [i.strip() for i in self.metadata.get('keep_vos', \
            '').split(',') if len(i.strip()) > 0]
        if kw.get('filter', 'true').lower() == 'false':
            vos = self.get_variable_values(vos_url)
        else:
            vos = self.get_vo_list(vos_url, registered_vos_url, keep_vos)
        data['vos'] = vos
        data['current_vo'] = kw.get('vo', None)
        data['static_url'] = self.metadata.get('static_url', '/store/gratia')
        data['title'] = 'VO Opportunistic Usage'
        return data

    def vo_opp2(self, *args, **kw):
        data = dict(kw)
        self.user_auth(data)
        vos_url = self.metadata.get('vos_url', '/gratia/xml/vo_corrected_table')
        registered_vos_url = self.metadata.get('registered_vos_url', \
            'http://www.grid.iu.edu/osg-includes/vo_txt.php')
        keep_vos = [i.strip() for i in self.metadata.get('keep_vos', \
            '').split(',') if len(i.strip()) > 0]
        if kw.get('filter', 'true').lower() == 'false':
            vos = self.get_variable_values(vos_url)
        else:
            vos = self.get_vo_list(vos_url, registered_vos_url, keep_vos)
        data['vos'] = vos
        data['current_vo'] = kw.get('vo', None)
        data['static_url'] = self.metadata.get('static_url', '/store/gratia')
        if data['current_vo']:
            data['title'] = '%s OSG Usage' % data['current_vo']
        else:
            data['title'] = 'OSG Usage'
        return data

    def vo_exitcode(self, *args, **kw):
        data = dict(kw)
        self.user_auth(data)
        vos_url = self.metadata.get('vos_url', '/gratia/xml/vo_corrected_table')
        registered_vos_url = self.metadata.get('registered_vos_url', \
            'http://www.grid.iu.edu/osg-includes/vo_txt.php')
        keep_vos = [i.strip() for i in self.metadata.get('keep_vos', \
            '').split(',') if len(i.strip()) > 0]
        if kw.get('filter', 'true').lower() == 'false':
            vos = self.get_variable_values(vos_url)
        else:
            vos = self.get_vo_list(vos_url, registered_vos_url, keep_vos)
        data['vos'] = vos
        data['current_vo'] = kw.get('vo', None)
        data['static_url'] = self.metadata.get('static_url', '/store/gratia')
        return data

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
        return apel_data, report_time

    def apel_data(self, gip_time=None, year=datetime.datetime.now().year, month=datetime.datetime.now().month, **kw):
        data = dict(kw)
        self.user_auth(data)
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

        data['title'] = "Reported WLCG data for %s %i" % (calendar.month_name[month], year)
        return data

    def site_normalization(self):
        data = {}
        apel_data, reporting_time = self.get_apel_data()
        # Determine all the WLCG sites:
        wlcg_sites = []
        for row in apel_data:
            if row['ExecutingSite'] not in wlcg_sites:
                wlcg_sites.append(row['ExecutingSite'])
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

