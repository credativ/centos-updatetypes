#!/usr/bin/env python

# The MIT License (MIT)
# Copyright (c)2014 Julian Schauder <julian.schauder@credativ.de>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from argparse import ArgumentParser , RawTextHelpFormatter
import lxml.etree as ET
import os


class rpmObject:
	# an rpmObject is a package from the RPM-List AND from the xml-lists.
	# for instance the string 'glibc-2.12-1.47.el6.x86_64' 
	# provides name, version, subversion(release) and arch.
	# type is pulled from xml-context
	# origin is purely cosmetic for verbose-mode.

	def __init__(self,name, version, subversion, arch, typ = "existing", orig="unknown"):
		# this constructor takes multiple variables instead of one string, as
		# there are different formats that would require multiple constructors.
		# 
		
		self.name = name
		self.version = version
		self.subversion = subversion
		self.arch = arch
		self.typ = typ
		self.orig = orig

	def show(self):
		# print this object to stdout
		print "[",self.orig,"]",self.name,"in version", self.version, self.subversion, "on arch",self.arch

	def equals(self, foreign):
		# 'equals' compares the major components and tests for compability
		# package1 equals package2 if they are updates of each other.
		# name, versio and arch need to fit. subversion(release) doesnt need to. 
		
		if (self.name == foreign.name and
			#self.version == foreign.version and  # commenting this allows major-updates to happen.
				((self.arch == foreign.arch)or(foreign.arch=="noarch")) ):
					return True
		return False

# Cutters take strings and cut them into smaller stringpackages.
# They're used to provide the rpmObject-class with the required options.

def default_cutter(line, typ, arch=None, rpmending = True):
	# this cutter parses lines that are delivered by rpm -qa.
	# ex glibc-2.12-1.47.el6.x86_64
	
	# cut by "-". Start right. 2Cuts - so 3 packages
	# ["glibc","2.12","1.47.el6.x86_64"]
	
	packagename = line.rsplit("-", 2)
	if len(packagename) < 3: # if there are less packages than 3, die.
		return None
		
	# give proper names to the packages. Start at the back.
	subversion_arch_rpm =  packagename[-1]
	version = packagename[-2]
	name = packagename[-3]
	
	# Last Package MAY have rpm or arch ending.
	# 1.47.el6
	# 1.47.el6.x86_64
	# 1.47.el6.x86_64.rpm
	
	# Cut by dots, start right. Expect 1 to 3 packages
	if rpmending:
		(subversion, arch, rpm) = subversion_arch_rpm.rsplit(".",2)
	elif arch==None:
		(subversion, arch) = subversion_arch_rpm.rsplit(".",1)
	else:
		subversion = subversion_arch_rpm
		
	# Build object and return.
	return rpmObject(name, version, subversion, arch, typ)

def epel_cutter(line, typ, arch=None):
	pass #see epel-parsetree tl;dr; epel-xml's dont require cutting as the xml is well made.
	
#def majorversion_a_is_bigger(first, second):
	
def version_a_is_bigger(first, second):
	# Compare the version(release)
	
	# Two versionstrings are supplied.
	# First, cut the supplied strings.
	# cut by dots.
	
	firstlist = first.split(".")
	secondlist = second.split(".")
	
	# Subversions are a little fuzzy to compare.
	for i in range(len(firstlist)):
		# Run through all those packages.
		# TRY to grab the current element.
		# As the arrays do not need to be of the same size, expect an error.
		# If there is an error, one version is obviously shorter.
		
		# 1.47.123.el6.x86_64 for instance is a bigger version than
		# 1.47.el6.x86_64
		# The 'longer' Version will win.
		try:
			a = firstlist[i]
			b = secondlist[i]
		except:
			if len(a)> len(b):
				return True
			elif len(a) < len(b):
				return False
		# "EL" (enterprise linux i assume?) shows up before arch.
		# Whoever reached EL first, is obviously shorter
		# 'longer' Version wins again.
		if a.find("el")!=-1 and b.find("el")==-1:
			return False
		elif a.find("el")==1 and b.find("el")!=1:
			return True
		
		# Vor every package of numbers, try to compare on a numerical level.
		# This MAY fail, if someone puts in a version like 1A.34
		# TRY the numerical approach.
		# If it fails -> lexicographic.
		try:
			if int(a) > int(b):
				return True
			elif int(a) < int(b):
				return False
		except:
			if a > b:
				return True
			elif a < b:
				return False
	# If everything fails, we cant say the version is bigger.
	return False
				
def buildrpmlist(rpm, VERBOSE = False):
	# Fetch all RPM's from inputfile.
	# Open file and line-by-line cut the strings to objects.
	# Return list of objects at the end.
	
	RPM_LIST = []
	if VERBOSE:
		print "----Parsing RPM:-File"

	skipped=0 # for verbose
	try:
		f = open(rpm, 'r')
		for line in f:
				try: # There are (mini) packages within the packagelist that 
					# dont follow the convention. Just be sure, try-catch it.
					cuttedObject = default_cutter(line.strip(), "existing", rpmending=False)
				except:
					pass
				if cuttedObject != None:
					RPM_LIST.append(cuttedObject)
				else:
					skipped = skipped + 1;
	except Exception as e:
		print "Could not parse",rpm,".", e
		exit(1)						
	if VERBOSE:
		print "Found",len(RPM_LIST),"Packages."
		if skipped:
			print "Could not read", skipped,"lines"
		print "----\n"
	return RPM_LIST

def buildlist(xml, RPM_LIST, VERBOSE = False, BUGS = False, SECURITY = True, identifier = "unknown", ALL = False):
	XML_LIST = []

	#XML-parser

	# Update XML's dont share a common structure.
	# Determine what structure it is by it's root-node and
	# fill the list accordingly.

	if VERBOSE:
		print "----Parsing XML-File"
	skipped =0
	try:
		
		
		tree = ET.parse(xml)
		root = tree.getroot()

		if VERBOSE:
			print "Detecting XML-Format"

		####################vvv Document specific parser ahead vvv##############################
		if root.tag == "opt": # most likely the steve-meier list. Parse it.
			if VERBOSE:
				print "'opt' is root. Should be a steve-meier list"
			for modules in root:
					if (modules.tag == "meta"):
						skipped = skipped + 1
						continue
					if ( ALL or
						   ((modules.attrib["type"].find("Bug")!=-1 ) and (BUGS)     )
						 or((modules.attrib["type"].find("Security")!=-1 ) and (SECURITY) ) ):
						for packages in modules:
							if (packages.tag == "packages"):
								val = default_cutter(packages.text, modules.attrib["type"])
								if val:
									XML_LIST.append(val)
								else:
									skipped = skipped + 1
									
									
									
		####################vvv Document specific parser ahead vvv##########################
		elif root.tag == "updates": #most likely epel-update list. Parse it.
			if VERBOSE:
				print "'updates' is root. Should be an epel or repo list"
			for update in root:
				if   (ALL or 
					 (update.attrib["type"].find("bugfix") != -1 and BUGS ) or
					 (update.attrib["type"].find("security") != -1 and SECURITY) ):
						 for package in update.find("pkglist").find("collection"):
							 if package.tag == "package":
								#here could be a cutter, but epel-files dont require cutting.
								a =  rpmObject(package.attrib["name"], package.attrib["version"],package.attrib["release"],package.attrib["arch"],update.attrib["type"], identifier)
								XML_LIST.append(a)
								
		else:
			print "Could not parse the given xml-file.\n Exiting"
			
	except Exception as e:
		print "Could not parse",xml,".", e
		exit(1)
		
	if VERBOSE:
		print "Found",len(XML_LIST),"Updates."
		if skipped:
			print "Could not read", skipped,"lines\n----"

	return XML_LIST
	
def merge(XML_LIST_LIST, RPM_LIST, VERBOSE = False,UPONLY = False):
	# this function "merges" xml and rpm object-lists.
	# compare both lists. If any object 'equals' the other, it could be an update.
	# compare subversions to filter 'upgrades' only.
	#
	# O(n*m) solution ahead. Think about sorted-lists or a proper search for speed-up.
	
	# Dictionary to avoid double entries in the final list
	validupdates = {} 
	if VERBOSE:
		print "----Comparing matches from List and XML"
	updatesfound = 0		#verbose
	updatesseemlower = 0	#verbose
	for XML_LIST in XML_LIST_LIST:
		for update in XML_LIST:
			for existing_rpm in RPM_LIST:
				if update.equals(existing_rpm):
					updatesfound += 1
					sign = "+"
					if version_a_is_bigger(existing_rpm.version,update.version ):
						# This is the case when there is a bigger Major-version installed.
						updatesseemlower += 1
						sign = "-"
						if UPONLY:
							continue
					elif version_a_is_bigger(update.version,existing_rpm.version ) :
						# This is the case when there is a bigger Major-version available.
						pass
					elif version_a_is_bigger(existing_rpm.subversion,update.subversion ):
						# This is the case when the major versions are equal.
						# but a bigger subversion is installed. 
						updatesseemlower += 1
						sign = "-"
						if UPONLY:
							continue
					elif ((not version_a_is_bigger(existing_rpm.subversion,update.subversion ))\
					  and( not version_a_is_bigger(update.subversion,existing_rpm.subversion))):
						#Equals - none is biger, even in subversion
						updatesseemlower += 1
						sign = "-"
						if UPONLY:
							continue

						
							
					if VERBOSE:					
						print sign,"[",update.orig,"]",update.typ,"available for", existing_rpm.name, existing_rpm.arch, existing_rpm.version," ", existing_rpm.subversion,  " to ",update.version ,update.subversion 

					validupdates[existing_rpm.name] = 1

					continue;
	if VERBOSE:
		print "---- Found",updatesfound,"Updates for the given RPM-List, distributed to", len(XML_LIST_LIST), "Files"
		print "----",updatesseemlower,"seem to be of a lower release"
		print "----",updatesfound - len(validupdates)," didnt make it to the resultlist"
		print "---- ( double entries? )"
	return validupdates
	
def pullFromWeb(url, VERBOSE=False , VERYVERBOSE = False ):
	# As we support repositories as xmlfile-origins the given url should
	# provide a 'repodata' subfolder.
	# Within this folder, a 'repomd.xml' should point to the correct xml.

	# Task:
	# pull <url>/repodata/repomd.xml
	# obtain link to update-xml from repomd.xml
	# (checksums are added infront of the filename by default, so we need to seek the
	#  update.xml's >real< name witin repomd.xml prior to loading it.
	# pull this file and return it's location for further use

	nonoise = ""
	if not VERYVERBOSE:
		nonoise = "  >/dev/null 2>&1"
	pullmechanism = "wget"
	target =  "%s/repodata/repomd.xml"%(url)
	dropoff = "updateinfo.xml"
	if os.system( "%s %s -O %s %s"%(pullmechanism, target, dropoff, nonoise) )!= 0:
		raise Exception("Error using wget. Destionation %s"%(target) )
	updatefile = ""
	
	rootname = ""
	filetofind= "updateinfo"
	
	tree = ET.parse(dropoff)
	root = tree.getroot()
	
	# fun fact about xml-namespaces in python - they're hardcoded to the tag.
	namespace = ""
	
	try:
		namespace = root.tag[:root.tag.find("}")+1]
	except:
		pass

	for elem in root:
		if elem.tag == "%s%s"%(namespace,"data"): #  surely it's a 'data'node
			if elem.attrib['type'] == filetofind:
				#print "location", elem.tag
				dest = elem.find("%slocation"%namespace)
				updatefile = "%s/%s"%(url, dest.attrib["href"])
	# updatefile located on the foreign host.
	# Lets pull it
	dropoff = "%s%s"%(filetofind , ".xml.gz")
	if os.system( "%s %s -O %s %s"%(pullmechanism, updatefile, dropoff, nonoise ) )!= 0:
		raise Exception("Error using wget. Destionation %s"%(updatefile))
	
	# Remove compression and return location.
	
	if os.system("gunzip -f %s"%(dropoff) ) != 0:
		raise Exception("error using gunzip")
		
	dropoff = dropoff[:-3] # new file most likely lacks .gz
	
	return dropoff

def main(args):
	# 1. Obtain RPM-List and build rpmObject-List
	# 2. For all XML'files, build rpmObject-Lists
	# 3. Test all XML-Lists against the RPM-List
	# 4. Print the matches.
	rpmfile = args.rpmfile
	rpmlist = buildrpmlist(rpmfile)
	
	XML_LIST_LIST = []
	
	xmlfileidentifier = 0 # this id supplies verbose-mode with an origin-id of the update.
	for xmlfile in args.xmlfiles:
		xmlfileidentifier +=1
		if xmlfile.find("http")!= -1:
			xmlfile = pullFromWeb(xmlfile, args.verbose, args.veryverbose)
		XML_LIST_LIST.append ( buildlist(xmlfile, rpmlist, args.verbose, args.bugs, args.security, xmlfileidentifier, args.All) )
	if args.verbose:
		for XML_LIST in XML_LIST_LIST:
			for item in XML_LIST:
				item.show()
	validupdates = merge(XML_LIST_LIST, rpmlist, args.verbose, args.uponly)
	for validupdate in validupdates:
		print validupdate
	if args.verbose:
		print "\n",len(validupdates), " items returned"
	
def constructArgParser():
	parser=ArgumentParser(
		description='This script parses a given XML-File with packgeupdate\n information and a list of installed rpm\'s on CentOS.\n It then seeks updates for installed rpm\'s in the XML and prints those to stdout.',
		 epilog="",formatter_class=RawTextHelpFormatter)
	parser.add_argument("-r", "--rpm", dest="rpmfile", required = True,
					  help="Path to 'installed-rpm'-list.\nThis file is returned by 'rpm -qa > filename'")
	parser.add_argument("-x", "--xml", dest="xmlfiles",nargs='+',required = True,
					  help="Path to XML-Updatelistfile or a repositorys HTTP-URL.\nXML-Files are obtained from sites like cefs.steve-meier.de. \nURL-Example http://your.domain.here/centos/6/updates/x86_64/ ")
	parser.add_argument("-b", "--bugs",
					  action="store_true", dest="bugs", default=False,
					  help="List bugfixes aswell")
	parser.add_argument("-s", "--security",
					  action="store_false", dest="security", default=True,
					  help="Ignore securityupdates")
	parser.add_argument("-v", action="store_true", dest="verbose", default=False,
					  help="Show extra messages")
	parser.add_argument("-V", action="store_true", dest="veryverbose", default=False,
					  help="Show extra messages and ncurses-like menues that break direct piping.")
	parser.add_argument("-u", action="store_false", dest="uponly", default=True,
					  help="Show downgrades") 
	parser.add_argument("-a", action="store_true", dest="All", default=False,
					  help="Print all upgrades regardless of type.") 
	args = parser.parse_args()
	return args

if __name__ == "__main__":
	

	main(constructArgParser())
