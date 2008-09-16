
import datetime
import calendar

from auth import Authenticate

class JotReporting(Authenticate):

    def __init__(self):
        pass

    def uslhc_table(self, month=None, year=None, **kw):
        data = dict(kw)
        self.user_auth(data)
        self.user_roles(data)
        data['month'] = month
        data['year'] = year
        data['month_name'] = calendar.month_name[name]
        data['cmp'] = cmp

        starttime, endtime = self.get_times(month, year)
        info = {\
            'starttime': starttime.strftime('%Y-%m-%d %H:%M:%S'),
            'endtime':   endtime.  strftime('%Y-%m-%d %H:%M:%S'),
            'exclude-vo': 'unknown',
        }
        cpu_hours = self.globals['GratiaPieQueries'].osg_facility_cpu_hours(\
            info)[0]
        wall_hours = self.globals['GratiaPieQueries'].osg_facility_hours(\
            info)[0]

        info['vo'] = 'atlas|cms'
        lhc_cpu_hours = self.globals['GratiaPieQueries'].\
            osg_facility_cpu_hours(info)[0]
        lhc_wall_hours = self.globals['GratiaPieQueries'].\
            osg_facility_cpu_hours(info)[0]

        associations = self.globals['RSVQueries'].service_to_resource()[0]
        associations = associations.keys()

        federations = self.globals['RSVQueries'].resource_to_federation()[0]

        del info['exclude-vo']
        resource_reliability = self.globals['RSVSummaryQueries'].\
            reli_summary_monthly(info)[0]
        resource_availability = self.globals['RSVSummaryQueries'].\
            avail_summary_monthly(info)[0]

        data['reliability'] = {}
        data['availability'] = {}
        data['cpu'] = {}
        data['count'] = {}
        data['wall'] = {}
        data['lhc_cpu'] = {}
        data['lhc_wall'] = {}

        for resource, fed in federations.items():
            data['reliability'].set_default(fed, 0)
            data['reliability'][fed] += reliability.get(resource, 0)
            data['availability'].set_default(fed, 0)
            data['availability'][fed] += availability.get(resource, 0)
            data['cpu'].set_default(fed, 0)
            data['cpu'][fed] += cpu_hours.get(resource, 0)
            data['count'].set_default(fed, 0)
            data['count'] += 1
            data['wall'].set_default(fed, 0)
            data['wall'][fed] += wall_hours.get(resource, 0)
            data['lhc_cpu'].set_default(fed, 0)
            data['lhc_cpu'][fed] += lhc_cpu_hours.get(resource, 0)
            data['lhc_wall'].set_default(fed, 0)
            data['lhc_wall'][fed] += lhc_wall_hours.get(resource, 0)


    def get_times(self, month, year)
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
        return starttime, endtime

