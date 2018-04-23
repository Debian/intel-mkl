#!/usr/bin/python3
# Helper Script for INTEL-MKL Packaging
# Copyright (C) 2018 Mo Zhou <cdluminate@gmail.com>
# MIT License
import os, re, sys, subprocess
from typing import *


def parse_binary_packages(control: str) -> List[Tuple[str,str]]:
    '''
    Parse the given control file. This is a working DIRTY HACK.
    returns List[Tuple(Package, Architectures)]
    '''
    packages = re.findall('Package:\s*(.*)', control)
    architectures = re.findall('Architecture:\s*(.*)', control)
    assert(len(packages) == len(architectures))
    return list(zip(packages, architectures))


def generate_install_files(packages: List[str], multiarch: str) -> None:
    '''
    Automatically generate .install files for shared object packages
    '''
    for p in packages:
        so = p.replace('-', '_') + '.so'
        install = f'{so}\tusr/include/{multiarch}/'
        with open(f'debian/{p}.install', 'w') as f:
            f.write(install)


if __name__ == '__main__':
    deb_host_arch = subprocess.Popen(['dpkg-architecture', '-qDEB_HOST_ARCH'],
                    stdout=subprocess.PIPE).communicate()[0].decode().strip()
    deb_host_multiarch = subprocess.Popen(['dpkg-architecture',
                    '-qDEB_HOST_MULTIARCH'], stdout=subprocess.PIPE
                     ).communicate()[0].decode().strip()

    # Read control file and parse
    control = open('debian/control', 'r').read()
    packages = list(parse_binary_packages(control))
    # Filter the package list by architecture and name
    packages = [p for (p, a) in packages if deb_host_arch in a
                  and p.startswith('lib') and '-dev' not in p]
    # Automatically generate install files for shared object packages
    generate_install_files(packages, deb_host_multiarch)
