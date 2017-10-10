@ECHO ON 

call "%userprofile%\AppData\Local\Continuum\Anaconda2\Scripts\activate.bat"

del /Q /S _temp html rst
sphinx-apidoc -F .. -o .
sphinx-build -b html . ../public

pause