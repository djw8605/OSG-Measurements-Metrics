
from auth import Authenticate

class SubclusterReport(Authenticate):

    def subclusters(self, timestamp=None):
        if timestamp==None:
            subclusters = self.globals['GIPQueries'].subcluster_latest()[0]
        else:
            subclusters = self.globals['GIPQueries'].subcluster_latest( \
                endtime=timestamp)[0]
        time_list = self.globals['GIPQueries'].subcluster_times()
        data['subclusters'] = subclusters

        # When the GIP recorded these subclusters.
        report_time = None
        for key, val in data['subclusters'].items():
            if report_time == None:
                report_time = val[0]
                break
        data['gip_report_time'] = report_time

        data['time_list'] = time_list
        data['title'] = 'Subclusters reported by the GIP.'
        return data

