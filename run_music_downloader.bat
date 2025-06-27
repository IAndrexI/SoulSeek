@echo off
REM Change directory to script location (update path accordingly)
cd /d E:\Soulseekdownloadscript

REM Run Python script minimized and wait for it to finish
start /min "" python music_downloader_gui.py

REM Exit the batch script immediately (doesn't wait for Python)
exit
