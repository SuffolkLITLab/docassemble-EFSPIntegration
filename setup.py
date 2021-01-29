import io
import os
from setuptools import setup, find_packages
from fnmatch import fnmatchcase
from distutils.util import convert_path

# From https://github.com/navdeep-G/setup.py/blob/master/setup.py
DESCRIPTION = 'A docassemble extension that handles EFSP Functionality'

standard_exclude = ('*.pyc', '*~', '.*', '*.bak', '*.swp*')
standard_exclude_directories = ('.*', 'CVS', '_darcs', './build', './dist', 'EGG_INFO', '*.egg-info')

here = os.path.abspath(os.path.dirname(__file__))

try:
    with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = '\n' + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION


def find_package_data(where='.', package='', exclude=standard_exclude, exclude_directories=standard_exclude_directories):
    out = {}
    stack = [(convert_path(where), '', package)]
    while stack:
        where, prefix, package = stack.pop(0)
        for name in os.listdir(where):
            fn = os.path.join(where, name)
            if os.path.isdir(fn):
                bad_name = False
                for pattern in exclude_directories:
                    if (fnmatchcase(name, pattern) or fn.lower() == pattern.lower()):
                        bad_name = True
                        break
                if bad_name:
                    continue
                if os.path.isfile(os.path.join(fn, '__init__.py')):
                    if not package:
                        new_package = name
                    else:
                        new_package = package + '.' + name
                        stack.append((fn, '', new_package))
                else:
                    stack.append((fn, prefix + name + '/', package))
            else:
                bad_name = False
                for pattern in exclude:
                    if (fnmatchcase(name, pattern) or fn.lower() == pattern.lower()):
                        bad_name = True
                        break
                if bad_name:
                    continue
                out.setdefault(package, []).append(prefix+name)
    return out


setup(name='docassemble.TylerEFSP',
      version='0.0.1',
      description=DESCRIPTION,
      long_description=long_description,
      long_description_content_type='text/markdown',
      author='Bryce Willey',
      author_email='bwilley@suffolk.edu',
      license='The MIT Lecense (MIT)',
      python_requires='>=3.6.0',
      url='https://github.com/SuffolkLITLab/docassemble-TylerEFSP',
      packages=find_packages(),
      namespace_packages=['docassemble'],
      install_requires=['zeep'],
      zip_safe=False,
      package_data=find_package_data(where='docassemble/TylerEFSP/', package='docassemble.TylerEFSP'),
      ) 
