
import os
import urllib
import urllib2
import re
import sys
import types
from threading import Condition, Thread, currentThread

import cherrypy
from Cheetah.Template import Template
from xml.dom.minidom import parse
from pkg_resources import resource_stream, resource_filename

from graphtool.base.xml_config import XmlConfig
from gratia.database.query_handler import displayName
from graphtool.web.security import DenyAll

# Helper functions

class Gratia(XmlConfig):

    def __init__(self, *args, **kw):
        super(Gratia, self).__init__(*args, **kw)

        security_obj_name = self.metadata.get('security', False)
        if security_obj_name:
            self.security_obj = self.globals[security_obj_name]
        else:
            self.security_obj = DenyAll()

        #self.metadata['template_dir'] = '$GRAPHTOOL_USER_ROOT/templates'
        #self.template_dir = os.path.expandvars(self.metadata.get('template_dir', '.'))
        self.main = self.template('main.tmpl')(self.main)
        self.overview = self.template('overview.tmpl')(self.overview)
        self.vo_overview = self.template('vo_overview.tmpl')(self.vo_overview)
        self.vo_opp = self.template('vo_opp.tmpl')(self.vo_opp)
        self.vo_opp2 = self.template('vo_opp2.tmpl')(self.vo_opp2)
        self.vo_exitcode = self.template('vo_exitcode.tmpl')(self.vo_exitcode)
        self.site_owner = self.template('site.tmpl')(self.site_owner)
        self._cp_config ={}
        self.index = self.overview

    def getTemplateFilename(self, template):
        template_name = template.replace(".", "_").replace("-", "_") + "_filename"
        if not hasattr(self, template_name):
            filename = resource_filename("gratia.templates", template)
            setattr(self, template_name, filename)
        return getattr(self, template_name)

    def template(self, name=None):
        #template_file = os.path.join(self.template_dir, name)
        template_fp = resource_stream("gratia.templates", name)
        tclass = Template.compile(source=template_fp.read())
        def template_decorator(func):
            def func_wrapper(*args, **kw):
                data = func(*args, **kw)
                if data.get('is_authenticated', True):
                    base_url = self.metadata.get('base_url', '')
                else:
                    base_url = self.metadata.get('base_url_noauth', '')
                if base_url == '/':
                    base_url = ""
                addl = {'base_url': base_url}
                return str(tclass(namespaces=[data, addl]))
            func_wrapper.exposed = True
            return func_wrapper
        return template_decorator

    def generate_drilldown(self, option, url):
        def drilldown(pivot, group, base_url, filter_dict):
            filter_dict[option] = pivot
            filter_url = urllib.urlencode(filter_dict)
            return os.path.join(base_url, url) + '?' + filter_url
        return drilldown

    def generate_pg_map(self, token, maps, func, kw, drilldown_url, 
            drilldown_option):
        def worker(self, token, maps, func, kw, drilldown_url, 
                drilldown_option):
            #print "Start worker!", currentThread().getName()
            try:
                map = self.__generate_pg_map(func, kw, drilldown_url,
                    drilldown_option)
                token['condition'].acquire()
                maps.append(map)
                token['condition'].release()
            finally:
                token['condition'].acquire()
                token['counter'] -= 1
                token['condition'].notify()
                token['condition'].release()
                #print "Finish worker!", currentThread().getName()
        try:
            token['condition'].acquire()
            token['counter'] += 1
            token['condition'].notify()
            token['condition'].release()
            args = (self, token, maps, func, kw, drilldown_url, 
                    drilldown_option)
            Thread(target=worker, args=args).start()
        except:
            token['condition'].acquire()
            token['counter'] -= 1
            token['condition'].notify()
            token['condition'].release()


    def __generate_pg_map(self, func, kw, drilldown_url, drilldown_option):
        map = {}
        map['kind'] = 'pivot-group'
        results, metadata = func(**kw)
        assert metadata['kind'] == 'pivot-group'
        map['name'] = metadata['name']
        column_names = str(metadata.get('column_names',''))
        column_units = str(metadata.get('column_units',''))
        names = [ i.strip() for i in column_names.split(',') ]
        units = [ i.strip() for i in column_units.split(',') ]
        map['column_names'] = names
        map['column_units'] = units
        map['pivot_name'] = metadata['pivot_name']
        data = {}
        map['data'] = data
        map['drilldown'] = self.generate_drilldown(drilldown_option, 
            drilldown_url)
        coords = metadata['grapher'].get_coords(metadata['query'], metadata, 
            **metadata['given_kw'])
        for pivot, groups in results.items():
            data_groups = {}
            data[pivot] = data_groups
            if pivot in coords:
                coord_groups = coords[pivot]
                for group, val in groups.items():
                    if group in coord_groups:
                        coord = str(coord_groups[group]).replace('(', '').\
                            replace(')', '')
                        if type(val) == types.FloatType and abs(val) > 1:
                            val = "%.2f" % val
                        data_groups[group] = (coord, val)
        return map

    def user_roles(self, data):
        """
        Authenticate a user and get their roles
        """
        data['is_site_owner'] = False
        data['is_vo_owner'] = False
        data['is_view_other_users'] = False
        if not data['is_authenticated']:
            data['auth_count'] = 0
            return
        dn = data['dn']
        data['vo_ownership'] = self.security_obj.list_roles("vo_ownership", dn)
        data['site_ownership'] = self.security_obj.list_roles("site_ownership", \
            dn)
        data['user_ownership'] = self.security_obj.list_roles("users", dn)
        auth_count = 0
        if len(data['vo_ownership']) > 0:
            data['is_vo_owner'] = True
            auth_count += 1
        if len(data['user_ownership']) > 0:
            data['is_view_other_users'] = True
            auth_count += 1
        if len(data['site_ownership']) > 0:
            data['is_site_owner'] = True
            auth_count += 1
        data['is_super_user'] = False
        data['auth_count'] = auth_count

    def user_auth(self, data):
        dn = cherrypy.request.headers.get('SSL-CLIENT-S-DN',None)
        if dn:
            assert cherrypy.request.headers.get('SSL-CLIENT-VERIFY', \
                  'Failure') == 'SUCCESS'
            data['is_authenticated'] = True
            data['dn'] = dn
            data['name'] = displayName(dn)
        else:
            data['is_authenticated'] = False

    def assign_blank(self, dict, *args):
        for arg in args:
            if arg not in dict:
                dict[arg] = ''

    def copy_if_present(self, to_dict, from_dict, *args):
        for arg in args:
            if arg in from_dict and from_dict[arg] != '':
                to_dict[arg] = from_dict[arg]

    def refine(self, data, filter_dict, facility=True, vo=True, dn=True):
        relTime = data.get('relativetime', False)
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
            'exclude-facility', 'exclude-vo', 'user', 'user', 'exclude-dn')
        data['query_kw'] = dict(filter_dict)
        data['filter_url'] = urllib.urlencode(filter_dict)
        self.assign_blank(filter_dict, 'facility', 'vo', 'exclude-vo', \
            'exclude-facility', 'exclude-dn', 'user')
        data['filter_dict'] = filter_dict
        if data['filter_url'] != '': 
            data['filter_url'] = '?' + data['filter_url']
        data['refine'] = self.getTemplateFilename('refine.tmpl')
        data['refine_error'] = None

    def start_image_maps(self):
        return {'condition': Condition(), 'counter': 0}

    def finish_image_maps(self, token):
        c = token['condition']
        #print "Main thread waiting"
        c.acquire()
        while token['counter'] > 0:
            #print "Live image generator count:", token['counter']
            c.wait()
        c.release()

    def image_map(self, token, data, obj_name, func_name, drilldown_url, 
                  drilldown_option):
 
        token['condition'].acquire()
        try:
            maps = data.get('maps', [])
            data['maps'] = maps
        finally:
            token['condition'].release()
        self.generate_pg_map(token, maps, getattr(self.globals[obj_name], 
            func_name), data['query_kw'], drilldown_url, drilldown_option)
        token['condition'].acquire() 
        if 'image_maps' not in data:
            data['image_maps'] = self.getTemplateFilename('image_map.tmpl')
        token['condition'].release()

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
        external['GridScan'] = self.fetch_gridscan(data.get('facility'))
        external['GIP Validator'] = self.gip_validation(data['facility'])
        return data

    def fetch_gridscan(self, site):
        doc = urllib2.urlopen('http://scan.grid.iu.edu/cgi-bin/show_results?grid=1')
        in_row = False
        in_font = False
        link_re = re.compile('HREF="(.*?)"')
        link = "#"
        status = "Unknown"
        for line in doc.readlines():
            if line.find(site) >= 0:
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
                break
        return status, "http://scan.grid.iu.edu" + link

    def gip_validation(self, site):
        doc = urllib2.urlopen('http://gip-validate.grid.iu.edu/production')
        row_re = re.compile("<td valign='middle'>%s</td>" % site)
        info_re = re.compile("<td height='30' bgcolor='(.*?)'><a href='(.*?)'>")
        in_row = False
        result = "Unknown"
        link = "#"
        for line in doc.readlines():
            if row_re.search(line):
                in_row = True
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
                break
        return result, "http://gip-validate.grid.iu.edu/production/" + link

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

