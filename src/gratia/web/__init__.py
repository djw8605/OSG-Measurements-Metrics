
import os
import urllib
import urllib2
import re
import sys
import time
import types
import calendar
import datetime
import cStringIO
import time

import cherrypy
from xml.dom.minidom import parse
from xml.dom.minidom import Node
from graphtool.tools.common import to_timestamp, convert_to_datetime
from graphtool.graphs.common_graphs import QualityMap, BarGraph, TimeGraph
from graphtool.graphs.basic import BasicStackedBar
from gratia.database.query_handler import displayName
from gratia.graphs.gratia_graphs import GratiaBar
from image_map import ImageMap
from auth import Authenticate
from navigate import Navigation
from wlcg_reporting import WLCGReporter
from jot_reporting import JOTReporter
from vo_installed_capacity import VOInstalledCapacity
from subcluster_report import SubclusterReport
from gratia_reporting import GratiaReporter

class Gratia(ImageMap, SubclusterReport, JOTReporter, VOInstalledCapacity, \
        GratiaReporter, WLCGReporter, Navigation):

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
        self.monbyvo_running_graphsonly = self.plain_template('monbyvo_running_graphsonly.tmpl')(self.monbyvo_running_graphsonly)
        self.monbyvo_waiting_graphsonly = self.plain_template('monbyvo_waiting_graphsonly.tmpl')(self.monbyvo_waiting_graphsonly)
        self.monbysite = self.template('monbysite.tmpl')(self.monbysite)
        self.wlcg_reporting = self.template('wlcg_reporting.tmpl')(\
            self.apel_data)
        self.jot_reporting = self.template('jot_uslhc.tmpl')(self.uslhc_table)
        self.email_lookup = self.template('email_lookup.tmpl')(\
            self.email_lookup)
        self.email_lookup_xml = self.plain_template('email_lookup_xml.tmpl',
            content_type='text/xml')(self.email_lookup_xml)
        self.subclusters = self.template('subcluster.tmpl')(self.subclusters)
        self.installed = self.template('installed_capacity.tmpl')\
            (self.site_table)
        self.site_report = self.template('gratia_site_report.tmpl')\
            (self.site_report)    
        self.pilot = self.template('pilot.tmpl')(self.pilot)
        self.project = self.template('project.tmpl')(self.project)
        self.factoryfrontend = self.template('factoryfrontend.tmpl')(self.factoryfrontend)

        configfile=''
        try:
            configfile=os.environ["DBPARAM_LOCATION"]                 
        except KeyError:
            configfile= "/etc/DBParam.xml"
        doc = parse(configfile)
        for node in doc.getElementsByTagName("staticfilehostname"):
            self.metadata['static_url']=node.getAttribute("value")  
        
        
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
            hours=True, default_rel_range=14*86400):
        relTime = data.get('relativetime', False)
        data['supports_hours'] = hours
        data['refine_vo'] = vo
        data['refine_facility'] = facility
        data['refine_dn'] = dn
        if relTime:
            if relTime == 'absolute':
                data['relTime'] = 'absolute'
		starttime = data.get('starttime', None)
                filter_dict['starttime'] = starttime
		while True: 
		 	try:
				valid = time.strptime(starttime,
                                    '%Y-%m-%d %H:%M:%S')
				break
			except ValueError: 
				relTime = 1209600
				break
		endtime = data.get('endtime', None)
		filter_dict['endtime'] = endtime
		while True: 
			try: 
                		valid2 = time.strptime(endtime,
                                    '%Y-%m-%d %H:%M:%S')
				break
			except ValueError: 
				relTime = 1209600
				break
                # try to determine default span
                try:
                    valid = datetime.datetime(*valid[:6])
                    valid2 = datetime.datetime(*valid2[:6])
                    timedelta = (valid2 - valid)
                    myinterval = timedelta.days * 86400 + timedelta.seconds
                    if myinterval < 4*86400:
                        default_span = 3600
                    elif myinterval <= 30*86400: 
                        default_span = 86400
                    elif myinterval < 365*86400:
                        default_span = 86400*7
                    else:
                        default_span = 86400*30
                except:
                    default_span = 86400
                # Set the span, defaulting to the determined default_span
                try:
                    filter_dict['span'] = int(data['span'])
                except:
                    filter_dict['span'] = default_span
            if relTime != 'absolute':
		data['relTime'] = relTime
                try:
                    interval = int(relTime)
                except:
                    raise ValueError("relTime must be an integer;" \
                        " input was %s." % relTime)
                filter_dict['starttime'] = 'time.time()-%i' % interval
                filter_dict['endtime'] = 'time.time()'
                if interval < 4*86400:
                    filter_dict['span'] = 3600
                elif interval <= 30*86400: 
                    filter_dict['span'] = 86400
                elif interval < 365*86400:
                    filter_dict['span'] = 86400*7
                else:
                    filter_dict['span'] = 86400*30
        else:
            data['relTime'] = 'absolute'

        self.copy_if_present(filter_dict, data, 'facility', 'vo', \
            'exclude-facility', 'exclude-vo', 'user', 'user', 'exclude-dn', \
            'vo_set', 'facility_set')
        if len(filter_dict.get('facility', '')) == 0 and 'facility_set' in \
                filter_dict:
            try:
                filter_dict['facility'] = '|'.join(self.site_sets[\
                    filter_dict['facility_set']])
            except:
                raise ValueError("Unknown facility set: %s." % \
                    filter_dict['facility_set'])
        print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> %s "%filter_dict
        if len(filter_dict.get('vo', '')) == 0 and 'vo_set' in \
                filter_dict:
            try:
                filter_dict['vo'] = '|'.join(self.site_sets[\
                    filter_dict['vo_set']])
            except:
                raise ValueError("Unknown VO set: %s." % \
                    filter_dict['vo_set'])
        data['query_kw'] = dict(filter_dict)

        if 'starttime' not in filter_dict:
            data['display_starttime'] = convert_to_datetime(time.time()-\
                default_rel_range)
        else:
            data['display_starttime'] = convert_to_datetime(\
                filter_dict['starttime'])
        data['display_starttime'] = data['display_starttime'].strftime(\
            '%Y-%m-%d %H:%M:%S')
        if 'endtime' not in filter_dict:
            data['display_endtime'] = convert_to_datetime(time.time()-\
                default_rel_range)
        else:
            data['display_endtime'] = convert_to_datetime(\
                filter_dict['endtime'])
        data['display_endtime'] = data['display_endtime'].strftime(\
            '%Y-%m-%d %H:%M:%S')

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
            #self.image_map(token, data, 'GratiaBarQueries', 
            #               'facility_transfer_rate', 'main', 'facility')
            self.image_map(token, data, 'GratiaBarQueries',
                'facility_hours_bar_smry', 'main', 'facility')
            #self.image_map(token, data, 'GratiaBarQueries', 
            #               'facility_quality', 'main', 'facility')
                           
            #self.image_map(token, data, 'GratiaBarQueries',
            #               'facility_transfer_volume', 'main', 'facility')
        else:
            self.image_map(token, data, 'GratiaBarQueries',
                'vo_hours_bar_smry', 'main', 'vo')
            #self.image_map(token, data, 'GratiaBarQueries', 'vo_transfer_rate',
            #               'main', 'vo')
            #self.image_map(token, data, 'GratiaBarQueries', 'vo_quality',
            #               'main', 'vo')
            #self.image_map(token, data, 'GratiaBarQueries', 
            #               'vo_transfer_volume', 'main', 'vo')
                           
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
        self.image_map(token, data, 'GratiaTransferQueries',
            'facility_transfer_volume', 'site', 'facility')

        # Special alteration for RSV graph.
        data2 = dict(data)
        data2['filter_dict'] = dict(data2['filter_dict'])
        if 'facility' in data2['filter_dict'] and data2['filter_dict']['facility'] == '':
            del data2['filter_dict']['facility']
        data3 = dict(data2['filter_dict'])
        data3['fixed-height'] = 'False'
        data['filter_url2'] = urllib.urlencode(data3)
        if data['filter_url2'] != '':
            data['filter_url2'] = '?' + data['filter_url2']

        #self.image_map(token, data2, "RSVSummaryQueries",
        #    "reli_summary_daily", "site", "facility")

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
        self.image_map(token, data, 'GratiaStatusQueries',
            'status_facility', 'site', 'facility')
        self.image_map(token, data, 'GratiaStatusQueries',
            'status_facility_pie', 'site', 'facility')
        #self.image_map(token, data, 'GIPQueries',
        #    'gip_free_cpu_realtime', 'site', 'facility')
        #self.image_map(token, data, 'GIPQueries',
        #    'gip_free_cpus_history', 'site', 'facility')
        self.image_map(token, data, 'GratiaStatusQueries',
            'status_facility_waiting', 'site', 'facility')
        self.image_map(token, data, 'GratiaStatusQueries',
            'status_facility_waiting_pie', 'site', 'facility')

        self.finish_image_maps(token)

        if data['is_authenticated']:
            data['title'] = "OSG Monitoring Information By Site for %s" % \
                data['name']
        else:
            data['title'] = "OSG Monitoring Information By Site"
        return data


    def factoryfrontend(self, *args, **kw):
        data = dict(kw)
        data['given_kw'] = dict(kw)
        self.user_auth(data)
        filter_dict = {}
        # Handle the refine variables
        self.refine(data, filter_dict)
        token = self.start_image_maps()
        # Generate image maps:
        self.image_map(token, data, 'GratiaStatusQueries',
            'status_facility', 'site', 'facility')
        self.finish_image_maps(token)
        data['title'] = "OSG Project Accounting"
        return data

    def project(self, *args, **kw):
        data = dict(kw)
        data['given_kw'] = dict(kw)
        self.user_auth(data)
        filter_dict = {}
        # Handle the refine variables
        self.refine(data, filter_dict)
        token = self.start_image_maps()
        # Generate image maps:
        self.image_map(token, data, 'GratiaStatusQueries',
            'status_facility', 'site', 'facility')
        self.finish_image_maps(token)
        data['title'] = "OSG Project Accounting"
        return data

    def pilot(self, *args, **kw):
        data = dict(kw)
        data['given_kw'] = dict(kw)
        self.user_auth(data)
        filter_dict = {}

        # Handle the refine variables
        self.refine(data, filter_dict)
        token = self.start_image_maps()
        # Generate image maps:
        self.image_map(token, data, 'GratiaStatusQueries',
            'status_facility', 'site', 'facility')
        #self.image_map(token, data, 'GratiaStatusQueries',
        #    'status_facility_pie', 'site', 'facility')
        #self.image_map(token, data, 'GIPQueries',
        #    'gip_free_cpu_realtime', 'site', 'facility')
        #self.image_map(token, data, 'GIPQueries',
        #    'gip_free_cpus_history', 'site', 'facility')
        #self.image_map(token, data, 'GratiaStatusQueries',
        #    'status_facility_waiting', 'site', 'facility')
        #self.image_map(token, data, 'GratiaStatusQueries',
        #    'status_facility_waiting_pie', 'site', 'facility')

        self.finish_image_maps(token)

        data['title'] = "OSG Pilot and Campus Accounting"
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
    def monbyvo_running_graphsonly(self, *args, **kw):
        data = dict(kw)
        data['given_kw'] = dict(kw)
        self.user_auth(data)
        # Handle the refine variables
        self.refine(data, data, dn=False, hours=False)
        token = self.start_image_maps()
        # Generate image maps:
        self.image_map(token, data, 'GratiaStatusQueries',
            'status_vo', 'monbyvo_running_graphsonly', '')
        self.finish_image_maps(token)
        return data

    def monbyvo_waiting_graphsonly(self, *args, **kw):
        data = dict(kw)
        data['given_kw'] = dict(kw)
        self.user_auth(data)
        # Handle the refine variables
        self.refine(data, data, dn=False, hours=False)
        token = self.start_image_maps()
        # Generate image maps:
        self.image_map(token, data, 'GratiaStatusQueries',
            'status_vo_waiting', 'monbyvo_waiting_graphsonly', '')
        self.finish_image_maps(token)
        return data


    def monbyvo(self, *args, **kw):
        data = dict(kw)
        data['given_kw'] = dict(kw)
        self.user_auth(data)
        filter_dict = {}
        #filter_dict['title']=title
        # Handle the refine variables
        self.refine(data, filter_dict, dn=False, hours=False)
        token = self.start_image_maps()
        # Generate image maps:
        self.image_map(token, data, 'GratiaStatusQueries',
            'status_vo', 'site', 'facility')
        self.image_map(token, data, 'GratiaStatusQueries',
            'status_vo_pie', 'site', 'facility')
        self.image_map(token, data, 'GratiaStatusQueries',
            'status_vo_waiting', 'site', 'facility')
        self.image_map(token, data, 'GratiaStatusQueries',
            'status_vo_waiting_pie', 'site', 'facility')

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

        data['title'] = 'Site owner view for %s' % data['facility']

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
        #external['GridScan'] = self.fetch_gridscan(data['facility'])
        #external['GIP Validator'] = self.gip_validation(data['facility'])
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
            'osg_facility_hours', 'site', 'facility')
        self.image_map(token, data, 'GratiaPieQueries',
            'osg_facility_count', 'site', 'facility')
        self.image_map(token, data, 'GratiaBarQueries',
            'facility_hours_bar_smry', 'site', 'facility')
        self.image_map(token, data, 'GratiaBarQueries',
            'vo_opp_hours_bar2', 'site', 'facility')
        self.image_map(token, data, 'GratiaCumulativeQueries',
            'facility_success_cumulative_smry', 'site', 'facility')
        self.finish_image_maps(token)

        data['title'] = 'VO Information'
        return data

    def rsv_reporting(self, *args, **kw):
        data = dict(kw) 
        data['given_kw'] = kw
        filter_dict = {} 
            
        #User auth
        self.user_auth(data)
        #Handle refine
        self.refine(data, filter_dict, facility=False)

        token = self.start_image_maps()
        #Generate image maps
        self.image_map(token, data, 'RSVQueries',
            'rsv_quality', 'rsv_site', 'facility')
        self.image_map(token, data, 'RSVQueries',
            'rsv_dist', None, None)
        self.finish_image_maps(token)

        data['title'] = 'RSV Information'
        return data

    def rsv_site(self, **kw):
        data = dict(kw)
        data['given_kw'] = kw
        filter_dict = {}
        data['error'] = False

        if 'facility' not in data:
            data['error'] = 'No facility present in the URL; try adding ' \
                '?facility=<name> to the URL.'

        self.user_auth(data)
        self.refine(data, filter_dict, facility=False)
        
        token = self.start_image_maps()
        self.image_map(token, data, 'RSVQueries', 'rsv_metric_quality', \
            'rsv_site', 'facility')
        self.finish_image_maps(token)

    def fetch_gridscan(self, site):
        return []
        #doc = urllib2.urlopen('http://scan.grid.iu.edu/cgi-bin/show_results' \
        #    '?grid=1')
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

    def gratia_live_display(self, *args, **kw):
        bars = int(kw.get('bars', 12))
        orig_bars = bars
        bars += 3
        span = int(kw.get('span', 600))
        now = time.time()
        start = now - span*bars
        minutes = span*bars/60
        kw = {\
              'span': span,
              'starttime': start-(start % span),
              'endtime': now - (now % span),
              'minutes': minutes,
             }
        str = ''
        results, metadata = self.globals['GratiaRTQueries'].live_display(**kw)
        keys = results.keys()
        keys.sort()
        keys = keys[-orig_bars:]
        for pivot in keys:
            cnt = results[pivot]
            pivot = int(pivot)
            #pivot = time.gmtime(pivot)
            #pivot = time.strftime("%Y-%m-%d %H:%M:%S", pivot)
            str += '%s,%i\n' % (pivot, cnt)

        cherrypy.response.headers['Content-Type'] = 'text/plain'

        return str
    gratia_live_display.exposed = True

    def osg_site_size(self, *args, **kw):
        results, metadata = self.globals['GratiaBarQueries'].osg_site_size(**kw)
        info = ['Site,Max Used,Total']
        USED = 'Max Used'
        UNACCESSIBLE = 'In OSG, but never used'
        for site in results[USED].keys():
            used = results[USED].get(site, None)
            unaccessible = results[UNACCESSIBLE].get(site, None)
            if used != None and unaccessible != None:
                info.append('%s,%i,%i' % (site, used, used + unaccessible))
        cherrypy.response.headers['Content-Type'] = 'text/plain'
        return '\n'.join(info)
    osg_site_size.exposed = True

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
        reg_vos = self.get_variable_values(registered_vos_url)
        reg_vos = [i.lower() for i in reg_vos]
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
            '/gratia/xml/vo')
        keep_vos = [i.strip() for i in self.metadata.get('keep_vos', \
            '').split(',') if len(i.strip()) > 0]
        if kw.get('filter', 'true').lower() == 'false':
            vos = self.get_variable_values(vos_url)
        else:
            vos = self.get_vo_list(vos_url, registered_vos_url, keep_vos)
        data['vos'] = vos
        data['current_vo'] = kw.get('vo', None)
        data['static_url'] = self.metadata.get('static_url', '/store/gratia')
        data['title'] = 'VO Overview'
        return data

    def vo_opp(self, *args, **kw):
        data = dict(kw)
        self.user_auth(data)
        vos_url = self.metadata.get('vos_url', '/gratia/xml/vo_corrected_table')
        registered_vos_url = self.metadata.get('registered_vos_url', \
            '/gratia/xml/vo')
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
            '/gratia/xml/vo')
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
            '/gratia/xml/vo')
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

    def email_lookup(self, **kw):
        data = dict(kw)
        data['title'] = "User email lookup"
        dn = data.get('dn', None)
        data['query_dn'] = dn
        self.user_auth(data)
        self.user_roles(data)
        if dn == None:
            data['is_query'] = False
        else:
            data['is_query'] = True
            data['results'] = self.globals['GratiaSecurity'].email_lookup(dn=dn)[0]
            data['displayName'] = displayName
        return data

    email_lookup_xml = email_lookup

    def uscms_t2_site_avail(self):
        url = self.metadata['dashboard_sam_url']
        req = urllib2.Request(url, headers={"Accept": "text/xml"})
        handler = urllib2.HTTPHandler()
        fp = handler.http_open(req)
        dom = parse(fp)
        cherrypy.response.headers['Content-Type'] = 'image/png'
        data_dom = dom.getElementsByTagName("data")[0]
        data = {}
        begin = None
        end = None
        for item in data_dom.getElementsByTagName("item"):
            timestamp_dom = item.getElementsByTagName("TimeStamp")[0]
            av_dom = item.getElementsByTagName("AvValue")[0]
            voname_dom = item.getElementsByTagName("VOName")[0]
            timestamp_str = str(timestamp_dom.firstChild.data)
            time_tuple = time.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            timestamp = datetime.datetime(*time_tuple[:6])
            if not begin:
                begin = timestamp
            if not end:
                end = timestamp
            begin = min(timestamp, begin)
            end = max(timestamp, end)
            av = float(av_dom.firstChild.data)
            voname = str(voname_dom.firstChild.data)
            site_dict = data.get(voname, {})
            data[voname] = site_dict
            site_dict[timestamp] = av
        metadata = {'title':'USCMS T2 SAM Availability', 'span':86400,
            'starttime':begin, 'endtime':end,
            'color_override': {-2:'grey'}}
        fp = cStringIO.StringIO()
        QM = QualityMap()
        QM(data, fp, metadata)
        return fp.getvalue()
    uscms_t2_site_avail.exposed=True

    def cms_site_avail(self):
        url = self.metadata['dashboard_sam_url_all']
        req = urllib2.Request(url, headers={"Accept": "text/xml"})
        handler = urllib2.HTTPHandler()
        fp = handler.http_open(req)
        dom = parse(fp)
        cherrypy.response.headers['Content-Type'] = 'image/png'
        data_dom = dom.getElementsByTagName("data")[0]
        data = {}
        begin = None
        end = None
        for item in data_dom.getElementsByTagName("item"):
            timestamp_dom = item.getElementsByTagName("TimeStamp")[0]
            av_dom = item.getElementsByTagName("AvValue")[0]
            voname_dom = item.getElementsByTagName("VOName")[0]
            timestamp_str = str(timestamp_dom.firstChild.data)
            time_tuple = time.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            timestamp = datetime.datetime(*time_tuple[:6])
            if not begin:
                begin = timestamp
            if not end:
                end = timestamp
            begin = min(timestamp, begin)
            end = max(timestamp, end)
            av = float(av_dom.firstChild.data)
            voname = str(voname_dom.firstChild.data)
            site_dict = data.get(voname, {})
            data[voname] = site_dict
            site_dict[timestamp] = av
        metadata = {'title':'CMS SAM Availability', 'span':86400,
            'starttime':begin, 'endtime':end, 'fixed-height': False,
            'color_override': {-2:'grey'}}
        fp = cStringIO.StringIO()
        QM = QualityMap()
        QM(data, fp, metadata)
        return fp.getvalue()
    cms_site_avail.exposed=True

    def d0(self, weekly=False):
        cherrypy.response.headers['Content-Type'] = 'image/png'
        url = self.metadata.get('d0_csv', 'http://physics.lunet.edu/~snow/' \
            'd0osgprod.csv')
        url_fp = urllib2.urlopen(url)
        metadata = {'croptime':True, 'span':86400, 'pivot_name': 'OSG Site', \
            'grouping_name': 'Date', 'column_names': 'Merged Events', \
            'title': 'D0 OSG Production'}
        if weekly:
            metadata['span'] *= 7
        fp = cStringIO.StringIO()
        data = {}
        for line in url_fp.readlines():
            info = line.strip().split(',')
            grouping_name = time.strptime(info[0], '%y%m%d')
            group = datetime.datetime(*grouping_name[:6])
            # Change the date to the first day of that week; groups things
            # by week instead of the default by day.
            if weekly:
                weekday = group.isoweekday()
                group -= datetime.timedelta(weekday, 0)
            print info[0], group
            pivot = info[1]
            results = int(info[3])
            if pivot not in data:
                data[pivot] = {}
            grouping_dict = data[pivot]
            if group not in grouping_dict:
                grouping_dict[group] = results
            else:
                grouping_dict[group] += results
        BSB = BasicStackedBar()
        BSB(data, fp, metadata)
        return fp.getvalue()
    d0.exposed = True

    def d0_basic(self, weekly=False):
        cherrypy.response.headers['Content-Type'] = 'image/png'
        url = self.metadata.get('d0_csv', 'http://physics.lunet.edu/~snow/' \
            'd0osgprod.csv')
        url_fp = urllib2.urlopen(url)
        metadata = {'croptime':False, 'span':86400, 'pivot_name': 'Date', \
            'column_names': 'Merged Events', \
            'title': 'D0 OSG Production'}
        if weekly:
            metadata['span'] *= 7
        fp = cStringIO.StringIO()
        data = {}
        for line in url_fp.readlines():
            info = line.strip().split(',')
            grouping_name = time.strptime(info[0], '%y%m%d')
            group = datetime.datetime(*grouping_name[:6])
            # Change the date to the first day of that week; groups things
            # by week instead of the default by day.
            if weekly:
                weekday = group.isoweekday()
                group -= datetime.timedelta(weekday, 0)
            group = to_timestamp(group)
            results = int(info[3])
            value = data.setdefault(group, 0)
            data[group] = value + results
        metadata['starttime'] = min(data.values())
        time_max = max(data.values())
        if weekly:
            metadata['endtime'] = time_max + 7*86400
        else:
            metadata['endtime'] = time_max + 1*86400
        GB = GratiaBar()
        GB(data, fp, metadata)
        return fp.getvalue()
    d0_basic.exposed = True

