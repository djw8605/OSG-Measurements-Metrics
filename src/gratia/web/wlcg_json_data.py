import datetime
import json
import urllib2

class WLCGWebUtil:
    def wlcg_pledges(self, month=datetime.datetime.now().month, year=datetime.datetime.now().year):     
            
        thisyear = str(year)
	sites_per_accountname={}
	fednames_and_accounts={}

        cms_fed = {}
        atlas_fed = {}
        alice_fed = {}

        cms_pledge = {}
        atlas_pledge = {}
        alice_pledge = {}

        url = 'http://gstat-wlcg.cern.ch/apps/topology/2/json'
        response  = urllib2.urlopen(url)
	s = response.read()
	x = json.read(s)
	resourcesnestedlist=x['aaData']
	for obj in resourcesnestedlist:
	    if('USA'==obj[0]):
		try:
			sites_per_accountname[obj[3]].append(obj[4])
		except KeyError:
			sites_per_accountname[obj[3]]=[obj[4]]

		fednames_and_accounts[obj[1]]=obj[3]#Name is key
	    if('USA'==obj[0] and obj[1].find('CMS') >= 0):  
		cms_fed[obj[3]]=1;
	    if('USA'==obj[0] and obj[1].find('ATLAS') >= 0):  
		atlas_fed[obj[3]]=1;
	    if('USA'==obj[0] and obj[1].find('ALICE') >= 0):  
		alice_fed[obj[3]]=1;


        url = 'http://gstat-wlcg.cern.ch/apps/pledges/resources/'+thisyear+'/2/json'
        response  = urllib2.urlopen(url)
	s = response.read()
	x = json.read(s)
	resourcesnestedlist=x['aaData']
	for obj in resourcesnestedlist:
	    if('USA'==obj[0] and 'CPU (HEP-SPEC06)' == obj[3]):
		try:
		   int(obj[8]) #atlas number exists
                   atlas_pledge[fednames_and_accounts[obj[1]]] = {'pledge': obj[8], 'site_names': sites_per_accountname[fednames_and_accounts[obj[1]]]}
		except:
		   None

		try:
		   int(obj[12]) #cms number exists
                   cms_pledge[fednames_and_accounts[obj[1]]] = {'pledge': obj[12], 'site_names': sites_per_accountname[fednames_and_accounts[obj[1]]]}
		except:
		   None

		try:
		   int(obj[4]) #alice number exists
                   alice_pledge[fednames_and_accounts[obj[1]]] = {'pledge': obj[4], 'site_names': sites_per_accountname[fednames_and_accounts[obj[1]]]}
		except:
		   None

        return atlas_pledge, cms_pledge, atlas_fed, cms_fed, alice_pledge, alice_fed



#atlas_pledge, cms_pledge,cms_fed,atlas_fed= WLCGWebUtil().wlcg_pledges()
#for key in cms_pledge:
#	print "\n",cms_pledge[key]['pledge']
