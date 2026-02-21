#!/bin/bash
# Start Rashi Bot

cd /home/aditya/Documents/discord-bot
source venv/bin/activate
nohup python rashi.py > bot.log 2>&1 &

echo "🚀 Bot starting..."
sleep 3

# Check if bot is running
if pgrep -f "python rashi.py" > /dev/null; then
    echo "✅ Rashi is ONLINE!"
    echo "📋 Bot process ID: $(pgrep -f 'python rashi.py')"
    echo "📄 View logs: tail -f bot.log"
else
    echo "❌ Failed to start bot"
    echo "Check bot.log for errors"
fi
