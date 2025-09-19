#!/bin/bash
launchctl unload ~/Library/LaunchAgents/com.user.localbrain.plist
sleep 2
launchctl load ~/Library/LaunchAgents/com.user.localbrain.plist
echo "Сервер local_brain перезапущено."