#!/usr/bin/python3
import sys, os, re
sys.path.append('./debian')
from control import getDpkgArchitecture

if __name__ == '__main__':

    if not sys.argv[1].endswith('.in'):
        raise Exception('Changing a non-template file???')
    dest = re.sub('\.in$', '', sys.argv[1])
    host_multiarch = getDpkgArchitecture('DEB_HOST_MULTIARCH')

    with open(sys.argv[1], 'r') as srcf, open(dest, 'w') as dstf:
        lines = srcf.readlines()
        lines = [line.replace('@DEB_HOST_MULTIARCH@', host_multiarch)
                 for line in lines]
        dstf.writelines(lines)
    print('wrote {}'.format(dest))
