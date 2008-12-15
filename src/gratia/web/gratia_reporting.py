
import sets
import datetime
import calendar

from auth import Authenticate

class GratiaReporter(Authenticate):

    def site_report(self, day=None, month=None, year=None, **kw):
        oday, omonth, oyear = day, month, year
        data = dict(kw)
        self.user_auth(data)
        self.user_roles(data)
        data['cmp'] = cmp
        data['error'] = None

        starttime, endtime, day, month, year = self._gratia_get_times(oday,
            omonth, oyear)
        print day, oday
        data['day'] = day
        data['month'] = month
        data['month_name'] = calendar.month_name[month]
        data['year'] = year
        data['title'] = 'OSG Site Report for %i %s %i' % (day,
            data['month_name'], data['year'])

        info = {\
            'starttime': starttime.strftime('%Y-%m-%d %H:%M:%S'),
            'endtime':   endtime.  strftime('%Y-%m-%d %H:%M:%S'),
            'exclude-vo': 'unknown',
        }
        starttime, endtime, _, _, _ = self._gratia_get_times(oday,
            omonth, oyear, length=7, offset=1)
        info2 = {\
            'starttime': starttime.strftime('%Y-%m-%d %H:%M:%S'),
            'endtime':   endtime.  strftime('%Y-%m-%d %H:%M:%S'),
            'exclude-vo': 'unknown',
        }

        site_report_daily = self.globals['GratiaDataQueries'].\
            site_report(**info)[0]
        site_report_weekly = self.globals['GratiaDataQueries'].\
            site_report(**info2)[0]

        # By default, remove all non-registered resources
        if kw.get('all', 'False').lower().find('f') >= 0:
            services = self.globals['RSVQueries'].service_to_resource_all()[0]
            resources = [i[1] for i in services if i[0].find('CE') >= 0]
            bad_resources = []
            for resource in site_report_weekly:
                if resource not in resources:
                    bad_resources.append(resource)
            for resource in bad_resources:
                del site_report_weekly[resource]
            bad_resources = []
            for resource in site_report_daily:
                if resource not in resources:
                    bad_resources.append(resource)
            for resource in bad_resources:
                del site_report_daily[resource]

        # Make sure that daily and weekly lists have the same resources
        all_resources = sets.Set()
        all_resources.update(site_report_daily.keys())
        all_resources.update(site_report_weekly.keys())
        default = (0., 0., 0., 0., 0., 0.)
        print site_report_weekly['Nebraska']
        for resource in all_resources:
            site_report_daily.setdefault(resource, default)
            site_report_weekly.setdefault(resource, default)
            site_report_weekly[resource] = list(site_report_weekly[resource])
            site_report_weekly[resource][1] /= 7.
            site_report_weekly[resource][2] /= 7.
            site_report_weekly[resource][4] /= 7.
            site_report_weekly[resource][5] /= 7.
        print site_report_weekly['Nebraska']

        data['site_daily'] = site_report_daily
        data['site_weekly'] = site_report_weekly
        def cmp2(x, y):
            val = cmp(site_report_daily.get(x, [0])[0],
                site_report_daily.get(y, [0])[0])
            if val == 0:
                return cmp(x, y)
            return val
        sorting = site_report_daily.keys()
        sorting.sort(cmp2)
        data['sorting'] = sorting
        data['round'] = round
        return data

    def _gratia_get_times(self, day, month, year, offset=0, length=1):
        today = datetime.datetime.utcnow()
        if month == None:
            month = today.month
        else:
            month = int(month)
        if year == None:
            year = today.year
        else:
            year = int(year)
        if day == None:
            day = datetime.datetime(year, month, today.day)
            day -= datetime.timedelta(1, 0)
        else:
            day = datetime.datetime(year, month, int(day))
        day -= datetime.timedelta(offset+length-1, 0)
        end_day = day + datetime.timedelta(length, 0)
        
        starttime = day
        endtime = end_day
        return starttime, endtime, day.day, day.month, day.year

