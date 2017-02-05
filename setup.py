# This file is part of MyPaint.


# Imports:

from __future__ import print_function
import subprocess
import glob
import os
import os.path
from distutils.core import setup
from distutils.core import Extension
from distutils.core import Command
from distutils.command.build import build as _build

import numpy


# Helper classes and routines:

class BuildTranslations (Command):
    """Builds binary message catalogs for installation.

    This is declared as a subcommand of "build", but it can be invoked
    in its own right. The generated message catalogs are later installed
    as data files.

    """

    description = "build binary message catalogs (*.mo)"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        build = self.get_finalized_command("build")
        for src in glob.glob("po/*.po"):
            data_files = self._compile_message_catalog(src, build.build_temp)
            if not self.dry_run:
                self.distribution.data_files.extend(data_files)

    def _compile_message_catalog(self, src, temp):
        lang = os.path.basename(src)[:-3]
        targ_dir = os.path.join(temp, "locale", lang, "LC_MESSAGES")
        targ = os.path.join(targ_dir, "mypaint.mo")
        install_dir = os.path.join("locale", lang, "LC_MESSAGES")

        needs_update = True
        if os.path.exists(targ):
            if os.stat(targ).st_mtime >= os.stat(src).st_mtime:
                needs_update = False

        if needs_update:
            cmd = ("msgfmt", src, "-o", targ)
            if self.dry_run:
                self.announce("would run %s" % (" ".join(cmd),))
                return []
            self.announce("running %s" % (" ".join(cmd),))

            if not os.path.exists(targ_dir):
                os.makedirs(targ_dir)
            subprocess.check_call(cmd)

        assert os.path.exists(targ)
        return [(install_dir, [targ])]


class Build (_build):
    """Custom build."""

    # Special order for swigging
    # adapted from https://stackoverflow.com/questions/17666018
    #
    # Some versions of distutils.command.build.build don't generate the
    # extension.py for a _extension.so unless the build_ext is done first
    # or you install twice.
    #
    # The fix is to build_ext before build_py, and thus swig first.
    # As of Python 2.7.13 distutils, this is still needed.

    sub_commands = (
        [(a, b) for (a, b) in _build.sub_commands if a == 'build_ext'] +
        [(a, b) for (a, b) in _build.sub_commands if a != 'build_ext'] +
        [("build_translations", None)]
    )


def uniq(items):
    """Order-preserving uniq()"""
    seen = set()
    result = []
    for i in items:
        if i in seen:
            continue
        seen.add(i)
        result.append(i)
    return result


def pkgconfig(packages, **kwopts):
    """Runs pkgconfig to update its args.

    Also returns the modified args dict. Recipe adapted from
    http://code.activestate.com/recipes/502261/

    """
    flag_map = {
        '-I': 'include_dirs',
        '-L': 'library_dirs',
        '-l': 'libraries',
    }
    extra_args_map = {
        "--libs": "extra_link_args",
        "--cflags": "extra_compile_args",
    }
    for (pc_arg, extras_key) in extra_args_map.items():
        cmd = ["pkg-config", pc_arg] + list(packages)
        for conf_arg in subprocess.check_output(cmd).split():
            flag = conf_arg[:2]
            flag_value = conf_arg[2:]
            flag_key = flag_map.get(flag)
            if flag_key:
                kw = flag_key
                val = flag_value
            else:
                kw = extras_key
                val = conf_arg
            kwopts.setdefault(kw, []).append(val)
    for kw, val in list(kwopts.items()):
        kwopts[kw] = uniq(val)
    return kwopts


# Binary extension module:

mypaintlib_opts = pkgconfig(
    packages=[
        "pygobject-3.0",
        "glib-2.0",
        "libpng",
        "lcms2",
        "gtk+-3.0",
        "libmypaint",
    ],
    include_dirs=[
        numpy.get_include(),
    ],
    extra_link_args=[
        '-O3',
        '-fopenmp',
    ],
    extra_compile_args=[
        '-Wall',
        '-Wno-sign-compare',
        '-Wno-write-strings',
        '-D_POSIX_C_SOURCE=200809L',
        '-O3',
        '-fopenmp',
    ],
)


if os.name == 'posix':
    mypaintlib_opts["extra_link_args"].append('-Wl,-z,origin')


mypaintlib = Extension(
    '_mypaintlib',
    [
        'lib/mypaintlib.i',
        'lib/fill.cpp',
        'lib/eventhack.cpp',
        'lib/gdkpixbuf2numpy.cpp',
        'lib/pixops.cpp',
        'lib/fastpng.cpp',
        'lib/brushsettings.cpp',
    ],
    swig_opts=['-Wall', '-noproxydel', '-c++'] + [
        "-I" + d for d in mypaintlib_opts["include_dirs"]
    ],
    language='c++',
    **mypaintlib_opts
)


# Data files:

# Target paths are relative to $base/share, assuming setup.py's
# default value for install-data.

data_files = [
    # TARGDIR, SRCFILES
    ("appdata", ["desktop/mypaint.appdata.xml"]),
    ("applications", ["desktop/mypaint.desktop"]),
    ("thumbnailers", ["desktop/mypaint-ora.thumbnailer"]),
    ("mypaint/brushes", ["brushes/order.conf"]),
]


# Append paths which can only derived from globbing the source tree.

data_file_patts = [
    # SRCDIR, SRCPATT, TARGDIR
    ("desktop/icons", "hicolor/*/*/*", "icons"),
    ("backgrounds", "*.*", "mypaint/backgrounds"),
    ("backgrounds", "*/*.*", "mypaint/backgrounds"),
    ("brushes", "*/*.*", "mypaint/brushes"),
    ("palettes", "*.gpl", "mypaint/palettes"),
    ("pixmaps", "*.png", "mypaint/pixmaps"),
]
for (src_pfx, src_patt, targ_pfx) in data_file_patts:
    for src_file in glob.glob(os.path.join(src_pfx, src_patt)):
        file_rel = os.path.relpath(src_file, src_pfx)
        targ_dir = os.path.join(targ_pfx, os.path.dirname(file_rel))
        data_files.append((targ_dir, [src_file]))


# Setup script "main()":

setup(
    name='MyPaint',
    version='1.3.0-alpha',
    description='Simple painting program for use with graphics tablets.',
    author='Andrew Chadwick',
    author_email='a.t.chadwick@gmail.com',
    packages=['lib', 'lib.layer', 'gui', 'gui.colors'],
    package_data={
        "gui": ['*.xml', '*.glade'],
    },
    data_files=data_files,
    cmdclass= {
        "build": Build,
        "build_translations": BuildTranslations,
    },
    scripts=[
        "mypaint.py",
        "desktop/mypaint-ora-thumbnailer.py",
    ],
    ext_modules=[mypaintlib],
)
