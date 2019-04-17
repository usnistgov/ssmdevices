@ECHO ON 

call "%userprofile%\AppData\Local\Continuum\Anaconda2\Scripts\activate.bat"

del /Q /S _build _static _templates *.rst
sphinx-apidoc -F -d 5 .. -o .
sphinx-build -b html . ../public

pause