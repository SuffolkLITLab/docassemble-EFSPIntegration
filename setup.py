import os
import sys
from setuptools import setup, find_packages
from fnmatch import fnmatchcase
from distutils.util import convert_path

standard_exclude = ('*.pyc', '*~', '.*', '*.bak', '*.swp*')
standard_exclude_directories = ('.*', 'CVS', '_darcs', './build', './dist', 'EGG-INFO', '*.egg-info')
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
                    if (fnmatchcase(name, pattern)
                        or fn.lower() == pattern.lower()):
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
                    if (fnmatchcase(name, pattern)
                        or fn.lower() == pattern.lower()):
                        bad_name = True
                        break
                if bad_name:
                    continue
                out.setdefault(package, []).append(prefix+name)
    return out

setup(name='docassemble.EFSPIntegration',
      version='0.2.0',
      description=(''),
      long_description='# docassemble-EFSPIntegration\r\n\r\nA docassemble extension that talks to [a proxy e-filing server](https://github.com/SuffolkLITLab/EfileProxyServer/) easily within a docassemble interview.\r\n\r\nMain interviews of import:\r\n\r\n* any_filing_interview.yml: allows you to make any type of filing, initial or subsequent\r\n* admin_interview.yml: lets you handle admin / user functionality, outside of the context of cases and filings\r\n\r\nIn progress!\r\n\r\n## Authors\r\n\r\nQuinten Steenhuis (qsteenhuis@suffolk.edu)\r\nBryce Willey (bwilley@suffolk.edu)\r\n',
      long_description_content_type='text/markdown',
      author='Bryce Willey',
      author_email='bwilley@suffolk.edu',
      license='The MIT License (MIT)',
      url='https://github.com/SuffolkLITLab/docassemble-EFSPIntegration',
      packages=find_packages(),
      namespace_packages=['docassemble'],
      install_requires=['docassemble.AssemblyLine>=2.4.1', 'requests>=2.25.1'],
      zip_safe=False,
      package_data=find_package_data(where='docassemble/EFSPIntegration/', package='docassemble.EFSPIntegration'),
     )

