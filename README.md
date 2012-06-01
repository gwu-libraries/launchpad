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

        sudo apt-get install apache2 libapache2-mod-wsgi libaio-dev

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

2. Create directory for your projects (replace <user> with your user name)

        mkdir /home/<user>/Projects/
        cd /home/<user>/Projects/

3. Pull down the project from github

        git clone git@github.com:gwu-libraries/launchpad.git

4. Create virtual Python environment for the project

        cd /home/<user>/Projects/launchpad
        virtualenv --no-site-packages ENV

5. Activate your virtual environment

        source ENV/bin/activate

10. Install django, cx_Oracle, and other python dependencies

        pip install -r requirements.txt


- - -

**Part III - Configuring your installation**

1. Edit wsgi file

        mv /home/<user/Projects/launchpad/lp/lp/wsgi.py.template /home/<user/Projects/launchpad/lp/lp/wsgi.py
        vim /home/<user/Projects/launchpad/lp/lp/wsgi.py

	Change parameter for site.addsitedir() to your local path. You
	will need to change the user name and possibly the Python
	version number.

2. Edit Apache config file

        vim /home/<user>/Projects/launchpad/apache/lp

	Change the values of the server, user, and python version in
	the document

3. Add apache config file to sites-enabled and enable it

        sudo mv /home/<user>/Projects/launchpad/apache/lp /etc/apache2/sites-enabled/lp
        sudo a2ensite lp
        sudo /etc/init.d/apache2 restart

4. Configure database and other settings in a local_settings file

        cd lp/lp
        mv local_settings.py.template local_settings.py
        vim local_settings.py

	Change database login and password and any other parameters you
	wish to change.



