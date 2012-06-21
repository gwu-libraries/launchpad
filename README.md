launchpad
=========

A django based system that provides a stable URL for every item in the
libraries catalog. Various discovery services will link to these URLs. The
page for each item will in turn link out to various other resources that
provide methods for accessing the content of the items.

Installation Instructions
-------------------------

This software should be runnable on any kind of operating system. However,
these installation instructions are tailored to a Linux server, and have
only been tested on ubuntu 10.04 LTS.

**Part I - Basic server requirements**

1. Install Apache and other dependencies:

        sudo apt-get install apache2 libapache2-mod-wsgi libaio-dev python-dev python-profiler

2. Install git 

        sudo apt-get install git-core

3. Download Oracle

    Download Instant Client 11.2.0.3 for Linux x86-64 or
    the platform that matches your system from
    http://www.oracle.com/technetwork/topics/linuxx86-64soft-092277.html

    * instant-client-basic
    * instant-client-devel
    * instant-client-sqlplus

    Or find a copy of the 11.2.0.3.0-1.x86_64 rpms in:

        /vol/backup/dependencies

4. Install alien in order to install the RPM packages on Debian or ubuntu
Linux Distributions. This is not required if you are using RedHat or
similar distribution.

        sudo apt-get install alien

5. Install all three download packages of oracle using the following
commands (for Debian and Ubuntu distros). For RedHat and similar Distros
use rpm -ivh packagename command.

        sudo alien --install oracle-instantclient11.2-basic-11.2.0.3.0-1.x86_64.rpm
        sudo alien --install oracle-instantclient11.2-devel-11.2.0.3.0-1.x86_64.rpm
        sudo alien --install oracle-instantclient11.2-sqlplus-11.2.0.3.0-1.x86_64.rpm

6. Setup ORACLE_HOME and LD_LIBRARY_PATH environment variables. Change
the path according to your installation of oracle.

        export ORACLE_HOME=/usr/lib/oracle/11.2/client64/
        export LD_LIBRARY_PATH=/usr/lib/oracle/11.2/client64/lib

7. Set environment variables in oracle.conf file

        vim /etc/ld.so.conf.d/oracle-instantclient11.2-basic.conf

    Add the following lines

        /lib
        /usr/lib/oracle/11.2/client64/lib

    Now run

        sudo ldconfig        


- - -

**Part II - Setting up the project environment**

1. Install virtualenv

        sudo apt-get install python-setuptools
        sudo easy_install virtualenv

2. Create directory for your projects (replace LPHOME with your root dir)

        mkdir /LPHOME
        cd /LPHOME

3. Pull down the project from github

        git clone git@github.com:gwu-libraries/launchpad.git

4. Create virtual Python environment for the project

        cd /LPHOME/launchpad
        virtualenv --no-site-packages ENV

5. Activate your virtual environment

        source ENV/bin/activate

6. Install django, cx_Oracle, and other python dependencies

        pip install -r requirements.txt

7. Modify django to allow us to connect to Oracle with the required encoding.  In ```ENV/lib/python2.6/site-packages/django/db/backends/oracle/base.py```,
modify line 35 from this:

        ('NLS_LANG', '.UTF8')

    to this:

        ('NLS_LANG', '.US7ASCII')
        
    Note: this is suboptimal.  For an explanation see https://github.com/gwu-libraries/launchpad/issues/22.  Sorry.


- - -

**Part III - Configuring your installation**

1. Configure database and other settings in a local_settings file

        cd lp/lp
        cp local_settings.py.template local_settings.py
        vim local_settings.py

	Change database login and password and any other parameters you
	wish to change.

        Define one or more Z39.50 servers if needed under Z3950_SERVERS.

        NOTE: If you are deploying to production, set DEBUG = False.

2. Edit wsgi file

        cp lp/wsgi.py.template lp/wsgi.py
        vim lp/wsgi.py

	Change parameter for site.addsitedir() to your local path. You
	will need to change the user name and possibly the Python
	version number.

3. Add apache config file to sites-enabled and edit it

        sudo cp ../apache/lp /etc/apache2/sites-available/lp
        vim /etc/apache2/sites-available/lp

	Change the values of the server, user, and python version in
	the document

4. Enable these apache modules:

        sudo a2enmod expires
        sudo a2enmod headers

5. Enable the app in apache and bounch apache2 to start it up

        sudo a2ensite lp
        sudo /etc/init.d/apache2 restart
