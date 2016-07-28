launchpad
=========

[![Build Status](https://secure.travis-ci.org/gwu-libraries/launchpad.png)](http://travis-ci.org/gwu-libraries/launchpad)

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

        sudo apt-get install -y libxml2-dev libxslt1-dev zlib1g-dev
        sudo apt-get install apache2 libapache2-mod-wsgi libaio-dev python-dev python-profiler memcached libmemcached-dev  libxslt-dev


2. Install git 

        sudo apt-get install git

3. Download Oracle Instant Client 11.2.0.3 for Linux
x86-64 or the platform that matches your system from
http://www.oracle.com/technetwork/topics/linuxx86-64soft-092277.html
(accept terms and login to download the files)

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

**Note**: if you have previous versions of these packages installed, you will likely
have to remove them first; updates to the sqlplus client (at least) conflict with
previous installations.

        sudo alien --install oracle-instantclient11.2-basic-11.2.0.3.0-1.x86_64.rpm
        sudo alien --install oracle-instantclient11.2-devel-11.2.0.3.0-1.x86_64.rpm
        sudo alien --install oracle-instantclient11.2-sqlplus-11.2.0.3.0-1.x86_64.rpm

6. Setup ORACLE_HOME and LD_LIBRARY_PATH environment variables. Change
the path according to your installation of oracle.

        export ORACLE_HOME=/usr/lib/oracle/11.2/client64/
        export LD_LIBRARY_PATH=/usr/lib/oracle/11.2/client64/lib

7. Set environment variables in oracle.conf file (create the file if it does not exist)

        sudo vim /etc/ld.so.conf.d/oracle-instantclient11.2-basic.conf

    Add the following lines

        /lib
        /usr/lib/oracle/11.2/client64/lib

    Remove any lines that refer to previous versions of the library.

    Remove any files in /etc/ld.so.conf.d that refer to previous versions 
    of the library

    Now run

        sudo ldconfig  

8. Install postgres and set up USER and PASSWORD to a new Database DB.

        sudo apt-get install postgresql postgresql-contrib
        sudo apt-get install libpq-dev
        sudo postgres createuser --createdb --no-superuser --no-createrole --pwprompt USER
        
        Enter a password for the USER. You will enter this password in a setting file later in the procedures.
  
        sudo -u postgres createdb -O USER DB



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

7. *Note*: Voyager's Oracle implementation *requires* ASCII encoding on
   database connections.  Django strictly mandates UTF8 encodings on 
   connections, so we have to override this by setting ```'NLS_LANG'```
   to ```'.US7ASCII'``` in our ```wsgi.py```, overriding Django's strong
   preference (and that of its community).  See the "Release: All"
   section of the release notes on our project wiki for examples to test.

        https://github.com/gwu-libraries/launchpad/wiki

   See https://code.djangoproject.com/ticket/15313#comment:4 for more
   details and a helpful response by a core Django developer advocating
   this approach over our previous Django-patching madness.
   
   If Oracle throws a access denied or Apache displays permissions error set directory permissions for launchpad/ and subdirectories as required.


- - -

**Part III - Configuring your installation**

Configure database and other settings in a local_settings file:

        cd lp/lp
        cp local_settings.py.template local_settings.py
        vim local_settings.py
 
- Set EMAIL_SUBJECT_PREFIX and SERVER_EMAIL to appropriate values.
- Change database login and password and any other parameters you
  wish to change.
- Define one or more Z39.50 servers if needed under Z3950_SERVERS.
- If you want to use memcache, define CACHES and ITEM_PAGE_CACHE_SECONDS.  
  For development or testing, set ITEM_PAGE_CACHE_SECONDS to something low.
- NOTE: If you are deploying to production, set DEBUG = False.
    Also, set GOOGLE_ANALYTICS_UA to your UA to enable google 
    analytics in production.
- Comment out CACHES if you are not using memcached
- Add 'default' database values as entered while creating POSTGRES Database

Edit wsgi file:

        cp lp/wsgi.py.template lp/wsgi.py
        vim lp/wsgi.py

- Change parameter for site.addsitedir() to your local path. You
  will need to change the path and possibly the Python version number.

If you want to use memcached, configure and ensure it has started:

        sudo vim /etc/memcached.conf
        sudo /etc/init.d/memcached start
        
Run the database migrations command.

        ./manage.py migrate

At this point, you should be able to run the app and view it working,
even without apache configured.  This might be sufficient for dev/test.

        python manage.py runserver 0.0.0.0:8080
        (visit http://your-server:8080/item/198738 to test)
        
- Performing this step will result in a new local file ```PyZ3950_parsetab.py``` 
generated by the Z39.50 support library.  If you follow the next steps to enable
apache integration *without* doing this first, apache might not be able to write
this file, depending on whether you've made changes to permissions, groups, or the
system user apache uses.  It's easy just to do this by hand first. :)

If you want to use apache, add apache config file to sites-enabled and edit it

        sudo cp ../apache/lp /etc/apache2/sites-available/lp.conf
        vim /etc/apache2/sites-available/lp.conf

- Change the values of LPHOME, server, user, and python version
in the document as appropriate.

Enable these apache modules:

        sudo a2enmod expires
        sudo a2enmod headers
        sudo a2enmod proxy
        sudo a2enmod proxy_http

Enable the app in apache and bounce apache2 to start it up

        sudo a2ensite lp
        sudo /etc/init.d/apache2 restart

If you are in production mode, and want to provide sitemaps, set launchpad's
ENABLE_SITEMAPS, SITEMAPS_DIR, and SITEMAPS_BASE_URL in ```local_settings.py```.
Make sure SITEMAPS_DIR exists, then run the management command:

        manage.py make_sitemap

If you are in production mode, be sure to set ```DEBUG = False``` and 
the appropriate ```ALLOWED_HOSTS``` in ```lp/local_settings.py```.
