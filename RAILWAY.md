# Railway Deployment Guide

This guide covers deploying the CBF Borderô Robot to Railway.

## Prerequisites

- Railway account (https://railway.app)
- GitHub repository
- Environment variables ready (see `.env.example`)

## Architecture on Railway

The application uses a **single service** that serves both the API and the frontend:

```
Railway Service (Web)
├── Backend: FastAPI (port $PORT)
└── Frontend: React (served by FastAPI from /frontend/dist)
```

For automated scraping, you can add an optional **Worker Service**.

## Quick Start

### 1. Create New Project

1. Go to https://railway.app/new
2. Click "Deploy from GitHub repo"
3. Select your `robo_bordero` repository
4. Railway will automatically detect the Dockerfile

### 2. Configure Environment Variables

In the Railway dashboard, add these variables:

#### Required
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key-here
```

#### Optional
```
ADMIN_PASSWORD=your-secure-password
CORS_ORIGINS=*
CBF_COMPETITIONS=142,424,242
```

**Important**: Railway automatically provides a `PORT` variable - don't set it manually.

### 3. Deploy

1. Click "Deploy"
2. Railway will:
   - Build the Docker image (multi-stage: frontend + backend)
   - Install frontend dependencies
   - Build React frontend to `/frontend/dist`
   - Install Python dependencies
   - Start the FastAPI server
3. Wait for deployment to complete (~5-10 minutes)

### 4. Access Your Application

Railway will provide a public URL like:
```
https://your-app-name.up.railway.app
```

- **Frontend**: https://your-app-name.up.railway.app
- **API Docs**: https://your-app-name.up.railway.app/docs
- **Health Check**: https://your-app-name.up.railway.app/health

## Adding Worker Service (Optional)

For automated daily PDF scraping:

### 1. Add New Service

1. In your Railway project, click "New Service"
2. Select "GitHub Repo" and choose the same repository
3. Railway will create a second service

### 2. Override Start Command

In the new service settings:
- Go to "Settings" → "Deploy"
- Set **Start Command**: `python -m src.cloud_worker`
- This service doesn't need a public URL

### 3. Set Environment Variables

Add the same environment variables as the main service, plus:
```
RUN_ONCE=false
```

### 4. Deploy

The worker will run continuously and execute scraping jobs daily at 2 AM UTC.

## Configuration Files

### railway.json
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "uvicorn src.api.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### Dockerfile
The multi-stage Dockerfile:
1. **Stage 1**: Builds React frontend
2. **Stage 2**: Copies frontend build + sets up Python backend

## Railway-Specific Features

### Port Binding
Railway provides `$PORT` environment variable. The app binds to this automatically:
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
```

### Health Checks
Railway pings `/health` every 30 seconds to ensure the service is running.

### Automatic HTTPS
Railway provides automatic HTTPS certificates for your domain.

### Zero-Downtime Deploys
Railway performs rolling deploys to avoid downtime.

### Logs
View logs in the Railway dashboard:
- Click on your service
- Go to "Logs" tab
- Real-time streaming available

## Custom Domain (Optional)

### 1. Add Domain
1. Go to service "Settings" → "Domains"
2. Click "Custom Domain"
3. Enter your domain (e.g., `cbf-bordero.yourdomain.com`)

### 2. Configure DNS
Add a CNAME record:
```
cbf-bordero.yourdomain.com → your-app.up.railway.app
```

### 3. Update CORS
Update the `CORS_ORIGINS` environment variable:
```
CORS_ORIGINS=https://cbf-bordero.yourdomain.com
```

## Monitoring

### Built-in Metrics
Railway provides:
- CPU usage
- Memory usage
- Network bandwidth
- Request count
- Response time

Access via "Metrics" tab in the dashboard.

### Custom Monitoring

Add external monitoring for `/health`:
```bash
curl https://your-app.up.railway.app/health
```

Recommended services:
- UptimeRobot (free)
- Pingdom
- StatusCake

## Troubleshooting

### Build Fails

**Check Node.js version:**
```dockerfile
# In Dockerfile, ensure Node.js 18+
FROM node:18-alpine AS frontend-builder
```

**Check build logs:**
- Railway dashboard → Click on deployment → View logs
- Look for errors in frontend build or Python install

### Frontend Not Loading

**Verify frontend was built:**
```bash
# In Railway shell (Settings → Service → Shell)
ls -la /app/frontend/dist/
```

Should contain:
- `index.html`
- `assets/` directory

**Check health endpoint:**
```bash
curl https://your-app.up.railway.app/health
```

Should return:
```json
{
  "status": "healthy",
  "database": "connected",
  "frontend": "available"
}
```

If `"frontend": "not_built"`, rebuild the service.

### Database Connection Issues

**Verify Supabase credentials:**
```bash
# In Railway shell
env | grep SUPABASE
```

**Test connection:**
```bash
curl https://your-app.up.railway.app/health
```

If `"database": "error"`, check:
1. Supabase project is active
2. Service role key is correct
3. Network connectivity

### Worker Not Running

**Check worker service logs:**
- Railway dashboard → Worker service → Logs
- Look for errors or exceptions

**Verify environment variables:**
- Worker service needs same variables as main service
- Check `ANTHROPIC_API_KEY` is set

**Test manually:**
```bash
# In worker service shell
python -m src.cloud_worker
```

### Port Binding Issues

Railway automatically sets `$PORT`. Don't override it.

**If seeing "Address already in use":**
- Ensure only one service per project
- Check start command uses `$PORT`
- Restart the service

## Scaling

### Horizontal Scaling
Railway allows multiple replicas:
1. Go to "Settings" → "Scaling"
2. Increase replica count
3. Railway load-balances automatically

**Note**: For stateless API, this works great. For worker, keep at 1 replica.

### Vertical Scaling
Upgrade Railway plan for more resources:
- Starter: $5/month (512MB RAM, 1 vCPU)
- Pro: $20/month (8GB RAM, 8 vCPU)
- Team: Custom pricing

### Database Scaling
Supabase handles database scaling:
- Free tier: 500MB database
- Pro tier: 8GB database (auto-scales)

## Cost Estimation

### Railway Costs
- **Free Trial**: $5 credit
- **Hobby Plan**: $5/month
- **Usage-based**: ~$0.000463/GB-hour

**Estimated monthly cost:**
- Single service: $5-10/month
- With worker: $10-15/month

### Supabase Costs
- **Free Tier**: Up to 500MB database, 1GB storage
- **Pro Tier**: $25/month (8GB database, 100GB storage)

### Anthropic API Costs
- **Claude Haiku**: ~$0.25 per 1M input tokens, $1.25 per 1M output tokens
- **Estimated**: $10-50/month depending on volume

**Total**: ~$20-90/month for full production deployment

## Best Practices

### 1. Environment Variables
- Never commit `.env` to git
- Use Railway's encrypted variables
- Rotate API keys periodically

### 2. Monitoring
- Set up uptime monitoring
- Check logs regularly
- Monitor Supabase usage

### 3. Backups
- Supabase provides automatic backups
- Enable PITR (Point-in-Time Recovery) for production
- Export data periodically

### 4. Security
- Change default admin password
- Use strong Supabase service key
- Enable RLS policies in Supabase
- Keep dependencies updated

### 5. Performance
- Enable CDN for static assets
- Use Railway metrics to monitor
- Optimize database queries
- Cache API responses (TanStack Query handles this)

## CI/CD

Railway automatically deploys on git push:

1. **Push to GitHub**:
   ```bash
   git push origin main
   ```

2. **Railway detects changes** and:
   - Pulls latest code
   - Rebuilds Docker image
   - Deploys with zero downtime
   - Runs health checks

3. **Rollback if needed**:
   - Railway dashboard → Deployments
   - Click on previous deployment
   - "Redeploy"

## Support

### Railway Support
- Documentation: https://docs.railway.app
- Discord: https://discord.gg/railway
- Email: team@railway.app

### Application Issues
- Check logs first: Railway dashboard → Logs
- Review health endpoint: `/health`
- Test API: `/docs`

## Quick Commands

```bash
# View logs
railway logs

# Open shell
railway shell

# Link project
railway link

# Deploy manually
railway up

# View environment variables
railway variables

# Add variable
railway variables set KEY=value
```

## Summary

✅ Single-service deployment (frontend + backend)
✅ Optional worker service for automation
✅ Automatic HTTPS and custom domains
✅ Built-in monitoring and metrics
✅ Zero-downtime deploys
✅ Auto-scaling capabilities
✅ Simple environment variable management

Your CBF Borderô Robot is now running on Railway! 🚀
