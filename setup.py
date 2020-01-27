#!/usr/bin/env python

'''
Getting started
=========================================================================================================================================
- Installation instructions are hosted at https://gitlab.nist.gov/gitlab/ssm/ssmdevices#installation
'''

"""
.. This software was developed by employees of the National Institute of
.. Standards and Technology (NIST), an agency of the Federal Government. Pursuant
.. to title 17 United States Code Section 105, works of NIST employees are not
.. subject to copyright protection in the United States and are considered to be
.. in the public domain. Permission to freely use, copy, modify, and distribute
.. this software and its documentation without fee is hereby granted, provided
.. that this notice and disclaimer of warranty appears in all copies.

.. THE SOFTWARE IS PROVIDED 'AS IS' WITHOUT ANY WARRANTY OF ANY KIND, EITHER
.. EXPRESSED, IMPLIED, OR STATUTORY, INCLUDING, BUT NOT LIMITED TO, ANY WARRANTY
.. THAT THE SOFTWARE WILL CONFORM TO SPECIFICATIONS, ANY IMPLIED WARRANTIES OF
.. MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND FREEDOM FROM INFRINGEMENT,
.. AND ANY WARRANTY THAT THE DOCUMENTATION WILL CONFORM TO THE SOFTWARE, OR ANY
.. WARRANTY THAT THE SOFTWARE WILL BE ERROR FREE. IN NO EVENT SHALL NASA BE LIABLE
.. FOR ANY DAMAGES, INCLUDING, BUT NOT LIMITED TO, DIRECT, INDIRECT, SPECIAL OR
.. CONSEQUENTIAL DAMAGES, ARISING OUT OF, RESULTING FROM, OR IN ANY WAY CONNECTED
.. WITH THIS SOFTWARE, WHETHER OR NOT BASED UPON WARRANTY, CONTRACT, TORT, OR
.. OTHERWISE, WHETHER OR NOT INJURY WAS SUSTAINED BY PERSONS OR PROPERTY OR
.. OTHERWISE, AND WHETHER OR NOT LOSS WAS SUSTAINED FROM, OR AROSE OUT OF THE
.. RESULTS OF, OR USE OF, THE SOFTWARE OR SERVICES PROVIDED HEREUNDER.

.. Distributions of NIST software should also include copyright and licensing
.. statements of any third-party software that are legally bundled with the code
.. in compliance with the conditions of those licenses.
"""

if __name__ == '__main__':
    import sys

    if '..' not in sys.path:
        sys.path.insert(0, '..')
    from glob import glob

    from distutils.core import setup
    import setuptools,os,sys,shutil

    dist = setup(name='ssmdevices',
                  version='0.7',
                  description='instrument automation drivers',
                  author='Dan Kuester',
                  author_email='daniel.kuester@nist.gov',
                  url='https://gitlab.nist.gov/gitlab/ssm/ssmdevices',
                  packages=setuptools.find_packages(),
                  package_data={'ssmdevices': ['*.pyi', '*/*.pyi', '*/*/*.pyi']},
                  include_package_data=True,
                  license='NIST',
                  install_requires=[
              		    	'labbench(>=0.20)',
                            'pandas(>=0.19.0)',
                            'pyminicircuits',
                            'pyserial(>3.0)',
                            'pyvisa(>=1.8)',
                            'ipywidgets',
                            'notebook',
                            'sphinx',
                            'hidapi',
                            ],
                  zip_safe=False,
                 )

    # Find and install binaries
    def listbinaries(path):
        def isbin(p):
            return not os.path.isdir(p) and not p.lower().endswith('.py')
        
        return [p for p in setuptools.findall(path) if isbin(p)]
    
    def find_scripts_dir():
        candidates = [p for p in os.environ['PATH'].split(';') if p.lower().endswith('scripts')]
        for c in candidates:
            py_guess = os.path.join(os.path.split(c)[0], 'python.exe')
            if os.path.exists(py_guess):
                return c
        raise ValueError('could not guess python distribution scripts path :(')
        
    
    scripts = listbinaries(r'ssmdevices\lib')
    sys.stderr.write('installing to PATH:\n'+'\n'.join(scripts))
    scripts_dir = find_scripts_dir()
    
    for s in scripts:
        to = os.path.join(scripts_dir, os.path.basename(s))
        print('copy {} to {}'.format(s,to))
        shutil.copyfile(s, to)