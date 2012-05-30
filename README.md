launchpad
===========

A django based system that provides a stable URL for every item in the libraries catalog. Various discovery services will link to these URLs. The page for each item will in turn link out to various other resources that provide methods for accessing the content of the items.

Installation Instructions
---------------------------
This software should be runnable on any kind of operating system. However, these installation instructions are tailored to a Linux server, and have only been tested on ubuntu 10.04 LTS.

**Part I - Basic server requirements**

1. Install Apache if not already installed. Also install the WSGI module if not already installed

        sudo apt-get install apache2

        sudo apt-get install libapache2-mod-wsgi

2. Install git if not already installed

    Follow the excellent instructions found on the [github website](http://help.github.com/linux-set-up-git/)

3. Install MySQL and build dependency libraries for Python

        sudo apt-get install mysql-server libmysqlclient-dev

    Create root account when prompted

- - -

**Part II - Setting up the project environment**

4. Install virtualenv

        sudo apt-get install python-setuptools

        sudo easy_install virtualenv

5. Create directory for your projects (replace <user> with your user name)

        mkdir /home/<user>/Projects/

        cd /home/<user>/Projects/

6. Pull down the project from github

        git clone git@github.com:gwu-libraries/idservice.git

7. Create virtual Python environment for the project

        cd /home/<user>/Projects/idservice

        virtualenv --no-site-packages ENV

8. Activate your virtual environment

	source ENV/bin/activate

9. Download Instant Client for Linux x86-64 or the platform that matches your system from http://www.oracle.com/technetwork/topics/linuxx86-64soft-092277.html
	
	download intant-client-basic, instant-client-develop and instant-client-sqlplus
	
10. Install alien in order to install the RPM packages on Debian or ubuntu Linux Distributions. This is not required if you are using RedHat or similar distribution.
	
	sudo apt-get install alien

11. Install all three download packages of oracle using the following commands (for Debian and Ubuntu distros). For RedHat and similar Distros use rpm -ivh packagename command.
	
	sudo alien --install oracle-instantclient11.2-basic-11.2.0.3.0-1.x86_64.rpm
	sudo alien --install oracle-instantclient11.2-devel-11.2.0.3.0-1.x86_64.rpm
	sudo alien --install oracle-instantclient11.2-sqlplus-11.2.0.3.0-1.x86_64.rpm

12. Setup ORACLE_HOME and LD_LIBRARY_PATH environment variables. Change the path according to your installation of oracle.
	
	export ORACLE_HOME=/usr/lib/oracle/11.2/client64/
	export LD_LIBRARY_PATH=/usr/lib/oracle/11.2/client64/lib

13. Install django, mysqldb and cx_Oracle

        pip install -r requirements.txt


- - -

**Part III - Configuring your installation**

14. Edit wsgi file

        mv /home/<user/Projects/launchpad/lp/lp/wsgi.py.template /home/<user/Projects/launchpad/lp/lp/wsgi.py
        vim /home/<user/Projects/idservice/lids/lids/wsgi.py

    Change parameter for site.addsitedir() to your local path. You will need to change the user name and possibly the Python version number.

15. Edit Apache config file

        vim /home/<user>/Projects/launchpad/apache/ld

    Change the values of the server, user, and python version in the document

16. Add apache config file to sites-enabled and enable it

        sudo mv /home/<user>/Projects/launchpad/apache/ld /etc/apache2/sites-enabled/ld

        sudo a2ensite ld

        sudo /etc/init.d/apache2 restart

17. Configure database and other settings in a local_settings file

        cd ld/ld

        mv local_settings.py.template local_settings.py

        vim local_settings.py

    Change database login and password and any other parameters you wish to change.



