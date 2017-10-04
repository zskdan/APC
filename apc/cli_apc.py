#!/usr/bin/env python

from argparse import ArgumentParser
import pexpect
from apc import APC
from apc import APC_DEFAULT_HOST, APC_DEFAULT_USER, APC_DEFAULT_PASSWORD


def main():
    parser = ArgumentParser(description='APC Python CLI')
    parser.add_argument('--host', action='store', default=APC_DEFAULT_HOST,
                        help='Override the host')
    parser.add_argument('--user', action='store', default=APC_DEFAULT_USER,
                        help='Override the username')
    parser.add_argument('--password', action='store', default=APC_DEFAULT_PASSWORD,
                        help='Override the password')

    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose messages')
    parser.add_argument('--quiet', action='store_true',
                        help='Quiet')
    parser.add_argument('--debug', action='store_true',
                        help='Debug mode')
    parser.add_argument('--reboot', action='store',
                        help='Reboot an outlet')
    parser.add_argument('--off', action='store',
                        help='Turn off an outlet')
    parser.add_argument('--on', action='store',
                        help='Turn on an outlet')

    args = parser.parse_args()

    is_command_specified = (args.reboot or args.debug or args.on or args.off)

    if not is_command_specified:
        parser.print_usage()
        raise SystemExit(1)

    try:
        apc = APC(args)
    except pexpect.TIMEOUT as e:
        raise SystemExit('ERROR: Timeout connecting to APC')

    if args.debug:
        apc.debug()
    else:
        try:
            if args.reboot:
                apc.reboot(args.reboot)
            elif args.on:
                apc.on(args.on)
            elif args.off:
                apc.off(args.off)
        except pexpect.TIMEOUT as e:
            raise SystemExit('APC failed!  Pexpect result:\n%s' % e)
        finally:
            apc.disconnect()


if __name__ == '__main__':
    main()
