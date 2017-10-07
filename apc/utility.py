'''
APC Network PDU Controller

Payton Quackenbush
Modified by Sebastien Celles

Tested with AP7900, but should work with similar models.
'''

import os
import re
import time
import pexpect
from apc.lockfile import FilesystemLock


APC_ESCAPE = '\033'

APC_YES    = 'YES'
APC_LOGOUT = '4'

APC_VERSION_PATTERN = re.compile(' v(\d+\.\d+\.\d+)')

APC_DEFAULT_HOST     = os.environ.get('APC_HOST',     '192.168.1.2')
APC_DEFAULT_USER     = os.environ.get('APC_USER',     'apc')
APC_DEFAULT_PASSWORD = os.environ.get('APC_PASSWORD', 'apc')

LOCK_PATH = '/tmp/apc.lock'
LOCK_TIMEOUT = 60


class APCFactory:
    def build(self, host, user, password, verbose, quiet, cli=''):
        self.quiet = quiet

        self._lock()

        self.info('Connecting to APC @ %s' % host)
        if cli == '':
            commandline = 'telnet %s' % host
        else:
            commandline = cli.format(host=host, user=user, password=password)
        if verbose:
            print("Running '%s'" % commandline)
        child = pexpect.spawn(commandline)

        child.timeout = 10
        child.setecho(True)

        child.expect('User Name : ')
        child.send(user + '\r\n')
        child.before
        child.expect('Password  : ')
        child.send(password + '\r\n')

        child.expect('Communication Established')

        header = child.before

        match = APC_VERSION_PATTERN.search(str(header))

        if not match:
            raise Exception('Could not parse APC version')

        version = match.group(1)

        self.info('Logged in as user %s, version %s'
                  % (user, version))

        if version[0] == '3':
            apc = APC3(host, verbose, quiet)
        else:
            apc = APC2(host, verbose, quiet)

        apc.child = child
        apc.version = version
        apc.apc_lock = self.apc_lock

        return apc

    def _lock(self):
        self.info('Acquiring lock %s' % (LOCK_PATH))

        self.apc_lock = FilesystemLock(LOCK_PATH)

        count = 0
        while not self.apc_lock.lock():
            time.sleep(1)
            count += 1
            if count >= LOCK_TIMEOUT:
                raise SystemError('Cannot acquire %s\n' % (LOCK_PATH))

    def info(self, msg):
        if not self.quiet:
            print(msg)

class AbstractAPC:
    def __init__(self, host, verbose, quiet):
        self.host = host
        self.verbose = verbose
        self.quiet = quiet

    def notify(self, outlet_name, state):
        print('APC %s: %s %s' % (self.host, outlet_name, state))

    def sendnl(self, a):
        self.child.send(a + '\r\n')
        if self.verbose:
            print(self.child.before)

    def get_outlet(self, outlet):
        if str(outlet) in ['*', '+', '9']:
            return (9, 'ALL outlets')
        else:
            # Assume integer outlet
            try:
                outlet = int(outlet)
                return (outlet, 'Outlet #%d' % outlet)

            except:
                raise SystemExit('Bad outlet: [%s]' % outlet)

    def _escape_to_main(self):
        for i in range(6):
            self.child.send(APC_ESCAPE)

    def reboot_immediate(self, outlet):
        (outlet, outlet_name) = self.get_outlet(outlet)

        self.control_outlet(outlet)

        self.sendnl(self.APC_IMMEDIATE_REBOOT)

        self.child.expect('Immediate Reboot')
        self.sendnl(APC_YES)
        self.sendnl('')

        self.get_command_result()

        self.notify(outlet_name, 'Rebooted')

        self._escape_to_main()

    def reboot_delayed(self, outlet, delay):
        raise NotImplementedError()

    def reboot(self, outlet, delay):
        if delay == 0:
            self.reboot_immediate(outlet)
        else:
            self.reboot_delayed(outlet, delay)

    def on_off_immediate(self, outlet, on):
        (outlet, outlet_name) = self.get_outlet(outlet)

        self.control_outlet(outlet)

        if on:
            cmd = self.APC_IMMEDIATE_ON
            str_cmd = 'On'
        else:
            cmd = self.APC_IMMEDIATE_OFF
            str_cmd = 'Off'

        self.sendnl(cmd)
        self.sendnl(APC_YES)
        self.sendnl('')

        self.get_command_result()

        self.notify(outlet_name, str_cmd)

        self._escape_to_main()

    def on_off_delayed(self, outlet, on, delay):
        raise NotImplementedError()

    def on(self, outlet, delay):
        if delay == 0:
            self.on_off_immediate(outlet, True)
        else:
            self.on_off_delayed(outlet, True, delay)

    def off(self, outlet, delay):
        if delay == 0:
            self.on_off_immediate(outlet, False)
        else:
            self.on_off_delayed(outlet, False, delay)

    def debug(self):
        self.child.interact()

    def _unlock(self):
        self.apc_lock.unlock()

    def disconnect(self):
        # self._escape_to_main()

        self.sendnl(APC_LOGOUT)
        self.child.sendeof()
        if not self.quiet:
            print('DISCONNECTED from %s' % self.host)

        if self.verbose:
            print('[%s]' % ''.join(self.child.readlines()))

        self.child.close()
        self._unlock()

    def control_outlet(self, outlet):
        raise NotImplementedError()

    def get_command_result(self):
        raise NotImplementedError()


class APC2(AbstractAPC):
    APC_IMMEDIATE_ON     = '1'
    APC_IMMEDIATE_OFF    = '3'
    APC_IMMEDIATE_REBOOT = '4'

    def control_outlet(self, outlet):
        self.sendnl('1')
        self.sendnl('1')
        self.sendnl(str(outlet))
        self.sendnl('1')
        self.child.before

    def get_command_result(self):
        self.child.expect('Outlet State')


class APC3(AbstractAPC):
    APC_IMMEDIATE_ON     = '1'
    APC_IMMEDIATE_OFF    = '2'
    APC_IMMEDIATE_REBOOT = '3'
    APC_DELAYED_ON       = '4'
    APC_DELAYED_OFF      = '5'
    APC_DELAYED_REBOOT   = '6'

    def control_outlet(self, outlet):
        self.sendnl('1')
        self.sendnl('2')
        self.sendnl('1')
        self.sendnl(str(outlet))
        self.sendnl('1')
        self.child.before

    def configure_outlet(self, outlet):
        self.sendnl('1')
        self.sendnl('2')
        self.sendnl('1')
        self.sendnl(str(outlet))
        self.sendnl('2')
        self.child.before

    def get_command_result(self):
        self.child.expect('Command successfully issued')

    def on_off_delayed(self, outlet, on, delay):
        (outlet, outlet_name) = self.get_outlet(outlet)

        self.configure_outlet(outlet)
        self.child.expect("Configure Outlet")

        if on:
            self.sendnl('2')  # Power On Delay(sec)
        else:
            self.sendnl('3')  # Power Off Delay(sec)
        if delay == -1 or delay >= 0 and delay <= 7200:
            self.sendnl(str(delay))
        else:
            raise NotImplementedError("Delay Range: -1 to 7200 sec, where -1=Never")
        self.sendnl('5')  # Accept Changes
        self.child.before

        self._escape_to_main()

        self.control_outlet(outlet)
        self.child.expect("Control Outlet")

        if on:
            cmd = self.APC_DELAYED_ON
            str_cmd = 'On'
        else:
            cmd = self.APC_DELAYED_OFF
            str_cmd = 'Off'

        self.sendnl(cmd)
        self.sendnl(APC_YES)
        self.sendnl('')

        self.get_command_result()

        self.notify(outlet_name, str_cmd)

        self._escape_to_main()

    def reboot_delayed(self, outlet, delay):
        raise NotImplementedError("ToDo: delay!=duration")
