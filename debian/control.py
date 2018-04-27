#!/usr/bin/python3
# Helper Script for INTEL-MKL Packaging
# Copyright (C) 2018 Mo Zhou <cdluminate@gmail.com>
# MIT License
import os, re, sys, subprocess, glob
from typing import *


def getDpkgArchitecture(query: str) -> str:
    '''
    dpkg-architecture -qQUERY
    '''
    result = subprocess.Popen(['dpkg-architecture', f'-q{query}'],
             stdout=subprocess.PIPE).communicate()[0].decode().strip()
    return result


def installFile(fpath: str, package: str, dest: str = '') -> None:
    '''
    Write an entry in specified package's install file, for installing
    the file to dest.
    '''
    with open(os.path.join('debian', f'{package}.install'), 'a') as f:
        f.write(f'{fpath}\t{dest}\n' if dest else f'{fpath}')


def installSharedObjects() -> None:
    '''
    Glob all the shared object and write install entries for them
    '''
    # Glob libs
    shlibs = glob.glob('opt/**/**.so', recursive=True)
    # filter the lib list by architecture
    deb_host_arch = getDpkgArchitecture('DEB_HOST_ARCH')
    deb_host_multiarch = getDpkgArchitecture('DEB_HOST_MULTIARCH')
    if deb_host_arch == 'amd64':
        shlibs = [x for x in shlibs if 'ia32' not in x]
        # dedup
        shlibs = [x for x in shlibs if 'intel64_lin' not in x]
    else:
        shlibs = [x for x in shlibs if 'intel64' not in x]
        shlibs = [x for x in shlibs if 'ia32_lin' not in x]
    # don't care about the libs used by intel's installer
    shlibs = [x for x in shlibs if 'uninstall' not in x]
    # tbb and iomp5 are already provided by other packages
    shlibs = [x for x in shlibs if 'iomp' not in x]
    shlibs = [x for x in shlibs if 'tbb/' not in x]
    # get package names in control file
    packages = parsePackages()
    # now let's install them !
    for so in shlibs:
        path, fname = os.path.dirname(so), os.path.basename(so)
        package = re.sub('\.so$', '', fname).replace('_', '-')
        #print(path, fname, package)
        if package in packages:
            print(f'installing {fname} ➜ {package}')
            installFile(os.path.join(path, fname), package,
                    f'usr/lib/{deb_host_multiarch}/')
        else:
            print(f'Warning: Which package should ship {fname} ??')


def parsePackages() -> List[str]:
    '''
    Parse debian/control and return a list of Package names
    '''
    with open('debian/control', 'r') as f:
        control = f.read()
    packages = re.findall('Package:\s*(.*)', control)
    return packages


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

    installSharedObjects()
    exit()

    # Read control file and parse
    control = open('debian/control', 'r').read()
    packages = list(parse_binary_packages(control))
    # Filter the package list by architecture and name
    packages = [p for (p, a) in packages if deb_host_arch in a
                  and p.startswith('lib') and '-dev' not in p]
    # Automatically generate install files for shared object packages
    generate_install_files(packages, deb_host_multiarch)
