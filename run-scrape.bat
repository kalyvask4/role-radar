@echo off
REM Role Radar - Weekly Scheduled Job Scrape + Email
REM Runs every Sunday at 9:00 AM via Windows Task Scheduler

cd /d "C:\Users\alexa\OneDrive\Documents\GSB\claude\role-radar"

echo [%date% %time%] Starting Role Radar weekly scrape... >> scrape.log
role-radar run "Alex_Kalyvas_Resume.pdf" --send >> scrape.log 2>&1
echo [%date% %time%] Weekly scrape complete. >> scrape.log
