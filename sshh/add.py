import os
import sys
import subprocess
import logging
import argparse
from getpass import getpass
from pathlib import Path

from sshh.regstry import Registry
from sshh.askpass import get_executable_askpass
from sshh.runner import run

logger = logging.getLogger(__name__)


def test_passphrase(keyfile, phrase) -> bool:
    """confirm passphrase for the keyfile.

    :param keyfile: ssh key file path
    :param phrase: passphrase for keyfile
    :return: True if the keyfile/phrase pair is matched, otherwise False.
    """
    env = os.environ.copy()
    env['SSH_ASKPASS'] = get_executable_askpass()
    env['DISPLAY'] = ':999'
    env['PASSPHRASE'] = phrase
    p = subprocess.Popen(
        ['ssh-keygen', '-yf', str(keyfile)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        encoding='ascii',
        preexec_fn=os.setsid
    )
    try:
        r = p.communicate(timeout=1)
        logger.debug('ssh-add return %s: %s', p.returncode, r)
    except subprocess.TimeoutExpired:
        logger.error('timeout')
        p.kill()
        logger.error(p.communicate())

    return p.returncode == 0


def cmd_add(request):
    passphrase = getpass(prompt='Enter passphrase for the keyfile: ')
    fpath = Path(request.keyfile.name).absolute()
    if test_passphrase(fpath, passphrase):
        request.registry.add_passphrase(request.group, fpath, passphrase)
        request.registry.save()
        logger.info('The keyfile is registered.')
    else:
        logger.error('passphrase for the keyfile is not correct.')


def cmd_list(request):
    for g, d in request.registry.items():
        print(f'[{g}]')
        for fn in d:
            print(fn)
        print()


def get_argparser():
    p = argparse.ArgumentParser()
    p.add_argument('-d', '--debug', action='store_true', default=False, help='debug mode')
    p.add_argument('-g', '--group', type=str, default='default', help='group name')
    eg = p.add_mutually_exclusive_group(required=True)
    eg.add_argument('-l', '--list', action='store_true', default=False, help='list keys')
    eg.add_argument('keyfile', nargs='?', type=argparse.FileType('r'), default=None, help='ssh secret key file')

    return p


def main():
    p = get_argparser()
    args = p.parse_args(sys.argv[1:])

    if args.list:
        cmd = cmd_list
    else:
        cmd = cmd_add
    try:
        run(cmd, p)
    except Registry.InvalidToken:
        logger.error('Wrong password')
        sys.exit(1)


if __name__ == '__main__':
    main()
