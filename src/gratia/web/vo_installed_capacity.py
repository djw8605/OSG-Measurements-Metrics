
import calendar

from auth import Authenticate

class VOInstalledCapacity(Authenticate):

    def __init__(self, *args, **kw):
        super(VOInstalledCapacity, self).__init__(*args, **kw)
        self._r_to_rg = {}

    def mapResourceToResourceGroup(self, resource):
        if not self._r_to_rg:
            service_to_rg = self.globals['RSVQueries'].\
                service_to_resource_all()[0]
            for key, val in service_to_rg.items():
                print key, val
                self._r_to_rg[key[1]] = val
        return self._r_to_rg.get(resource, "UNKNOWN RESOURCE GROUP")

    def _voic_get_times(self, month, year):
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
        return starttime, endtime, month, year

    def site_table(self, vo, month=None, year=None, **kw):
        data = dict(kw)
        self.user_auth(data)
        self.user_roles(data)
        data['cmp'] = cmp 
        data['error'] = None
        data['vo'] = vo
        
        starttime, endtime, month, year = self.get_times(month, year)
        data['month'] = month
        data['month_name'] = calendar.month_name[month]
        data['year'] = year
        data['title'] = '%s Installed Capacity Report for %s %i' %(vo,
            data['month_name'], data['year'])

        subclusters = self.globals['GIPQueries'].subcluster_latest()[0]
        se_space = self.globals['GIPQueries'].se_space_pie()[0]

        resource_to_fed = self.globals['RSVQueries'].resource_to_federation()[0]

        capacity = {}
        def cmp2(x, y):
            i = cmp(x[1], y[1])
            if i == 0:
                return cmp(x[0], y[0])
            return i
        order = resource_to_fed.items()
        order.sort(cmp2)
        for resource, fed in resource_to_fed.items():
            if (fed.startswith('US') and vo.lower().find('cms') >= 0) or \
                    fed.startswith('T2') and vo.lower().find('atlas') >= 0:
                continue
            if resource.find('SE') >= 0:
                continue
            rinfo = {'Site': resource, 'Federation': fed}
            nproc_tot = 0
            si2k_tot = 0
            for entry, sdata in subclusters.items():
                ssite, scluster, ssubcluster = entry
                if ssite != resource:
                    continue
                _, _, nproc, si2k, ownership = sdata
                owners = ownership.split(',')
                perc = 0
                for i in owners:
                    if len(i.strip()) == 0:
                        continue
                    try:
                        owner, percent = i.split(':')
                        owner = owner.lower()
                        percent = int(percent.replace('%', '').strip())
                    except:
                        continue
                    if owner.find('cms') >= 0 and vo.lower().find('cms') >= 0:
                        pass
                    if owner.find('atlas') >= 0 and vo.lower().find('atlas') \
                            >= 0:
                        pass
                    elif owner.find(vo.lower()) >= 0:
                        pass
                    else:
                        continue
                    perc += percent
                if perc == 0:
                    perc = 100
                perc = perc / 100.
                nproc_tot += nproc * perc
                si2k_tot += nproc * si2k * perc
            rinfo['nproc'] = nproc_tot
            rinfo['si2k'] = si2k_tot
            tot_space = 0
            for sresource, ssize in se_space.items():
                resource_group = self.mapResourceToResourceGroup(sresource)
                if resource_group != resource:
                    continue
                tot_space += ssize
            rinfo['space'] = tot_space
            capacity[resource, fed] = rinfo
        order = [i for i in order if i in capacity]
        data['capacity'] = capacity
        data['order'] = order
        return data

