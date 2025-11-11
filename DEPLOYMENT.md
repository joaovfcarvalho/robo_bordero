# Deployment Guide - CBF Borderô Robot

This guide covers deployment of the refactored FastAPI + React application.

## Prerequisites

- Docker (recommended) or Python 3.11+ and Node.js 18+
- Environment variables configured
- Supabase project set up
- Anthropic API key

## Environment Variables

Create a `.env` file or set these in your hosting platform:

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...

# Optional
ADMIN_PASSWORD=cbf2025admin
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
CBF_COMPETITIONS=142,424,242
RUN_ONCE=false
```

## Deployment Options

### Option 1: Docker (Recommended)

#### Using Docker Compose

```bash
# 1. Clone the repository
git clone <repository-url>
cd robo_bordero

# 2. Create .env file with required variables
cp .env.example .env
# Edit .env with your credentials

# 3. Build and run
docker-compose up -d

# 4. View logs
docker-compose logs -f

# 5. Stop
docker-compose down
```

The application will be available at:
- API: http://localhost:8000
- Frontend: http://localhost:8000 (served by FastAPI)
- API Docs: http://localhost:8000/docs

#### Using Docker Only

```bash
# Build
docker build -t cbf-bordero .

# Run
docker run -d \
  --name cbf-bordero \
  -p 8000:8000 \
  -e ANTHROPIC_API_KEY=your_key \
  -e SUPABASE_URL=your_url \
  -e SUPABASE_SERVICE_KEY=your_key \
  -e ADMIN_PASSWORD=your_password \
  cbf-bordero

# View logs
docker logs -f cbf-bordero

# Stop
docker stop cbf-bordero
docker rm cbf-bordero
```

### Option 2: Railway

Railway is the recommended cloud platform for this application.

#### Steps:

1. **Fork or push the repository to GitHub**

2. **Create a new Railway project**
   - Go to https://railway.app
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

3. **Set environment variables**
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   SUPABASE_URL=https://xxxxx.supabase.co
   SUPABASE_SERVICE_KEY=eyJ...
   ADMIN_PASSWORD=your_secure_password
   CORS_ORIGINS=https://your-app.railway.app
   ```

4. **Deploy**
   - Railway will automatically detect the Dockerfile
   - The build will start automatically
   - Wait for deployment to complete

5. **Access your app**
   - Railway will provide a public URL
   - Frontend: https://your-app.railway.app
   - API Docs: https://your-app.railway.app/docs

#### Railway Configuration

The `railway.json` file is pre-configured:

```json
{
  "build": {
    "builder": "DOCKERFILE"
  },
  "deploy": {
    "startCommand": "uvicorn src.api.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "restartPolicyType": "ON_FAILURE"
  }
}
```

#### Adding the Worker Service

For automated PDF processing, add a second service:

1. Click "New Service" in your Railway project
2. Link to the same GitHub repository
3. Set environment variables (same as main app)
4. Override start command: `python -m src.cloud_worker`
5. This will run the background worker for scheduled scraping

### Option 3: Render

Similar to Railway, Render supports Dockerfile deployment.

1. **Create a new Web Service**
   - Go to https://render.com
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

2. **Configure the service**
   - Name: cbf-bordero
   - Environment: Docker
   - Instance Type: Free or Starter
   - Health Check Path: `/health`

3. **Set environment variables** (same as Railway)

4. **Add Background Worker** (optional)
   - Create a new Background Worker
   - Start Command: `python -m src.cloud_worker`
   - Same environment variables

### Option 4: Manual Deployment

For VPS or dedicated servers:

#### Prerequisites
```bash
# Install Python 3.11+
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# Install Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

#### Deployment Steps

```bash
# 1. Clone repository
git clone <repository-url>
cd robo_bordero

# 2. Set up Python environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Build frontend
cd frontend
npm install
npm run build
cd ..

# 4. Create .env file
cp .env.example .env
# Edit .env with your credentials

# 5. Run with systemd
sudo cp deployment/cbf-bordero.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable cbf-bordero
sudo systemctl start cbf-bordero

# 6. Check status
sudo systemctl status cbf-bordero
```

#### Systemd Service File

Create `/etc/systemd/system/cbf-bordero.service`:

```ini
[Unit]
Description=CBF Borderô Robot API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/robo_bordero
Environment="PATH=/var/www/robo_bordero/venv/bin"
EnvironmentFile=/var/www/robo_bordero/.env
ExecStart=/var/www/robo_bordero/venv/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Nginx Configuration

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Option 5: Heroku

```bash
# 1. Install Heroku CLI
# 2. Login
heroku login

# 3. Create app
heroku create cbf-bordero

# 4. Set environment variables
heroku config:set ANTHROPIC_API_KEY=your_key
heroku config:set SUPABASE_URL=your_url
heroku config:set SUPABASE_SERVICE_KEY=your_key
heroku config:set ADMIN_PASSWORD=your_password

# 5. Deploy
git push heroku main

# 6. Scale
heroku ps:scale web=1

# 7. View logs
heroku logs --tail
```

## Post-Deployment

### 1. Health Check

Visit `/health` endpoint:
```bash
curl https://your-app.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

### 2. API Documentation

Visit `/docs` for interactive API documentation (Swagger UI).

### 3. Initial Setup

1. **Login to Admin**
   - Navigate to `/admin/login`
   - Enter admin password
   - You'll be redirected to PDF Manager

2. **Start First Scrape**
   - Go to PDF Manager
   - Select year and competition
   - Click "Processar em Lote" (Bulk Scrape)

3. **Monitor Queue**
   - Queue status updates every 5 seconds
   - Check for any failed items
   - Retry failures if needed

### 4. Set Up Automated Worker (Optional)

For automatic daily scraping, deploy the worker service:

```bash
# Docker Compose (already included)
docker-compose up -d

# Or manually
python -m src.cloud_worker
```

The worker runs daily at 2 AM by default.

## Monitoring

### Logs

#### Docker
```bash
docker logs -f cbf-bordero
docker logs -f cbf-bordero-worker
```

#### Railway
- View logs in Railway dashboard
- Real-time log streaming available

#### Systemd
```bash
sudo journalctl -u cbf-bordero -f
```

### Health Checks

Set up monitoring to ping `/health` endpoint regularly:
- UptimeRobot
- Pingdom
- StatusCake

### Database

Monitor your Supabase project:
- Table row counts
- Storage usage
- API usage
- Active connections

## Troubleshooting

### Build Fails

1. Check Docker logs
2. Verify all files are committed
3. Check Node.js and Python versions
4. Ensure frontend builds successfully: `cd frontend && npm run build`

### Database Connection Issues

1. Verify Supabase credentials
2. Check network connectivity
3. Verify Supabase project is not paused
4. Check RLS policies in Supabase

### API Returns 500 Errors

1. Check application logs
2. Verify environment variables
3. Test Claude API key: `curl https://api.anthropic.com/v1/messages -H "x-api-key: $ANTHROPIC_API_KEY"`
4. Check Supabase status page

### Frontend Not Loading

1. Verify frontend was built: `ls frontend/dist/`
2. Check CORS configuration
3. Clear browser cache
4. Check browser console for errors

### Worker Not Running

1. Check if worker service is running
2. Verify environment variables
3. Check worker logs
4. Ensure no port conflicts

## Scaling

### Horizontal Scaling

The application is stateless and can be scaled horizontally:

1. **Railway**: Increase instances in dashboard
2. **Docker**: Use Docker Swarm or Kubernetes
3. **Manual**: Run multiple instances behind a load balancer

### Vertical Scaling

Increase resources:
- Railway: Upgrade plan
- Docker: Adjust resource limits
- VPS: Upgrade server specs

### Database Scaling

Supabase handles scaling automatically, but monitor:
- Connection pool size
- Query performance
- Storage usage

## Security Checklist

- [ ] Change default admin password
- [ ] Set proper CORS origins (not `*`)
- [ ] Use HTTPS in production
- [ ] Rotate API keys periodically
- [ ] Enable Supabase RLS policies
- [ ] Set up rate limiting (if needed)
- [ ] Configure firewall rules
- [ ] Enable logging and monitoring
- [ ] Regular security updates

## Backup Strategy

### Database
- Supabase provides automatic daily backups
- Enable point-in-time recovery (PITR) for production

### PDFs
- Stored in Supabase Storage
- Included in Supabase backups
- Consider additional backup to S3/GCS

### Configuration
- Keep `.env` backed up securely
- Store credentials in password manager
- Document any custom configurations

## Cost Estimation

### Free Tier (Supabase + Railway)
- Supabase: Free tier (500MB database, 1GB storage)
- Railway: $5/month with free trial
- Anthropic: Pay per use (~$0.25 per 1M tokens)

### Production (Estimated)
- Railway/Render: $20-50/month
- Supabase Pro: $25/month
- Anthropic API: $10-100/month (depending on volume)

**Total**: ~$55-175/month for production deployment

## Support

For deployment issues:
1. Check logs first
2. Review this guide
3. Check API documentation at `/docs`
4. Open GitHub issue if problem persists
