#!/usr/bin/env python

'''
Installation instructions
=========================================================================================================================================
- Install git for windows (recent version?):		https://git-scm.com/download/win
- Install tortoisegit (version>2.0): 			https://tortoisegit.org/download/
- Install anaconda python 4.1.1 (64 bit python 2.7):	https://www.continuum.io/downloads
- Install acroname brainstem development kit v2.3.0	https://acroname.com/software/brainstem-development-kit-ms-windows-ms-windows
  Extract the folders into a convenient location on your computer.
  Open a command prompt, and use cd to enter the root of the extracted folder.
  Use pip to install the python drivers for the acroname brainstem by typing
  
  ::

      pip install development\\python\\brainstem-2.3.0-py2-none-any.whl

  on a command line.
  
- Install the minicircuits driver mcl_RUDAT64.dll		http://www.minicircuits.com/support/software_download.html
	- Copy mcl_RUDAT64.dll out of the zipfile into C:\windows\syswow64
- Use tortoisegit to clone the source code 
	- Right click in a windows explorer window where you want to clone the source directory, and click "Clone..."
	- For the repository url enter
	  \\cfs2w.nist.gov\67Internal\DivisionProjects\NASCTN_GPS\gpslte
	- Click OK
- Set the testbed computer IP address
	- Fixed IP address... 10.0.0.240 should work
- Run the installer script in the code repository to install the remaining python package dependencies
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
    from distutils.core import setup
    import setuptools
    
    setup(name='remotelets_drivers',
          version='0.0.1',
          description='instrument automation drivers',
          author='Dan Kuester',
          author_email='daniel.kuester@nist.gov',
          url='',
          packages=setuptools.find_packages(),
          license='NIST',
          install_requires=[
                    'remotelets',
                    'pandas(>=0.19.0)',
                    'pyserial',
                    'pyvisa(>=1.8)',
                    'ipywidgets',
                    'notebook',
                    'sphinx',
                    ]
         )