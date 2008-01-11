
from graphtool.base.xml_config import XmlConfig
from gratia.database.query_handler import displayName
from graphtool.web.security import DenyAll
from Cheetah.Template import Template
import cherrypy, os, urllib

class Gratia(XmlConfig):

    def __init__(self, *args, **kw):
        super(Gratia, self).__init__(*args, **kw)

        security_obj_name = self.metadata.get('security', False)
        if security_obj_name:
            self.security_obj = self.globals[security_obj_name]
        else:
            self.security_obj = DenyAll()

        self.metadata['template_dir'] = '$GRAPHTOOL_USER_ROOT/templates'
        self.main = self.template('main.tmpl')(self.main)
        self.overview = self.template('overview.tmpl')(self.overview)
        self._cp_config ={}
        self.index = self.overview

    def template(self, name=None):
        template_dir = self.metadata.get('template_dir', '.')
        template_file = os.path.join(os.path.expandvars(template_dir), name)
        tclass = Template.compile(file=template_file)
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

    def user_roles(self, data):
        """
        Authenticate a user and get their roles
        """
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

    def main(self, *args, **kw):
        data = dict(kw)
        filter_dict = {}
        # Do user auth:
        self.user_auth(data)
        self.user_roles(data)
        relTime = kw.get('relativetime', False)
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
            'exclude-facility', 'exclude-vo')
        data['filter_url'] = urllib.urlencode(filter_dict)
        self.assign_blank(filter_dict, 'facility', 'vo', 'exclude-vo', \
            'exclude-facility')
        data['filter_dict'] = filter_dict
        if data['filter_url'] != '':
            data['filter_url'] = '?' + data['filter_url']
        if data['is_authenticated']:
            data['title'] = "OSG Storage Main for %s" % data['name']
        else:
            data['title'] = "OSG Storage Main"
        data['displayName'] = displayName
        data['urlquote'] = urllib.quote
        def select(val1, val2):
            if val1==val2:
                return "true"
            else:
                return "false"
        data['select'] = select
        return data

    def site_owner(self, *args, **kw):
        return "We're sorry, but the site owner page has not been written."
    site_owner.exposed = True

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
    overview.exposed = True
