#!/usr/bin/env python

import re
import os
import types
import datetime
import calendar
import smtplib
import urllib
import urllib2
import optparse
import ConfigParser

from email.MIMEText import MIMEText
from email.MIMEImage import MIMEImage
from email.MIMEMultipart import MIMEMultipart
from email.Utils import formataddr

from gratia.utility.make_table import Table

ftoa_re = re.compile(r'(?<=\d)(?=(\d\d\d)+(\.|$))')
def ftoa(s):
    """
    Converts a float or integer to a properly comma-separated string using
    regular expressions.  Kudos to anyone who can actually read the RE.
    """
    return ftoa_re.sub(',', str(s))

def loadConfig():
    """
    Loads up the config parser object for the WLCG email.
    """
    cp = ConfigParser.ConfigParser()

    fps = []
    try:
        from pkg_resources import resource_stream
        fps.append(resource_stream("gratia.config", "wlcg_email.conf"))
    except:
        pass
    fps.append('/etc/wlcg_email.conf')

    parser = optparse.OptionParser()
    parser.add_option("-c", "--config", dest="config", help="Comma-separated "\
        "list of config files.", default="")
    parser.add_option("-d", "--dev", dest="dev", action="store_true", \
        default=False, help="Development mode email.")
    parser.add_option("-l", "--lastmonth", dest="lastmonth", \
        action="store_true", default=False, help="Show last month's data.")
    (options, args) = parser.parse_args()
    for entry in options.config.split(','):
        entry = entry.strip()
        if os.path.exists(entry):
            fps.append(open(entry, 'r'))
    for fp in fps:
        cp.readfp(fp)
    if not cp.has_section("info"):
        cp.add_section("info")
        cp.set("info", "url", "http://t2.unl.edu/gratia/pledge_table")
    cp.set("info", "dev", str(options.dev))
    if options.lastmonth:
        cp.set("info", "lastmonth", "True")
    else:
        cp.set("info", "lastmonth", "False")
    return cp

#toStr = ['bbockelm@cse.unl.edu']
#toNames = ["Brian Bockelman"]
#fromStr = 'bbockelm@t2.unl.edu'
subject = "WLCG Pledge data for %s %s"
email_plain = \
"""Below is the pledge data so far for %(month)s %(year)s.  This data was recorded from the beginning of the month until %(report_time)s.

Note: We have recently changed this report to show CPU-hours instead of Wall-hours; this drastically changes the percentages for some sites.

ATLAS T2 Sites
%(atlas_plain_table)s
CMS T2 Sites
%(cms_plain_table)s
For each WLCG accounting site, we show the following information:
   - %(pledge_year)s KSI2K Pledge: The size of the resource, as measured in KSI2K.
   - Month goal for KSI2K-hours: The number of hours in the month times the pledged size of the resource times the month's efficiency (currently 60%%).
   - KSI2K-hours for the owning VO: KSI2K hours are CPU-hours multiplied by the average KSI2K rating of the resource
   - KSI2K-hours for all WLCG VOs
   - Site's total KSI2K-hours
   - Percentage of the WLCG goal accomplished.  Percentage is based only on the entire month's goal.
   - Percentage of the site's total time delivered to non-WLCG VOs.

This is a summary of the available data; a more thorough analysis is available at:

http://t2.unl.edu/gratia/wlcg_reporting

Thank you for your consideration,
OSG Metrics and Measurements
"""

email_html = """

<p>Below is the pledge data so far for <b>%(month)s %(year)s</b>.  This data was recorded from the beginning of the month until %(report_time)s.</p>

<br/>
<p style='font-weight: bold;'>Note: We have recently changed this report to show CPU-hours instead of Wall-hours; this drastically changes the percentages for some sites.</p>

For each WLCG accounting site, we show the following information:
<ul>
   <li>%(pledge_year)s KSI2K Pledge: The size of the resource, as measured in KSI2K.</li>
   <li>Month goal for KSI2K-hours: The number of hours in the month times the pledged size of the resource times the month's efficiency (currently 60%%).</li>
   <li>KSI2K-hours for the owning VO: KSI2K hours are CPU-hours multiplied by the average KSI2K rating of the resource</li>
   <li>KSI2K-hours for all WLCG VOs</li>
   <li>Site's total KSI2K-hours</li>
   <li>Percentage of the WLCG KSI2K-hours goal accomplished. Percentage is based only on the entire month's goal.</li>
   <li>Percentage of the site's total time delivered to non-WLCG VOs.</li>
</ul>

<h2>ATLAS T2 Sites</h2>
%(atlas_html_table)s

<h2>CMS T2 Sites</h2>
%(cms_html_table)s

<br/>

<p>This is a summary of the available data; a more thorough analysis is available at:</p>
<p><a href="http://t2.unl.edu/gratia/wlcg_reporting">http://t2.unl.edu/gratia/wlcg_reporting</a></p>
<p>Thank you for your consideration,<br/>
OSG Metrics and Measurements
</p>
"""

html_table_css = """
<style type="text/css">
table.mytable{
	border-width: 1px 1px 1px 1px;
	border-spacing: 2px;
	border-style: outset outset outset outset;
	border-collapse: collapse;
	background-color: white;
}
table.mytable th {
	border-width: 1px 1px 1px 1px;
	padding: 1px 1px 1px 1px;
	border-style: inset inset inset inset;
	background-color: white;
        font-weight: normal;
}
table.mytable td {
	border-width: 1px 1px 1px 1px;
	padding: 1px 1px 1px 1px;
	border-style: inset inset inset inset;
	background-color: white;
        text-align: right;
}
</style>
"""

html_table = html_table_css + """
<table class="mytable">
<thead><th>WLCG Accounting Name</th><th>%(pledge_year)s KSI2K Pledge</th><th>Month goal of KSI2K-hours</th><th>KSI2K-hours for owner VO</th><th>KSI2K-hours for WLCG VOs</th><th>KSI2K-hours for all VOs</th><th>Percent of WLCG goal achieved</th><th>Percent of site's time given to non-WLCG VOs</th></thead>
%s
</table>
"""

table_headers = ['WLCG\nAccounting\nName', '%(pledge_year)s KSI2K\nPledge', 'Month goal\nof Norm.\nCPU hours', \
    'Norm. CPU\nHours for\nowner VO', 'Norm. CPU\nHours for all\nWLCG VOs', 'Norm. CPU\nHours for\nall VOs', \
    'Percent of\nWLCG goal\nachieved', 'Percent of site\'s\ntime given to\nnon-WLCG VOs']

plain_table = """
-------------------------------------------------------------------------------------------------------
|    Site Name    | Pledge |  KSI2K |    Owner    |     WLCG    |    Total    | %% of WLCG | %% of work |
|                 |        |   Goal | KSI2K-hours | KSI2K-hours | KSI2K-hours |    Goal   | non-WLCG  |
-------------------------------------------------------------------------------------------------------
%s-------------------------------------------------------------------------------------------------------

"""

html_table_row = """
<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>
"""

plain_table_row = \
"""| %15s | %6s | %6s | %11s | %11s | %11s | %9s | %9s |
"""

def load_pledges(month, cp):
    url = cp.get("info", "url")
    data = urllib.urlencode({'month': month})
    fp = urllib2.urlopen(url, data)
    return eval(fp.read(), {}, {})

def to_str(cp):
    toNames = cp.get("email", "toNames")
    toStr = cp.get("email", "toStr")
    toNames = eval(toNames, {}, {})
    toStr = eval(toStr, {}, {})
    if len(toNames) > 1 and cp.getboolean("info", "dev"):
        raise Exception("Cannot send to multiple recipients in dev mode.")
    names = [formataddr(i) for i in zip(toNames, toStr)]
    return ', '.join(names)

def send_email(msg, cp):
    toStr = cp.get("email", "toStr")
    toStr = eval(toStr, {}, {})
    if isinstance(toStr, types.StringType):
        toStr = [toStr]
    fromStr = cp.get("email", "fromStr")
    smtp = smtplib.SMTP()
    smtp.connect()
    #print "Sending email to %s from %s." % (toStr, fromStr)
    #print msg
    smtp.sendmail(fromStr, toStr, msg)
    smtp.quit()

def main():
    now = datetime.datetime.now()
    cp = loadConfig()
    year = now.year
    month = now.month
    if cp.getboolean("info", "lastmonth"):
        month -= 1
    #Bug fix - on the first day of the month, we're actually reporting the
    # previous month's usage.
    if now.day == 1 and not cp.getboolean("info", "lastmonth"):
        month_str = calendar.month_name[month-1]
    else:
        month_str = calendar.month_name[month]
    pledges = load_pledges(month, cp)
    wlcg_sites = []
    for site in pledges['apel_data']:
        if site['ExecutingSite'] not in wlcg_sites:
            wlcg_sites.append(site['ExecutingSite'])

    if year >= 2008 and month >= 4:
        pledge_year = '2008'
    else:
        pledge_year = '2007'

    t = Table()
    table_headers[1] = table_headers[1] % {'pledge_year': pledge_year}
    t.setHeaders(table_headers)
    for site, data in pledges['pledges']['atlas'].items():
        pledge = int(data['pledge'])
        goal = int(data['efficiency'] * pledge * data['days_in_month'] * 24)
        vo = data['voNormCPU']
        wlcg = data['wlcgNormCPU']
        total = data['totalNormCPU']
        wlcg_perc = '%i%%' % int(wlcg/float(goal)*100)
        other_perc = '%i%%' % int((total-wlcg)/float(total)*100)
        t.addRow([site, pledge, goal, vo, wlcg, total, wlcg_perc, other_perc])
    atlas_html_table = html_table_css + t.html()
    atlas_plain_table = t.plainText()

    html_strng = ''
    plain_strng = ''
    t = Table()
    t.setHeaders(table_headers)
    for site, data in pledges['pledges']['cms'].items():
        pledge = int(data['pledge'])
        goal = int(data['efficiency'] * pledge * data['days_in_month'] * 24)
        vo = data['voNormCPU']
        wlcg = data['wlcgNormCPU']
        total = data['totalNormCPU']
        wlcg_perc = '%i%%' % int(wlcg/float(goal)*100)
        other_perc = '%i%%' % int((total-wlcg)/float(total)*100)
        t.addRow([site, pledge, goal, vo, wlcg, total, wlcg_perc, other_perc])
    cms_html_table = html_table_css + t.html()
    cms_plain_table = t.plainText()

    if cp.getboolean("info", "lastmonth"):
        report_time = "the end of the month"
    else:
        report_time = pledge
    email_info = {'atlas_html_table': atlas_html_table, 'cms_html_table': \
        cms_html_table, "report_time": report_time, "year": year, "month": \
        month_str, "atlas_plain_table": atlas_plain_table, "cms_plain_table": \
        cms_plain_table, "pledge_year": pledge_year}

    fromName = cp.get("email", "fromName")
    fromStr = cp.get("email", "fromStr")
    fromHeader = '"%s" <%s>' % (fromName, fromStr)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject % (month_str, year)
    msg['From'] = fromHeader
    msg['To'] = to_str(cp)
    msgText = MIMEText(email_plain % email_info)
    msgHtml = MIMEText(email_html % email_info, "html")
    msg.attach(msgText)
    msg.attach(msgHtml)
    send_email(msg.as_string(), cp)

if __name__ == '__main__':
    main()

