#!/usr/bin/python3
# Helper Script for INTEL-MKL Packaging
# Copyright (C) 2018 Mo Zhou <cdluminate@gmail.com>
# MIT License
# FIXME: Backporters, please notice that this script utilized one of the
#        python3.6 features (format string, i.g. f''). That means this script
#        requires python >= 3.6 . I'm sorry for the inconvenience but I like
#        this feature so much ...
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


def parsePackages() -> List[str]:
    '''
    Parse debian/control and return a list of Package names
    '''
    with open('debian/control', 'r') as f:
        control = f.read()
    packages = re.findall('Package:\s*(.*)', control)
    return packages


def installSharedObjects(deb_host_arch: str, deb_host_multiarch: str) -> None:
    '''
    Glob all the shared object and write install entries for them
    '''
    # Glob libs
    libs = glob.glob('opt/**/**.so', recursive=True)
    # get package names in control file
    packages = parsePackages()
    # filter the lib list by architecture
    if deb_host_arch == 'amd64':
        libs = [x for x in libs if 'ia32' not in x]
        # dedup
        libs = [x for x in libs if 'intel64_lin' not in x]
    else:
        libs = [x for x in libs if 'intel64' not in x]
        libs = [x for x in libs if 'ia32_lin' not in x]
    # don't care about the libs used by intel's installer
    libs = [x for x in libs if 'uninstall' not in x]
    # tbb and iomp5 are already provided by other packages
    libs = [x for x in libs if 'iomp' not in x]
    libs = [x for x in libs if 'tbb/' not in x]
    # now let's install them !
    for so in libs:
        path, fname = os.path.dirname(so), os.path.basename(so)
        package = re.sub('\.so$', '', fname).replace('_', '-')
        #print(path, fname, package)
        if package in packages:
            print(f'installing {fname} ➜ {package}')
            installFile(os.path.join(path, fname), package,
                    f'usr/lib/{deb_host_multiarch}/')
        else:
            raise Exception(f'Warning: Which package should ship {fname} ??')


def installStaticLibs(deb_host_arch: str, deb_host_multiarch: str) -> None:
    '''
    Glob all the static libraries and add them into .install files
    '''
    # Glob libs
    libs = glob.glob('opt/**/**.a', recursive=True)
    # get package names in control file
    packages = parsePackages()
    # filter the lib list by architecture
    if deb_host_arch == 'amd64':
        libs = [x for x in libs if 'ia32' not in x]
        # dedup
        libs = [x for x in libs if 'intel64_lin' not in x]
    else:
        libs = [x for x in libs if 'intel64' not in x]
        libs = [x for x in libs if 'ia32_lin' not in x]
    libs = [x for x in libs if 'benchmarks' not in x]
    libs = [x for x in libs if 'iomp' not in x]
    # now let's install them !
    for so in libs:
        path, fname = os.path.dirname(so), os.path.basename(so)
        if any(x in fname for x in ('thread', 'sequential')):
            package = 'libmkl-threading-dev'
        elif any(x in fname for x in ('blacs', 'scalapack', 'cdft')):
            package = 'libmkl-cluster-dev'
        elif any(x in fname for x in ('intel_', 'gf_')):
            package = 'libmkl-interface-dev'
        elif any(x in fname for x in ('core', 'lapack', 'blas')):
            package = 'libmkl-computational-dev'
        else:
            package = 'no-such-package'
        if package in packages:
            print(f'installing {fname} ➜ {package}')
            installFile(os.path.join(path, fname), package,
                    f'usr/lib/{deb_host_multiarch}/')
        else:
            raise Exception(f'Warning: Which package should ship {fname} ??')


def installDocs() -> None:
    '''
    '''
    pass


def installIncludes() -> None:
    '''
    '''
    pass


def installTools() -> None:
    '''
    '''
    pass


def installMisc() -> None:
    '''
    '''
    pass


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

    host_arch = getDpkgArchitecture('DEB_HOST_ARCH')
    host_multiarch = getDpkgArchitecture('DEB_HOST_MULTIARCH')
    #host_arch, host_multiarch = 'i386', 'i386-linux-gnu'  # DEBUG for i386

    allfiles = sorted(glob.glob('opt/**', recursive=True))
    allfiles = [x for x in allfiles if not os.path.isdir(x)]  # Remove dirs

    installSharedObjects(host_arch, host_multiarch)
    allfiles = [x for x in allfiles if not re.match('.*\.so(\.?\d*)$', x)]

    installStaticLibs(host_arch, host_multiarch)
    allfiles = [x for x in allfiles if not re.match('.*\.a$', x)]

    installDocs()
    allfiles = [x for x in allfiles if not '/documentation_' in x]

    installIncludes()
    allfiles = [x for x in allfiles if not '/linux/mkl/include/' in x]
    allfiles = [x for x in allfiles if not '/linux/mkl/bin/pkgconfig/' in x]

    installTools()
    allfiles = [x for x in allfiles if not '/linux/mkl/tools/' in x]

    installMisc()
    allfiles = [x for x in allfiles if not '/linux/mkl/benchmarks/' in x]
    allfiles = [x for x in allfiles if not '/linux/mkl/examples/' in x]
    allfiles = [x for x in allfiles if not '/linux/bin/' in x]

    pass  # FIXME: how to deal with the interfaces
    allfiles = [x for x in allfiles if '/linux/mkl/interfaces/' not in x]

    # ignore unwanted files
    allfiles = [x for x in allfiles if 'opt/intel/parallel_studio_xe' not in x]
    allfiles = [x for x in allfiles if 'iomp' not in x]

    # just like dh-missing --list-missing
    for f in allfiles: print(f)

    exit()

    # Read control file and parse
    control = open('debian/control', 'r').read()
    packages = list(parse_binary_packages(control))
    # Filter the package list by architecture and name
    packages = [p for (p, a) in packages if deb_host_arch in a
                  and p.startswith('lib') and '-dev' not in p]
    # Automatically generate install files for shared object packages
    generate_install_files(packages, deb_host_multiarch)
