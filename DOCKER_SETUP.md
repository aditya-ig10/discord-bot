# 🐳 Docker Setup for Rashi Bot

## Local Docker Deployment

### Prerequisites
- Docker installed: https://docs.docker.com/get-docker/
- Docker Compose (usually included with Docker Desktop)

### Quick Start

#### Option 1: Using Docker Compose (Recommended)

```bash
# 1. Make sure .env file exists with DISCORD_TOKEN
cat .env

# 2. Build and run with Docker Compose
docker-compose up -d

# 3. Check logs
docker-compose logs -f

# 4. Stop bot
docker-compose down
```

#### Option 2: Using Docker Commands

```bash
# 1. Build the image
docker build -t rashi-bot .

# 2. Run the container
docker run -d \
  --name rashi-discord-bot \
  --env-file .env \
  --restart unless-stopped \
  rashi-bot

# 3. Check logs
docker logs -f rashi-discord-bot

# 4. Stop bot
docker stop rashi-discord-bot
docker rm rashi-discord-bot
```

## Useful Commands

### View Logs
```bash
# With docker-compose
docker-compose logs -f

# With docker
docker logs -f rashi-discord-bot

# Last 50 lines
docker logs --tail 50 rashi-discord-bot
```

### Restart Bot
```bash
# With docker-compose
docker-compose restart

# With docker
docker restart rashi-discord-bot
```

### Stop Bot
```bash
# With docker-compose
docker-compose down

# With docker
docker stop rashi-discord-bot
```

### Update Bot Code
```bash
# 1. Make code changes
# 2. Rebuild and restart
docker-compose down
docker-compose up -d --build

# Or with docker
docker stop rashi-discord-bot
docker rm rashi-discord-bot
docker build -t rashi-bot .
docker run -d --name rashi-discord-bot --env-file .env rashi-bot
```

### Check Container Status
```bash
docker ps
docker ps -a  # Include stopped containers
```

### Enter Container (for debugging)
```bash
# With docker-compose
docker-compose exec rashi-bot bash

# With docker
docker exec -it rashi-discord-bot bash
```

## Environment Variables

Create `.env` file with:
```
DISCORD_TOKEN=your_token_here
GEMINI_API_KEY=your_api_key_here
FIREBASE_API_KEY=your_firebase_key_here
```

## Troubleshooting

### Container Exits Immediately
```bash
# Check logs for errors
docker logs rashi-discord-bot

# Common issues:
# - Missing DISCORD_TOKEN in .env
# - Invalid token
# - Missing dependencies in requirements.txt
```

### "Cannot connect to Docker daemon"
```bash
# Make sure Docker is running
sudo systemctl start docker  # Linux
# Or start Docker Desktop on Windows/Mac
```

### Port Conflicts (if any)
```bash
# Check what's using the port
docker ps
sudo netstat -tulpn | grep <port>

# Stop conflicting container
docker stop <container_name>
```

## Production Tips

### Auto-restart on System Reboot
The `--restart unless-stopped` flag ensures the bot restarts automatically.

### View Resource Usage
```bash
docker stats rashi-discord-bot
```

### Clean Up Old Images
```bash
# Remove unused images
docker image prune

# Remove all unused data
docker system prune -a
```

## File Structure
```
discord-bot/
├── Dockerfile              # Build instructions
├── docker-compose.yml      # Compose configuration
├── .dockerignore          # Files to exclude from build
├── requirements.txt       # Python dependencies
├── rashi.py              # Bot code
├── .env                  # Environment variables (not in git)
└── .env.example          # Template for .env
```

## Next Steps
- For cloud deployment, see `RENDER_DEPLOYMENT.md`
- For Railway deployment, see Railway docs
- For AWS/GCP/Azure, push image to container registry
