# 🚀 Deploy Rashi Bot to Render

## Prerequisites
- GitHub account
- Render account (free): https://render.com
- Your Discord bot token

## 📋 Deployment Steps

### 1. Push Code to GitHub

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Discord bot ready for deployment"

# Create GitHub repo and push
git remote add origin https://github.com/YOUR_USERNAME/rashi-discord-bot.git
git branch -M main
git push -u origin main
```

### 2. Deploy on Render

#### Option A: Using render.yaml (Recommended)

1. Go to https://render.com/dashboard
2. Click **"New"** → **"Blueprint"**
3. Connect your GitHub repository
4. Select the repository with your bot code
5. Render will automatically detect `render.yaml`
6. Click **"Apply"**
7. Go to **Environment** tab and set `DISCORD_TOKEN` (copy from your .env file)
8. Click **"Manual Deploy"** → **"Deploy latest commit"**

#### Option B: Manual Setup

1. Go to https://render.com/dashboard
2. Click **"New"** → **"Web Service"**
3. Connect your GitHub repository
4. Select the repository
5. Configure:
   - **Name**: `rashi-discord-bot`
   - **Region**: Singapore (or closest to you)
   - **Branch**: `main`
   - **Runtime**: Docker
   - **Plan**: Free
6. Add Environment Variables:
   - `DISCORD_TOKEN` = (your bot token from .env)
   - `GEMINI_API_KEY` = `AIzaSyBr4wdDxpDf7IdNB5XC0YXWNBJ7T34m6K4`
   - `FIREBASE_API_KEY` = `AIzaSyBJQCqOevVzb39IlywpjEpHlnA7FJ8s8ck`
7. Click **"Create Web Service"**

### 3. Verify Deployment

1. Check the **"Logs"** tab on Render
2. Look for: `Bot is ready to respond to messages!`
3. Your bot should show as **ONLINE** in Discord

## 🔧 Environment Variables on Render

Go to your service → **Environment** tab:

```
DISCORD_TOKEN = (paste from .env file)
GEMINI_API_KEY = AIzaSyBr4wdDxpDf7IdNB5XC0YXWNBJ7T34m6K4
FIREBASE_API_KEY = AIzaSyBJQCqOevVzb39IlywpjEpHlnA7FJ8s8ck
PYTHONUNBUFFERED = 1
```

## 📝 Important Notes

### Free Tier Limitations
- **Render Free Plan**:
  - Service spins down after 15 minutes of inactivity
  - Takes ~30 seconds to wake up on first message
  - 750 hours/month free (enough for 24/7 if only one service)

### Keep Bot Alive (Optional)
If you want 24/7 uptime on free tier:
- Upgrade to Render Starter plan ($7/month)
- Or use a service like UptimeRobot to ping your bot every 10 minutes

### Auto-Deploy
- Render automatically deploys when you push to `main` branch
- Check logs after each deployment

## 🐛 Troubleshooting

### Bot Not Coming Online
1. Check Render logs for errors
2. Verify `DISCORD_TOKEN` is set correctly
3. Make sure privileged intents are enabled in Discord Developer Portal

### "Application error" in Logs
1. Check all environment variables are set
2. Verify requirements.txt has all dependencies
3. Check Dockerfile builds successfully locally:
   ```bash
   docker build -t rashi-bot .
   docker run --env-file .env rashi-bot
   ```

### Deployment Failed
1. Check GitHub repo has all files
2. Verify Dockerfile syntax
3. Check requirements.txt is valid

## 🔄 Update Bot

```bash
# Make changes to code
git add .
git commit -m "Update bot features"
git push

# Render auto-deploys the changes
# Check logs to verify successful deployment
```

## 💰 Cost Comparison

| Platform | Free Tier | Paid (24/7) |
|----------|-----------|-------------|
| **Render** | 750hrs/month (sleeps after 15min) | $7/month |
| **Railway** | $5 credit/month | $5-10/month |
| **Fly.io** | 3 VMs free (limited) | $5-10/month |
| **Heroku** | No free tier | $7/month |

**Recommendation**: Start with Render free tier, upgrade if you need 24/7 uptime.

## ✅ Success Checklist

- [ ] Code pushed to GitHub
- [ ] Render service created
- [ ] Environment variables set (especially DISCORD_TOKEN)
- [ ] Bot shows as ONLINE in Discord
- [ ] `/chat` command works
- [ ] Bot responds to mentions

---

**Need Help?**
- Render Docs: https://render.com/docs
- Discord.py Docs: https://discordpy.readthedocs.io
- Check bot logs on Render dashboard
