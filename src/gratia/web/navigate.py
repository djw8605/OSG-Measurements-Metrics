
import urllib

from graphtool.base.xml_config import XmlConfig
from template import Template
from auth import Authenticate

class Navigation(Authenticate, Template):

    def parse_dom(self):
        super(Navigation, self).parse_dom()
        self.site_sets = {}
        self.vo_sets = {}
        for setsDom in self.dom.getElementsByTagName("sets"):
            for setDom in setsDom.getElementsByTagName("set"):
                name = setDom.getAttribute("name")
                kind = setDom.getAttribute("kind")
                text = str(setDom.firstChild.data).strip()
                info = [i.strip() for i in text.split(',')]
                if kind == 'site':
                    self.site_sets[name] = info
                elif kind == 'vo':
                    self.vo_sets[name] = info

    def navFromRoles(self, data):
        self.user_roles(data)
        if data['is_site_owner']:
            sites = {}
            for site in data['site_ownership']:
                sites[site] = 'site?facility=%s' % site
            data['navigation']['Site Owner'] = sites
        if data['is_vo_owner']:
            vos = {}
            for vo in data['vo_ownership']:
                vos[vo] = 'vo_owner?vo=%s' % vo
            data['navigation']['VO Owner'] = vos
        if data['is_vo_member']:
            vos = {}
            for vo in data['vo_membership']:
                vos[vo] = 'vo?vo=%s' % vo
            data['navigation']['VO Membership'] = vos

    def gridNav(self, data):
        info = {"Accounting By Site": "bysite",
                "Accounting By VO":   "byvo",
                "Monitoring By Site": "monbysite",
                "Monitoring By VO":   "monbyvo",
                "Opportunistic Usage": "vo_opp",
               }
        data['navigation']['Grid-wide'] = info

    def otherNav(self, data):
        info = {}
        data['navigation']['Other'] = info
        for vo, members in self.vo_sets.items():
            set_info = '|'.join(members)
            set_info = urllib.quote(set_info, safe='')
            info['%s' % vo] = 'vo?set=%s&vo=%s' % (vo, set_info)
        for site, members in self.site_sets.items():
            set_info = '|'.join(members)
            set_info = urllib.quote(set_info, safe='')
            info['%s' % site] = 'site?set=%s&facility=%s' % (site, set_info)
        
    def defaultData(self, data):
        x = XmlConfig()
        data['vo_list'] = [i[0] for i in x.\
            globals['GratiaDataQueries'].vo_list()[0]]
        data['site_list'] = [i[0] for i in x.\
            globals['GratiaDataQueries'].site_list()[0]]
        super(Navigation, self).defaultData(data)
        data['navigation'] = data.get('navigation', {})
        self.navFromRoles(data)
        self.gridNav(data)
        self.otherNav(data)
        return data

