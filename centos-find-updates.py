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


########IMPORTS###########################
from argparse import ArgumentParser , RawTextHelpFormatter
import lxml.etree as ET
from lxml import objectify
import os


########CLASSES AND FUNCTIONS###########################
class rpmObject:
	def __init__(self,name, version, subversion, arch, typ = "existing"):
		self.name = name
		self.version = version
		self.subversion = subversion
		self.arch = arch
		self.typ = typ


	def show(self):
		print self.name,"in version", self.version, self.subversion, "on arch",self.arch

	def equals(self, foreign):
		# Splitted up in many if's for readability's sake.
		if (self.name == foreign.name and
			self.version == foreign.version and
				((self.arch == foreign.arch)or(foreign.arch=="noarch")) ):
					return True
		return False

def default_cutter(line, typ, arch=None, rpmending = True):
	packagename = line.rsplit("-", 2)
	if len(packagename) < 3:
		return None
	subversion_arch_rpm =  packagename[-1]
	version = packagename[-2]
	name = packagename[-3]
	if rpmending:
		(subversion, arch, rpm) = subversion_arch_rpm.rsplit(".",2)
	elif arch==None:
		(subversion, arch) = subversion_arch_rpm.rsplit(".",1)
	else:
		subversion = subversion_arch_rpm

	return rpmObject(name, version, subversion, arch, typ)

def epel_cutter(line, typ, arch=None):
	pass #see epel-parsetree
	
	
	
def subversion_a_is_bigger(first, second):
	# "12.el3.342" is exampleinput
	#
	# Basically split it up by dots.
	# The one with a lower number is smaller
	# OR 
	# The one with a lower lexicographic value is smaller
	# OR
	# The one first reaching el is smaller
	#  >Magic
	firstlist = first.split(".")
	secondlist = second.split(".")

	for i in range(len(firstlist)):
		try:
			a = firstlist[i]
			b = secondlist[i]
		except:#one seems to be bigger. Yay
			if len(a)> len(b):
				return True
			elif len(a) < len(b):
				return False
		if a.find("el")!=-1 and b.find("el")==-1:

			return False
		elif a.find("el")==1 and b.find("el")!=1:

			return True
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


def buildlists(xml, rpm, VERBOSE = False, BUGS = False, SECURITY = True):
	########INIT THE MAIN LISTS###########################
	XML_LIST = []
	RPM_LIST = []



	# _________      _______
	#|RPM-List |____/CUTTER/_____
	#|P_A_R_S_E|   /______/     _|___
	#                          |MERGE|___print Result
	# __________    _______    |VUPS_|
	#|Update-XML|__/CUTTER/_____|
	#|P_A_R_S_E_| /______/
	#
	#
	######## PROCESSING ###########################
	#Fetch all RPM's from inputfile.

	if VERBOSE:
		print "----Parsing RPM:-File"

	skipped =0
	try:
		f = open(rpm, 'r')
		for line in f:
				cuttedObject = default_cutter(line.strip(), "existing", rpmending=False)
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

		####################vvv Document specific magic ahead vvv##############################
		if root.tag == "opt": # most likely the steve-meier list. Parse it.
			if VERBOSE:
				print "'opt' is root. Should be a steve-meier list"
			for modules in root:
					if (modules.tag == "meta"):
						skipped = skipped + 1
						continue
					if ( 
						   ((modules.attrib["type"].find("Bug")!=-1 ) and (BUGS)     )
						 or((modules.attrib["type"].find("Security")!=-1 ) and (SECURITY) ) ):
						for packages in modules:
							if (packages.tag == "packages"):
								val = default_cutter(packages.text, modules.attrib["type"])
								if val:
									XML_LIST.append(val)
								else:
									skipped = skipped + 1
									
									
									
		####################vvv Document specific magic ahead vvv##########################
		elif root.tag == "updates": #most likely epel-update list. Parse it.
			if VERBOSE:
				print "'updates' is root. Should be an epel or repo list"
			for update in root:
				if ( (update.attrib["type"].find("bugfix") != -1 and BUGS ) or
					 (update.attrib["type"].find("security") != -1 and SECURITY) ):
						 for package in update.find("pkglist").find("collection"):
							 if package.tag == "package":
								#here could be a cutter, but epel-files dont require cutting.
								a =  rpmObject(package.attrib["name"], package.attrib["version"],package.attrib["release"],package.attrib["arch"],update.attrib["type"])
								XML_LIST.append(a)
								
		####################vvv Document specific magic ahead vvv##########################
		else:
			print "Could not parse the given xml-file.\n Exiting"
			
	except Exception as e:
		print "Could not parse",xml,".", e
		exit(1)
		
	if VERBOSE:
		print "Found",len(XML_LIST),"Updates."
		if skipped:
			print "Could not read", skipped,"lines\n----"

	return XML_LIST, RPM_LIST
	
def merge(XML_LIST, RPM_LIST, VERBOSE = False, UPONLY = False):
	#O(n*m) solution ahead. Think about sorted-lists or a proper search for speed-up.
	validupdates = {} # Dict to avoid double entries
	if VERBOSE:
		print "----Comparing matches from List and XML"
	updatesfound = 0
	updatesseemlower = 0
	for update in XML_LIST:
		for existing_rpm in RPM_LIST:
			if update.equals(existing_rpm):
				updatesfound += 1
				sign = "+"
				if subversion_a_is_bigger(existing_rpm.subversion,update.subversion ):
							updatesseemlower += 1
							sign = "-"
							if UPONLY:
								continue
				if VERBOSE:					
					print sign,update.typ,"available for", existing_rpm.name, existing_rpm.arch, existing_rpm.version," ", existing_rpm.subversion,  " to ",update.subversion 
				try:
					validupdates[existing_rpm.name] = 1
				except:
					pass
	if VERBOSE:
		print "---- Found",updatesfound,"Updates for the given RPM-List."
		print "----",updatesseemlower,"seem to be of a lower release"
	return validupdates
	
def pullFromWeb(url, VERBOSE):
	# As we support repositories as xmlfile-origins the given url should
	# provide a 'repodata' subfolder.
	# Within this folder, a 'repomd.xml' should point to the correct xml.
	# pull <url>/repodata/repomd.xml
	# obtain link to update-xml from repomd.xml
	# pull this file and return it's location for further use
	nonoise = ""
	if not VERBOSE:
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
	xmlfile = args.xmlfile
	rpmfile = args.rpmfile
	try:
		if xmlfile.find("http")!= -1:
			xmlfile = pullFromWeb(xmlfile, args.verbose)
		(xmllist, rpmlist) = buildlists(xmlfile, rpmfile, args.verbose, args.bugs, args.security)
		validupdates = merge(xmllist, rpmlist, args.verbose, args.uponly)
		for validupdate in validupdates:
			print validupdate
	except Exception as e:
			import traceback
			traceback.print_exc()
		
if __name__ == "__main__":
	parser=ArgumentParser(
		description='This script parses a given XML-File with packgeupdate information and a list of installed rpm\'s on CentOS.\n It then seeks updates for installed rpm\'s in the XML and prints those to stdout.',
		 epilog="",formatter_class=RawTextHelpFormatter)
	parser.add_argument("-r", "--rpm", dest="rpmfile", required = True,
					  help="Path to 'installed-rpm'-list.\nThis file is returned when you run 'rpm -qa > filename'")
					  
	parser.add_argument("-x", "--xml", dest="xmlfile",required = True,
					  help="Path to XML-UpdatelistFile or a repositories HTTP-URL.\nXML-Files are obtained from sites like cefs.steve-meier.de. \nURL-Example http://your.domain.here/centos/6/updates/x86_64/ ")
					  
	parser.add_argument("-b", "--bugs",
					  action="store_true", dest="bugs", default=False,
					  help="List Bugfixes")

	parser.add_argument("-s", "--security",
					  action="store_false", dest="security", default=True,
					  help="Ignore Security Updates")
					  
	parser.add_argument("-v", action="store_true", dest="verbose", default=False,
					  help="show extra messages")
	 
	parser.add_argument("-u", action="store_true", dest="uponly", default=False,
					  help="Upgrades to highter releaseversions onls") 

	args = parser.parse_args()

	main(args)
