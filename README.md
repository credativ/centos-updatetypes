centos-updatetypes
==================

this script will compare a given rpm-list to a repositories xml'file and list packages with possible updates.

usage: centos-find-updates.py [-h] -r RPMFILE -x XMLFILE [-b] [-s] [-v] [-u]

This script parses a given XML-File with packgeupdate information and a list of installed rpm's on CentOS.
 It then seeks updates for installed rpm's in the XML and prints those to stdout.

optional arguments:
  -h, --help            show this help message and exit
  -r RPMFILE, --rpm RPMFILE
                        Path to 'installed-rpm'-list.
                        This file is returned when you run 'rpm -qa > filename'
  -x XMLFILE, --xml XMLFILE
                        Path to XML-UpdatelistFile or a repositories HTTP-URL.
                        XML-Files are obtained from sites like cefs.steve-meier.de. 
                        URL-Example http://your.domain.here/centos/6/updates/x86_64/ 
  -b, --bugs            List Bugfixes
  -s, --security        Ignore Security Updates
  -v                    Show extra messages
  -u                    Upgrades to higher releaseversions only
