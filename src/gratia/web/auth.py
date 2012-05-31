
import cherrypy
import libxml2

from graphtool.web.security import DenyAll
from graphtool.base.xml_config import XmlConfig

from gratia.database.query_handler import displayName

class Authenticate(XmlConfig):

    def __init__(self, *args, **kw):
        super(Authenticate, self).__init__(*args, **kw)

        user_security_obj_name = self.metadata.get('user_security', False)
        vo_security_obj_name = self.metadata.get('vo_security', False)
        site_security_obj_name = self.metadata.get('site_security', False)
        if user_security_obj_name:
            self.user_security_obj = self.globals[user_security_obj_name]
        else:
            self.user_security_obj = DenyAll()
        if vo_security_obj_name:
            self.vo_security_obj = self.globals[vo_security_obj_name]
        else:
            self.vo_security_obj = DenyAll()
        if site_security_obj_name:
            self.site_security_obj = self.globals[site_security_obj_name]
        else:
            self.site_security_obj = DenyAll()
        print vo_security_obj_name


    def user_roles(self, data):
        """
        Authenticate a user and get their roles
        """
        if 'auth_count' in data:
            return
        data['is_site_owner'] = False
        data['is_vo_owner'] = False
        data['is_view_other_users'] = False
        data['is_vo_member'] = False
        if not data['is_authenticated']:
            data['auth_count'] = 0
            return
        dn = data['dn']
        data['vo_membership'] =[]
        data['vo_ownership']=[]
        data['site_ownership']=[]
        data['user_ownership']=[]
        try:
            doc = libxml2.parseFile("/tmp/myosg.cache.xml") #updated by cron defined in GratiaStaticGraphs.cron
            #types:
            #Submitter Contact
            #Administrative Contact
            #VO Manager
            #Security Contact
            #Miscellaneous Contact
            for vo in doc.xpathEval("//VO[ContactTypes//DN='%s']"%dn):
                currvo=(vo.xpathEval("Name")[0]).content
                data['vo_membership'].append(currvo)
                for voin in vo.xpathEval("ContactTypes/ContactType[Contacts/Contact/DN='%s']"%dn):
                    typeof=(voin.xpathEval("Type")[0]).content
                    if('VO Manager'==typeof):
                    #if('Miscellaneous Contact'==typeof):  #Testing
                        data['vo_ownership'].append(currvo)
                        for site in vo.xpathEval("MemeberResources/Resource/Name"):
                            data['site_ownership'].append(site.content)
                        for dn in vo.xpathEval("ContactTypes/ContactType/Contacts/Contact/DN"):
                            data['user_ownership'].append(dn.content)
        except:
            pass                  

        """
        #obsolted now
        data['vo_ownership'] = self.vo_security_obj.list_roles("vo_ownership",
            dn)
        data['site_ownership'] = self.site_security_obj.list_roles( \
            "site_ownership", dn)
        data['user_ownership'] = self.user_security_obj.list_roles("users", dn)
        data['vo_membership'] = self.user_security_obj.list_roles( \
            "vo_membership", dn)
        """
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
        if len(data['vo_membership']) > 0:
            data['is_vo_member'] = True
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

    def defaultData(self, data):
        super(Authenticate, self).defaultData(data)
        if 'is_authenticated' not in data:
            self.user_auth(data)
        super(Authenticate, self).defaultData(data)
        if data.get('is_authenticated', True):
            base_url = self.metadata.get('base_url', '')
            base_server = self.metadata.get("base_server", "")
        else:
            base_url = self.metadata.get('base_url_noauth', '')
            base_server = self.metadata.get("base_server_noauth", "")
        if base_url == '/':
            base_url = ""
        data['base_url'] = base_url
        data['base_server'] = base_server
