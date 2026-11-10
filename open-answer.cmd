@echo off
if exist "%~dp0latest-answer.txt" (
    start "" notepad.exe "%~dp0latest-answer.txt"
) else (
    echo No answer saved yet. Press F9 while a question is visible, then wait for the response.
    pause
)
