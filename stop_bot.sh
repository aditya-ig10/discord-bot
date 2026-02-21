#!/bin/bash
# Stop Rashi Bot

pkill -f "python rashi.py"

if [ $? -eq 0 ]; then
    echo "✅ Bot stopped"
else
    echo "⚠️  Bot was not running"
fi
