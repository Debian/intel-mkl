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


def installIncludes(filelist: List[str],
                    *, verbose: bool = False) -> List[str]:
    '''
    Install docs and return the filtered list.
    Print ignored files when verbose is set.
    '''
    incs = [x for x in filelist if '/linux/mkl/include/' in x]
    incs += [x for x in filelist if '/linux/mkl/bin/pkgconfig/' in x]
    rest = [x for x in filelist if x not in incs]
    # install them!
    for inc in incs:
        path, fname = os.path.dirname(inc), os.path.basename(inc)
        if 'pkgconfig' not in path:
            package = 'libmkl-dev'
            dest = os.path.dirname(re.sub('.*include/', '', inc))
            dest = f'usr/include/mkl/{dest}'
            print(f'installing {fname} ➜ {package} : {dest}')
            installFile(inc, package, dest)
        else:
            package = 'libmkl-dev'
            print(f'installing {fname} ➜ {package}')
            installFile(inc, package, f'usr/share/pkgconfig/')
    return rest


def installTools(filelist: List[str], deb_host_arch: str,
                 *, verbose: bool = False) -> List[str]:
    '''
    Install tools. Argument is similary to previous functions.
    '''
    tools = [x for x in allfiles if '/linux/mkl/tools/' in x]
    rest = [x for x in filelist if x not in tools]
    # install them!
    for tool in tools:
        path, fname = os.path.dirname(tool), os.path.basename(tool)
        if 'mkl_link_tool' in tool:
            package = 'intel-mkl-linktool'
            print(f'installing {fname} ➜ {package}')
            installFile(tool, package, 'usr/bin/')
        else:
            package = 'libmkl-full-dev'
            print(f'installing {fname} ➜ {package}')
            installFile(tool, package, 'usr/share/intel-mkl/')
    return rest


def installDocs(filelist: List[str], *, verbose: bool = False) -> List[str]:
    '''
    similar to previous functions.
    '''
    docs = [x for x in filelist if '/documentation_' in x]
    rest = [x for x in filelist if x not in docs]
    # install them!
    for doc in docs:
        path, fname = os.path.dirname(doc), os.path.basename(doc)
        package = 'intel-mkl-doc'
        if re.match('.*/en/mkl/.*', path):
            dest = os.path.dirname(re.sub('.*/en/mkl/', '', doc))
            dest = f'usr/share/doc/intel-mkl/{dest}'
            print(f'installing {fname} ➜ {package} : {dest}')
            installFile(doc, package, dest)
        elif re.match('.*/ja/mkl/.*', path): # Japanese
            dest = os.path.dirname(re.sub('.*/ja/mkl/', '', doc))
            dest = f'usr/share/doc/intel-mkl/ja/{dest}'
            print(f'installing {fname} ➜ {package} : {dest}')
            installFile(doc, package, dest)
        else:
            raise Exception('New language found??')
    return rest


def installMisc(filelist: List[str], *, verbose: bool = False) -> List[str]:
    '''
    similar to previous functions.
    '''
    miscs = [x for x in filelist if '/linux/mkl/benchmarks/' in x]
    miscs += [x for x in filelist if '/linux/mkl/examples/' in x]
    miscs += [x for x in filelist if '/linux/mkl/interfaces/' in x]
    miscs += [x for x in filelist if 'samples.html' in x]
    rest = [x for x in filelist if x not in miscs]
    # let's install the misc stuff!
    # XXX: the benchmark files are problematic: rpath, missing libmpicxx.so.12
    #      currently we don't install them.
    #installFile(
    #    'opt/intel/compilers_and_libraries_2018.2.199/linux/mkl/benchmarks',
    #    'libmkl-full-dev', 'usr/share/intel-mkl/')
    miscs = [x for x in miscs if 'mkl/benchmarks' not in x]
    installFile(
        'opt/intel/compilers_and_libraries_2018.2.199/linux/mkl/examples',
        'intel-mkl-doc', 'usr/share/doc/intel-mkl/')
    miscs = [x for x in miscs if 'mkl/examples' not in x]
    installFile(
        'opt/intel/compilers_and_libraries_2018.2.199/linux/mkl/interfaces',
        'libmkl-full-dev', 'usr/share/intel-mkl/')
    miscs = [x for x in miscs if 'mkl/interfaces' not in x]
    installFile('opt/intel/samples_2018/en/samples.html',
        'intel-mkl-doc', 'usr/share/doc/intel-mkl/')
    miscs = [x for x in miscs if 'samples.html' not in x]
    for misc in miscs:
        if verbose:
            print('Ignoring', misc)
    return rest


def installCats(filelist: List[str], deb_host_arch: str,
                *, verbose: bool = False) -> List[str]:
    '''
    similar to previous functions
    '''
    cats = [x for x in filelist if re.match('.*\.cat$', x)]
    rest = [x for x in filelist if x not in cats]
    # find opt -type f -name '*.cat' -exec md5sum '{}' \;
    # amd64 and i386 message catalog files are the same.
    if 'amd64' == deb_host_arch:
        installFile('opt/intel/compilers_and_libraries_2018.2.199/linux/mkl/lib/intel64_lin/locale/ja_JP/mkl_msg.cat',
                    'libmkl-locale', 'usr/share/locale/ja_JP/')
        installFile('opt/intel/compilers_and_libraries_2018.2.199/linux/mkl/lib/intel64_lin/locale/en_US/mkl_msg.cat',
                    'libmkl-locale', 'usr/share/locale/en_US/')
    else: # i386
        installFile('opt/intel/compilers_and_libraries_2018.2.199/linux/mkl/lib/ia32_lin/locale/ja_JP/mkl_msg.cat',
                    'libmkl-locale', 'usr/share/locale/ja_JP/')
        installFile('opt/intel/compilers_and_libraries_2018.2.199/linux/mkl/lib/ia32_lin/locale/en_US/mkl_msg.cat',
                    'libmkl-locale', 'usr/share/locale/en_US/')
    return rest


def overrideLintian() -> None:
    '''
    Write lintian-overrides files
    '''
    packages = parsePackages()

    # shared lib packages
    for p in [p for p in packages if 'libmkl-' in p
                and 'meta' not in p and '-dev' not in p]:
        overrides = [f'# Automatically generated by {__file__}',  # comment
                     'unstripped-binary-or-object',  # stripping not alowed
                     'library-not-linked-against-libc',  # upstream issue
                     'hardening-no-fortify-functions',  # upstream issue
                     'hardening-no-bindnow',  # upstream issue
                     'spelling-error-in-binary',  # upstream issue
                     'sharedobject-in-library-directory-missing-soname',  # upstream issue
                     ]
        print(f'lintian overrides for {p} ...')
        with open(f'debian/{p}.lintian-overrides', 'a') as f:
            f.writelines(x + '\n' for x in overrides)

    # static lib packages
    for p in [p for p in packages if 'libmkl-' in p
                and 'meta' not in p and '-dev' in p]:
        overrides = [f'# Automatically generated by {__file__}',  # comment
                      'unstripped-static-library',  # upstream issue
                      'static-library-has-unneeded-section',  # upstream issue
                     ]
        print(f'lintian overrides for {p} ...')
        with open(f'debian/{p}.lintian-overrides', 'a') as f:
            f.writelines(x + '\n' for x in overrides)

if __name__ == '__main__':

    dh_verbose = os.getenv('DH_VERBOSE')  or True
    host_arch = getDpkgArchitecture('DEB_HOST_ARCH')
    host_multiarch = getDpkgArchitecture('DEB_HOST_MULTIARCH')
    #host_arch, host_multiarch = 'i386', 'i386-linux-gnu'  # DEBUG for i386

    allfiles = sorted(glob.glob('opt/**', recursive=True))
    num_allfiles = len(allfiles)
    allfiles = [x for x in allfiles if not os.path.isdir(x)]  # Remove dirs

    # install .so files and filter the list
    allfiles = installSharedObjects(
                   allfiles, host_arch, host_multiarch, verbose=dh_verbose)

    # install .a files and filter the list
    allfiles = installStaticLibs(
                   allfiles, host_arch, host_multiarch, verbose=dh_verbose)

    # install header files and filter the list
    allfiles = installIncludes(allfiles, verbose=dh_verbose)

    # install tools and filter the list
    allfiles = installTools(allfiles, host_arch, verbose=dh_verbose)

    # install docs and filter the list
    allfiles = installDocs(allfiles, verbose=dh_verbose)

    # install misc files and filter the list
    allfiles = installMisc(allfiles, verbose=dh_verbose)

    # install the locale file
    allfiles = installCats(allfiles, host_arch, verbose=dh_verbose)

    # filter the files that we don't want
    allfiles = [x for x in allfiles if 'opt/intel/parallel_studio_xe' not in x]
    allfiles = [x for x in allfiles if 'iomp' not in x]

    print(f'{len(allfiles)} / {num_allfiles} Files left uninstalled.')

    # just like what dh-missing --list-missing does.
    if dh_verbose:
        for f in allfiles: print(f)

    # the license files, the shell scripts for compiler variables are ignored.

    # do the lintian stuff
    overrideLintian()
