@ECHO ON 

call "%userprofile%\AppData\Local\Continuum\Anaconda2\Scripts\activate.bat"

del /Q /S _temp html rst
sphinx-apidoc -F .. -o _temp
copy conf.py _temp\conf.py
sphinx-build -b html _temp ../public
REM sphinx-build -b rst _temp rst

pause