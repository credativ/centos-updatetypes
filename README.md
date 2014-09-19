# centos-updatetypes

This script will compare a given list of installed rpm files with the update information of CentOS/EPEL yum metadata repositories and list packages with security or bugfix updates.

The idea is to check CentOS offline servers if relevant bugfixes or security updates are available.

## Usage

First, generate the list of rpm files on your CentOS machine:

    rpm -qa > filelist.txt

Afterwards, check this script against given Update-Repositories. In the following example we check a file list against the EPEL repository to see if an EPEL security update is available:

    $ ./centos-find-updates.py -s -r filelist.txt -x http://tesla/epel/6/x86_64
    djvulibre

There are various options for the script, more details can be seen with:

    ./centos-find-updates.py --help

## Requirements

The script needs an installed python, wget and gunzip.

Beware that for CentOS repositories you need to have your own mirror with added security information. See for example http://blog.vmfarms.com/2013/12/inject-little-security-in-to-your.html for more information.
