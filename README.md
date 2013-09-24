launchpad
=========

A django based system that provides a stable URL for every item in the
libraries' catalog.  Various discovery services will link to these
URLs. The page for each item will in turn link out to various other
resources that provide methods for accessing the content of the items.

Installation Instructions
-------------------------

This software should be runnable on any kind of operating system. However,
these installation instructions are tailored to a Linux server, and have
only been tested on ubuntu 10.04 LTS.

**Part I - Basic server requirements**

1. Install Apache and other dependencies:

        sudo apt-get install apache2 libapache2-mod-wsgi libaio-dev python-dev python-profiler memcached libmemcached-dev libxml2-dev libxslt-dev


2. Install git 

        sudo apt-get install git

3. Download Oracle Instant Client 11.2.0.3 for Linux
x86-64 or the platform that matches your system from
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

        (GW staff only)
        git clone git@github.com:gwu-libraries/launchpad.git

        (everyone else)
        git clone https://github.com/gwu-libraries/launchpad.git


4. Create virtual Python environment for the project

        cd /LPHOME/launchpad
        virtualenv --no-site-packages ENV

5. Activate your virtual environment

        source ENV/bin/activate

6. Install django, cx_Oracle, and other python dependencies

        pip install -r requirements.txt
        easy_install pytz

7. Modify django to allow us to connect to Oracle with the required encoding.  In ```ENV/lib/python2.7/site-packages/django/db/backends/oracle/base.py```,
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

        If you want to use memcache, define CACHES and
        ITEM_PAGE_CACHE_SECONDS.  For development or testing, set
        ITEM_PAGE_CACHE_SECONDS to something low.

        NOTE: If you are deploying to production, set DEBUG = False.
        Also, set GOOGLE_ANALYTICS_UA to your UA to enable google 
        analytics in production.

2. Edit wsgi file

        cp lp/wsgi.py.template lp/wsgi.py
        vim lp/wsgi.py

	Change parameter for site.addsitedir() to your local path. You
	will need to change the user name and possibly the Python
	version number.

3. If you want to use memcached, configure and ensure it has started:

        sudo vim /etc/memcached.conf
        sudo /etc/init.d/memcached start

4. At this point, you should be able to run the app and view it working,
even without apache configured.  This might be sufficient for dev/test.

        python manage.py runserver 0.0.0.0:8080
        (visit http://your-server:8080/item/198738 to test)

5. If you want to use apache, add apache config file to sites-enabled and edit it

        sudo cp ../apache/lp /etc/apache2/sites-available/lp
        vim /etc/apache2/sites-available/lp

	Change the values of LPHOME, server, user, and python version
	in the document as appropriate.

6. Enable these apache modules:

        sudo a2enmod expires
        sudo a2enmod headers

7. Enable the app in apache and bounce apache2 to start it up

        sudo a2ensite lp
        sudo /etc/init.d/apache2 restart

8. If you are in production mode, and want to provide sitemaps, set the
ENABLE_SITEMAPS, SITEMAPS_DIR, and SITEMAPS_BASE_URL settings.  Make sure
SITEMAPS_DIR exists, then run the management command:

        manage.py make_sitemap

9. If you are in production mode, be sure to set ```DEBUG = False``` and 
the appropriate ```ALLOWED_HOSTS``` in ```lp/local_settings.py```.
