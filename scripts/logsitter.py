# NOTE: Must be run with sudo (running via supervisor accomplishes this)

import datetime
import time
import subprocess
import select

f = subprocess.Popen(['tail','-F', '-n 0', '/var/log/apache2/error.log'],
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
p = select.poll()
p.register(f.stdout)

while True:
    if p.poll(1):
        logline = f.stdout.readline()
        if 'DatabaseError: ORA-65535: Message 65535 not found;  product=RDBMS; facility=ORA' in logline:
            # Kill the log tailing process; this way, we can start tailing it afresh
            # after the restart.  Avoids multiple restarts associated with a single incident.
            f.kill()
            # Restart apache
            subprocess.call(['echo','Restarting apache at %s' % datetime.datetime.now()])
            subprocess.call(['service','apache2','restart'])
            # Start a new log tailing process
            f = subprocess.Popen(['tail','-F', '-n 0', '/var/log/apache2/error.log'],
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p.register(f.stdout)
    time.sleep(0.5)
