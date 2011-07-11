Name: InstalledCapacityReport          
Version: 1.0        
Release: 1
Summary: Installed Capacity Report        

Source: InstalledCapacityReport.tar      
Group: Development/System          
License: GPL        
URL: http://osgbdiifilter.svn.sourceforge.net/viewvc/osgbdiifilter/pledgedCapacity/ 

BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}
BuildArch: noarch

%description
WLCG OIM Installed Capacity Report RPMs

%install
rm -rf $RPM_BUILD_ROOT
tar -xvf $RPM_SOURCE_DIR/InstalledCapacityReport.tar
mkdir -p $RPM_BUILD_ROOT/%{_usr}/local/
cp -rf InstalledCapacityReport $RPM_BUILD_ROOT%{_usr}/local/
mkdir -p $RPM_BUILD_ROOT%{_usr}/local/InstalledCapacityReport/log

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%{_usr}/local/InstalledCapacityReport/bin/*
%{_usr}/local/InstalledCapacityReport/etc/config.ini
%dir %{_usr}/local/InstalledCapacityReport/log
%doc

%config
%{_usr}/local/InstalledCapacityReport/etc/config.ini



%post
echo "--------------------------------------------------------"
echo "   %{name} Installed Capacity Report Installed in %{_usr}/local/InstalledCapacityReport"
echo "   %{name} Please do the following:"
echo "   1) Configure email in %{_usr}/local/InstalledCapacityReport/etc/config.ini"    
echo "   2) make cron entry to run the report as %{_usr}/local/InstalledCapacityReport/bin/report.py --email"    
echo "--------------------------------------------------------"

%changelog
* Thu Jul 7 2011  Ashu Guru <aguru2@unl.edu> 1.01
- Initial version of the package

