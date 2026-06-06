@echo off
echo Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo Building FormCreator.exe...
pyinstaller --onefile --windowed --name FormCreator ^
  --add-data "templates;templates" ^
  --add-data "assets;assets" ^
  --hidden-import webview.platforms.winforms ^
  app.py

echo.
echo Done! Your exe is in the dist\ folder.
echo Copy dist\FormCreator.exe and your forms\ folder to the target machine.
pause
