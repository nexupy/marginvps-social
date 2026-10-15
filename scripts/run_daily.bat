@echo off
cd /d "%~dp0.."
if not exist logs mkdir logs
"C:\Users\Lab\AppData\Local\Programs\Python\Python312\python.exe" scripts\daily_post.py >> logs\post_log.txt 2>&1
