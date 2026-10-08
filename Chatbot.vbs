Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\HP\Desktop\chatbot"
WshShell.Run "cmd /c launch_chatbot.bat", 0, False
