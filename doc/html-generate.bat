@ECHO ON 

call "%userprofile%\AppData\Local\Continuum\Anaconda2\Scripts\activate.bat"

del /Q /S _temp html rst
sphinx-apidoc -F -d 3 .. -o .
sphinx-build -b html . ../public

pause