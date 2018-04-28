#!/usr/bin/python3
# Helper Script for INTEL-MKL Packaging
# Copyright (C) 2018 Mo Zhou <cdluminate@gmail.com>
# MIT License
# FIXME: Backporters, please notice that this script utilized one of the
#        python3.6 features (format string, i.g. f''). That means this script
#        requires python >= 3.6 . I'm sorry for the inconvenience but I like
#        this feature so much ...
import os, re, sys, subprocess, glob, copy
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


def installSharedObjects(filelist: List[str],
                         deb_host_arch: str, deb_host_multiarch: str,
                         *, verbose: bool = False) -> List[str]:
    '''
    Glob all the shared object from the file list, and write install entries
    for them. The filtered list that does not contain .so file will be returned.
    When verbose is toggled, it prints .so files ignored.
    '''
    # Glob libs
    solibs = [x for x in filelist if re.match('.*\.so(\.?\d*)$', x)]
    libs = copy.copy(solibs)
    rest = [x for x in filelist if not re.match('.*\.so(\.?\d*)$', x)]
    # get package names in control file
    packages = parsePackages()
    # filter the lib list by architecture
    if deb_host_arch == 'amd64':
        libs = [x for x in libs if 'ia32' not in x]
        libs = [x for x in libs if 'intel64_lin' not in x] # dedup
    else:
        libs = [x for x in libs if 'intel64' not in x]
        libs = [x for x in libs if 'ia32_lin' not in x]
    # don't care about the libs used by intel's installer
    libs = [x for x in libs if 'uninstall' not in x]
    # tbb and iomp5 are already provided by other packages
    libs = [x for x in libs if 'iomp' not in x]
    libs = [x for x in libs if 'tbb/' not in x]
    # report dropped files
    for lib in solibs:
        if lib not in libs and verbose:
            print('Ignoring', lib)
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
    return rest


def installStaticLibs(filelist: List[str],
                      deb_host_arch: str, deb_host_multiarch: str,
                      *, verbose: bool = False) -> List[str]:
    '''
    Glob all the static libraries from filelist, and add them into corresponding
    .install files. A list contains no .a file will be returned.
    When verbose is toggled, it prints ignored static libs.
    '''
    # Glob libs
    alibs = [x for x in allfiles if re.match('.*\.a$', x)]
    libs = copy.copy(alibs)
    rest = [x for x in allfiles if not re.match('.*\.a$', x)]
    # get package names in control file
    packages = parsePackages()
    # filter the lib list by architecture
    if deb_host_arch == 'amd64':
        libs = [x for x in libs if 'ia32' not in x]
        libs = [x for x in libs if 'intel64_lin' not in x] # dedup
    else:
        libs = [x for x in libs if 'intel64' not in x]
        libs = [x for x in libs if 'ia32_lin' not in x]
    libs = [x for x in libs if 'benchmarks' not in x]
    libs = [x for x in libs if 'iomp' not in x]
    # report static libs being dropped
    for lib in alibs:
        if lib not in libs and verbose:
            print('Ignoring', lib)
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
    return rest


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

    dh_verbose = os.getenv('DH_VERBOSE')  or True
    host_arch = getDpkgArchitecture('DEB_HOST_ARCH')
    host_multiarch = getDpkgArchitecture('DEB_HOST_MULTIARCH')
    #host_arch, host_multiarch = 'i386', 'i386-linux-gnu'  # DEBUG for i386

    allfiles = sorted(glob.glob('opt/**', recursive=True))
    allfiles = [x for x in allfiles if not os.path.isdir(x)]  # Remove dirs

    # install .so files and filter the list
    allfiles = installSharedObjects(
                   allfiles, host_arch, host_multiarch, verbose=dh_verbose)

    allfiles = installStaticLibs(
                   allfiles, host_arch, host_multiarch, verbose=dh_verbose)
    exit()

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
