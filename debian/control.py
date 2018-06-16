#!/usr/bin/python3
# Helper Script for INTEL-MKL Packaging
# Copyright (C) 2018 Mo Zhou <cdluminate@gmail.com>
# MIT License
# FIXME: Backporters, please notice that this script utilized one of the
#        python3.6 features (format string, i.g. f''). That means this script
#        requires python >= 3.6 . I'm sorry for the inconvenience but I like
#        this feature so much ... Type annotation for python >= 3.5 is also
#        used ...
import os, re, sys, subprocess, glob, copy
from typing import *


def dhVerbose() -> bool:
    '''
    Literally get the value of DH_VERBOSE
    '''
    return os.getenv('DH_VERBOSE') or True


def getDpkgArchitecture(query: str) -> str:
    '''
    dpkg-architecture -qQUERY
    '''
    result = subprocess.Popen(['dpkg-architecture', f'-q{query}'],
             stdout=subprocess.PIPE).communicate()[0].decode().strip()
    return result


def parsePackages() -> List[str]:
    '''
    Parse debian/control and return a list of Package names
    '''
    with open('debian/control', 'r') as f:
        control = f.read()
    packages = re.findall('Package:\s*(.*)', control)
    return packages


def eGrep(ls: List[str], regex: str) -> List[str]:
    '''
    Just like grep -e.
    '''
    regex, match, unmatch = re.compile(regex), [], []
    for l in ls:
        if regex.match(l):
            match.append(l)
        else:
            unmatch.append(l)
    return match, unmatch


def installFile(fpath: str, package: str, dest: str = '') -> None:
    '''
    Write an entry in specified package's install file, for installing
    the file to dest.
    '''
    if package not in parsePackages():
        raise Exception(f'Package [{package}] is not found in debian/control!' +
                f' cannot install {fpath}')
    print(f'installing {fpath} ➜ {package}')
    with open(os.path.join('debian', f'{package}.install'), 'a') as f:
        f.write(f'{fpath}\t{dest}\n' if dest else f'{fpath}')


def installSharedObjects(filelist: List[str],
                         *, verbose: bool = dhVerbose()) -> List[str]:
    '''
    Glob all the shared object from the file list, and write install entries
    for them. The filtered list that does not contain .so file will be returned.
    When verbose is toggled, it prints .so files ignored.
    '''
    # lookup arch info
    deb_host_arch = getDpkgArchitecture('DEB_HOST_ARCH')
    deb_host_multiarch = getDpkgArchitecture('DEB_HOST_MULTIARCH')
    # Glob libs
    solibs, rest = eGrep(filelist, '.*\.so(\.?\d*)$')
    libs = copy.copy(solibs)
    # filter the lib list by architecture
    if deb_host_arch == 'amd64':
        _, libs = eGrep(libs, '.*ia32.*')
        _, libs = eGrep(libs, '.*intel64_lin.*')  # Dedup
    else:
        _, libs = eGrep(libs, '.*intel64.*')
        _, libs = eGrep(libs, '.*ia32_lin.*')  # Dedup
    # report dropped files
    for lib in solibs:
        if lib not in libs and verbose:
            print('Ignoring', lib)
    # now let's install them !
    for so in libs:
        path, fname = os.path.dirname(so), os.path.basename(so)
        package = re.sub('\.so$', '', fname).replace('_', '-')
        installFile(os.path.join(path, fname), package,
                f'usr/lib/{deb_host_multiarch}/')
    return rest


def installStaticLibs(filelist: List[str],
                      *, verbose: bool = dhVerbose()) -> List[str]:
    '''
    Glob all the static libraries from filelist, and add them into corresponding
    .install files. A list contains no .a file will be returned.
    When verbose is toggled, it prints ignored static libs.
    '''
    # lookup arch info
    deb_host_arch = getDpkgArchitecture('DEB_HOST_ARCH')
    deb_host_multiarch = getDpkgArchitecture('DEB_HOST_MULTIARCH')
    # Glob libs
    alibs, rest = eGrep(filelist, '.*/linux/mkl/lib/.*\.a$')
    libs = copy.copy(alibs)
    # filter the lib list by architecture
    if deb_host_arch == 'amd64':
        libs = [x for x in libs if 'ia32' not in x]
        libs = [x for x in libs if 'intel64_lin' not in x] # dedup
    else:
        libs = [x for x in libs if 'intel64' not in x]
        libs = [x for x in libs if 'ia32_lin' not in x] # dedup
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
        elif any(x in fname for x in ('intel_', 'gf_', 'intel.a', 'blas95',
                                      'lapack95', 'gf.a')):
            package = 'libmkl-interface-dev'
        elif any(x in fname for x in ('core', 'lapack', 'blas')):
            package = 'libmkl-computational-dev'
        else:
            package = 'no-such-package'
        installFile(os.path.join(path, fname), package,
                    f'usr/lib/{deb_host_multiarch}/')
    return rest


def installIncludes(filelist: List[str],
                    *, verbose: bool = dhVerbose()) -> List[str]:
    '''
    Install docs and return the filtered list.
    Print ignored files when verbose is set.
    '''
    _, rest = eGrep(filelist, '.*/linux/mkl/include/.*')
    incs = 'opt/intel/compilers_and_libraries_*/linux/mkl/include/*'
    installFile(incs, 'libmkl-dev', 'usr/include/mkl/')
    return rest


def installTools(filelist: List[str],
                 *, verbose: bool = dhVerbose()) -> List[str]:
    '''
    Install tools. Argument is similary to previous functions.
    '''
    _, rest = eGrep(filelist, '.*/linux/mkl/tools/.*')
    installFile(
            'opt/intel/compilers_and_libraries_*/linux/mkl/tools/mkl_link_tool',
            'intel-mkl-linktool', 'usr/bin/')
    installFile(
            'opt/intel/compilers_and_libraries_*/linux/mkl/tools/builder',
            'libmkl-full-dev', 'usr/share/intel-mkl/')
    return rest


def installDocs(filelist: List[str],
                *, verbose: bool = dhVerbose()) -> List[str]:
    '''
    similar to previous functions.
    '''
    _, rest = eGrep(filelist, '^opt/intel/documentation.*')
    _, rest = eGrep(rest, '^opt/intel/samples.*')
    installFile('opt/intel/documentation_2018',
                'intel-mkl-doc', 'usr/share/doc/intel-mkl/')
    installFile('opt/intel/samples_2018',
                'intel-mkl-doc', 'usr/share/doc/intel-mkl/')
    return rest


def installCatalog(filelist: List[str],
                *, verbose: bool = False) -> List[str]:
    '''
    similar to previous functions
    '''
    deb_host_arch = getDpkgArchitecture('DEB_HOST_ARCH')
    _, rest = eGrep(filelist, '.*\.cat$')
    # find opt -type f -name '*.cat' -exec md5sum '{}' \;
    # amd64 and i386 message catalog files are the same.
    if 'amd64' == deb_host_arch:
        installFile('opt/intel/compilers_and_libraries_*/linux/mkl/lib/intel64_lin/locale/ja_JP/mkl_msg.cat',
                    'libmkl-locale', 'usr/share/locale/ja_JP/')
        installFile('opt/intel/compilers_and_libraries_*/linux/mkl/lib/intel64_lin/locale/en_US/mkl_msg.cat',
                    'libmkl-locale', 'usr/share/locale/en_US/')
    else: # i386
        installFile('opt/intel/compilers_and_libraries_*/linux/mkl/lib/ia32_lin/locale/ja_JP/mkl_msg.cat',
                    'libmkl-locale', 'usr/share/locale/ja_JP/')
        installFile('opt/intel/compilers_and_libraries_*/linux/mkl/lib/ia32_lin/locale/en_US/mkl_msg.cat',
                    'libmkl-locale', 'usr/share/locale/en_US/')
    return rest


def installExamples(filelist: List[str]) -> List[str]:
    '''
    similar to previous
    '''
    exs, rest = eGrep(filelist, '.*/linux/mkl/examples/.*')
    for ex in exs:
        installFile(ex, 'intel-mkl-doc', 'usr/share/intel-mkl/')
    return rest


def installBenchmarks(filelist: List[str]) -> List[str]:
    '''
    similar to previous
    '''
    _, rest = eGrep(filelist, '.*/linux/mkl/benchmarks/.*')
    # hpcg is ignored.
    # - because I didn't find the way to build them without Intel C++ compiler.
    # linpack and ml_linpack are ignored. we have suggested hpcc package.
    # - linpack directory contains a pile of binaries. they works.
    # - mp_linpack same as above
    return rest


def installDebianSpecific(deb_host_arch: str, deb_host_multiarch: str) -> None:
    '''
    install debian specific files that come from debian/
    '''
    dest = f'/usr/lib/{deb_host_multiarch}/pkgconfig/'
    installFile('debian/pkgconfig/*.pc', f'libmkl-dev', dest)


def _override(package: str, overrides: List[str]) -> None:
    '''
    Write a lintian override file for specified package
    '''
    overrides = [f'# Automatically overridden by {__file__}'] + overrides
    print(f'lintian overrides for {package} ...')
    with open(f'debian/{package}.lintian-overrides', 'a') as f:
        f.writelines(x + '\n' for x in overrides)


def overrideLintian() -> None:
    '''
    Write lintian-overrides files
    '''
    packages = parsePackages()

    # shared lib packages
    for p in [p for p in packages if 'libmkl-' in p
                and 'meta' not in p and '-dev' not in p]:
        overrides = ['hardening-no-bindnow',  # upstream issue
                     'hardening-no-fortify-functions',  # upstream issue
                     'library-not-linked-against-libc',  # upstream issue
                     'shared-lib-without-dependency-information',  # upstream issue
                     'sharedobject-in-library-directory-missing-soname',  # upstream issue
                     'shlib-without-versioned-soname',  # upstream issue
                     'spelling-error-in-binary',  # upstream issue
                     'unstripped-binary-or-object',  # stripping not alowed
                     ]
        _override(p, overrides)

    # static lib packages
    for p in [p for p in packages if 'libmkl-' in p
                and 'meta' not in p and '-dev' in p]:
        overrides = ['static-library-has-unneeded-section',  # upstream issue
                     'unstripped-static-library',  # upstream issue
                     ]
        _override(p, overrides)

    # overrides for libmkl-locale:any
    p = 'libmkl-locale'
    overrides = [ # we have to make it arch-dependent, because it's used
                  # by a number of Arch:any packages. Making it Arch:all
                  # triggers lintian Errors.
                  'package-contains-no-arch-dependent-files',
                 ]
    _override(p, overrides)

    # overrides for intel-mkl-linktool:i386
    p = 'intel-mkl-linktool'
    overrides = ['binary-without-manpage',  # upstream issue
                 'unstripped-binary-or-object',  # upstream issue
                 ]
    _override(p, overrides)


if __name__ == '__main__':

    # The two variables can be overriden in d/rules or by environment
    # variables, for debugging i386 build under amd64 without any
    # cross build tooling.
    host_arch = getDpkgArchitecture('DEB_HOST_ARCH')
    host_multiarch = getDpkgArchitecture('DEB_HOST_MULTIARCH')

    allfiles = sorted(glob.glob('opt/**', recursive=True))
    num_allfiles = len(allfiles)

    # Remove directories from file list
    allfiles = [x for x in allfiles if not os.path.isdir(x)]

    # [ Filter files that we never wanted ]
    # -- upstream installer stuff. we don't need
    _, allfiles = eGrep(allfiles, '^opt/intel/parallel_studio_xe.*')
    # -- there is already libtbb-dev package.
    _, allfiles = eGrep(allfiles, '.*/libtbb.*')
    # -- libiomp5 is already prodided by other package.
    _, allfiles = eGrep(allfiles, '.*/libiomp.*')
    # -- these wrapper (interfaces/*) files relys on MKLROOT. We already broke
    #    upstream directory structure, rendering the these files hard to use.
    _, allfiles = eGrep(allfiles, '.*/linux/mkl/interfaces/.*')

    # install specific files and filter the list
    allfiles = installSharedObjects(allfiles)
    allfiles = installStaticLibs(allfiles)
    allfiles = installIncludes(allfiles)
    allfiles = installTools(allfiles)
    allfiles = installDocs(allfiles)
    allfiles = installCatalog(allfiles)
    allfiles = installExamples(allfiles)
    allfiles = installBenchmarks(allfiles)

    installDebianSpecific(host_arch, host_multiarch)

    # just like what dh-missing --list-missing does.
    print(f'{len(allfiles)} / {num_allfiles} Files left uninstalled.')
    if dhVerbose():
        for f in allfiles: print('missing', '<><><>', f)
    # notes about missing files:
    #  - /licensing/* not installed. They are in copyright.
    #  - the shell scripts for compiler variables are ignored. They are
    #    somewhat useless if we don't retain upstream directory structure.

    # do the lintian overridding
    overrideLintian()
