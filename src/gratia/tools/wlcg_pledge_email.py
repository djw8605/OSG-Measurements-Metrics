#!/usr/bin/env python

import os
import datetime
import calendar
import smtplib
import urllib
import urllib2
from email.MIMEText import MIMEText
from email.MIMEImage import MIMEImage
from email.MIMEMultipart import MIMEMultipart
from email.Utils import formataddr

url = 'http://t2.unl.edu/gratia/pledge_table'

toStr = ['bbockelm@cse.unl.edu']
toNames = ["Brian Bockelman"]
fromStr = 'bbockelm@t2.unl.edu'
subject = "WLCG Pledge data for %s %s"
email_plain = """

Below is the pledge data so far for %(month)s %(year)s.  This data was recorded from the beginning of the month \
until %(report_time)s.

ATLAS Sites

%(atlas_plain_table)s

CMS Sites

%(cms_plain_table)s

For each WLCG accounting site, we show the following information:
   - 2007 KSI2K Pledge
   - Month goal for KSI2K-hours
   - KSI2K-hours for the owning VO
   - KSI2K-hours for all WLCG VOs
   - Site's total KSI2K-hours
   - Percentage of the WLCG goal accomplished
   - Percentage of the site's total time delivered to non-WLCG VOs.

"""

email_html = """

<p>Below is the pledge data so far for <b>%(month)s %(year)s</b>.  This data was recorded from the beginning of the month until %(report_time).</p>

<h2>ATLAS Sites</h2>
%(atlas_html_table)s

<h2>CMS Sites</h2>
%(cms_html_table)s

For each WLCG accounting site, we show the following information:
<ul>
   <li>2007 KSI2K Pledge</li>
   <li>Month goal for KSI2K-hours</li>
   <li>KSI2K-hours for the owning VO</li>
   <li>KSI2K-hours for all WLCG VOs</li>
   <li>Site's total KSI2K-hours</li>
   <li>Percentage of the WLCG goal accomplished</li>
   <li>Percentage of the site's total time delivered to non-WLCG VOs.</li>
</ul>
"""

html_table = """
<table>
<td><th>WLCG Accounting Name</th><th>2007 KSI2K Pledge</th><th>Month goal of KSI2K-hours</th><th>KSI2K-hours for owner VO</th><th>KSI2K-hours for WLCG VOs</th><th>KSI2K-hours for all VOs</th><th>Percent of WLCG goal</th><th>Percent non-WLCG</th><td>
%s
</table>
"""

plain_table = """
-------------------------------------------------------------------------------------------
| Site Name | Pledge  | KSI2K |    Owner    |     WLCG    |    Total    | % of WLCG | % of work |
|           |         |  Goal | KSI2K-hours | KSI2K-hours | KSI2K-hours |    Goal   | non-WLCG  |
-------------------------------------------------------------------------------------------
"""

html_table_row = """
<tr><td>%s</td><td>%i</td><td>%i</td><td>%i</td><td>%i</td><td>%i</td><td>%s</td><td>%s</td></tr>
"""

plain_table_row = \
"""| %9s | %6s | %6i | %11i | %11i | %11i | %8i%% | %8i%% |
-------------------------------------------------------------------------------------------"""

def load_pledges():
    fp = urllib2.urlopen(url)
    return eval(fp.read(), {}, {})

def to_str():
    names = [formataddr(*i) for i in zip(toNames, toStr)]
    return ', '.join(names)

def send_email(msg):
    smtp = smtplib.SMTP()
    smtp.connect()
    smtp.sendmail(fromStr, [toStr], msg)
    smtp.quit()

def main():
    year = datetime.datetime.now().year
    month = datetime.datetime.now().month
    month_str = calendar.month_name[month]

    pledges = load_pledges()
    wlcg_sites = []
    for site in pledges['apel_data']:
        if site['ExecutingSite'] not in wlcg_sites:
            wlcg_sites.append(site['ExecutingSite'])

    html_strng = '' 
    plain_strng = ''
    for site, data in pledges['pledges']['atlas'].items():
        pledge = int(data['pledge07'])
        goal = data['efficiency'] * pledge * data['days_in_month']
        vo = data['voNormWCT']
        wlcg = data['wlcgNormWCT']
        total = data['totalNormWCT']
        wlcg_perc = '%i%%' % int(wlcg/float(vo)*100)
        other_perc = '%i%%' % int((total-wlcg)/float(total)*100)
        html_strng += html_table_row % (site, pledge, goal, vo, wlcg, total, wlcg_perc, other_perc)
        plain_strng += plain_table_row % (site, pledge, goal, vo, wlcg, total, wlcg_perc, other_perc)
    atlas_html_table = html_table % html_strng
    atlas_plain_table = plain_table % plain_strng

    html_strng = ''
    plain_strng = ''
    for site, data in pledges['pledges']['cms'].items():
        pledge = int(data['pledge07'])
        goal = data['efficiency'] * pledge * data['days_in_month']
        vo = data['voNormWCT']
        wlcg = data['wlcgNormWCT']
        total = data['totalNormWCT']
        wlcg_perc = '%i%%' % int(wlcg/float(vo)*100)
        other_perc = '%i%%' % int((total-wlcg)/float(total)*100)
        html_strng += html_table_row % (site, pledge, goal, vo, wlcg, total, wlcg_perc, other_perc)
        plain_strng += plain_table_row % (site, pledge, goal, vo, wlcg, total, wlcg_perc, other_perc)
    cms_html_table = html_table % html_strng
    cms_plain_table = plain_table % plain_strng

    email_info = {'atlas_html_table': atlas_html_table, 'cms_html_table': \
        cms_html_table, "report_time": report_time, "year": year, "month": \
        month_str, "atlas_plain_table": atlas_plain_table, "cms_plain_table": \
        cms_plain_table}

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject % (month_str, year)
    msg['From'] = fromStr
    msg['To'] = to_str()
    msgText = MIMEText(email_plain % email_info)
    msgHtml = MIMEText(email_html % email_info, "html")
    msg.attach(msgText)
    msg.attach(msgHtml)
    send_email(msg.as_string())

if __name__ == '__main__':
    main()

