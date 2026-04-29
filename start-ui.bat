@echo off
REM Role Radar - Start Flask UI
REM Runs on logon via Windows Task Scheduler

cd /d "C:\Users\alexa\OneDrive\Documents\GSB\claude\role-radar"
role-radar ui --port 5000
