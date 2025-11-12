# Railway Scraper Service Configuration

## Overview

The `cbf-scraper-daily` service is a **worker service** (not a web service) that runs scheduled PDF scraping jobs. It does NOT serve HTTP traffic and does NOT need a PORT.

## Service Configuration in Railway

### 1. Create New Service

1. In your Railway project, click **"New Service"**
2. Select **"GitHub Repo"** and choose your repository
3. Name it: `cbf-scraper-daily`

### 2. Configure Start Command

**CRITICAL**: Override the default start command in Service Settings:

1. Go to **Settings → Deploy**
2. Set **Start Command**:
   ```bash
   python -m src.cloud_worker
   ```

**DO NOT** use the default `uvicorn` command from railway.json - that's for the web service only.

### 3. Disable Healthcheck

Since this is a worker service (not a web API):

1. Go to **Settings → Deploy**
2. Set **Healthcheck Path** to empty/none
3. Or set to a custom path if you add a health endpoint to the worker

### 4. Environment Variables

Add the same environment variables as the main web service:

#### Required
```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key-here
```

#### Optional
```bash
# Competition codes to scrape (comma-separated)
CBF_COMPETITIONS=142,424,242

# Run mode: false for continuous scheduling, true for one-time run
RUN_ONCE=false

# Log level
LOG_LEVEL=INFO
```

### 5. Service Settings

- **Public URL**: NOT required (this is a background worker)
- **Restart Policy**: ON_FAILURE
- **Restart Max Retries**: 10

## How It Works

### Run Mode: Continuous (RUN_ONCE=false)

The worker runs continuously and executes scraping jobs:
- **Schedule**: Daily at 2:00 AM UTC
- **Also runs**: Once immediately on startup

```python
# src/cloud_worker.py
schedule.every().day.at("02:00").do(run_scheduled_job)
```

### Run Mode: One-Time (RUN_ONCE=true)

The worker executes a single scraping job and exits:
- Useful for manual/cron-triggered runs
- Exit code 0 = success
- Exit code 1 = errors occurred

## Scraping Process

The worker performs these steps:

1. **Download PDFs** from CBF for configured competitions
2. **Upload PDFs** to Supabase Storage
3. **Analyze PDFs** with Claude AI
4. **Save results** to Supabase Database
5. **Normalize data** (team names, stadiums, etc.)
6. **Generate reports** and update analytics

## Monitoring

### View Logs

```bash
# In Railway dashboard
Service → cbf-scraper-daily → Logs
```

### Expected Log Output

```
🚀 Initializing Cloud Worker
📊 Starting scrape and process job for 2025
⬇️  Downloading PDFs: year=2025, competition=142
✅ Downloaded 15 PDFs
🔄 Processing PDF: 12345
✅ Successfully processed: 12345
📈 Job completed: pdfs_downloaded=45, pdfs_processed=42, errors=0
```

### Error Handling

The worker logs errors but continues processing:
- Individual PDF failures don't stop the entire job
- Job exits with code 1 if any errors occurred
- Check logs for specific error messages

## Common Issues

### Issue 1: Port Binding Error

**Symptom**:
```
Error: Invalid value for '--port': '$PORT' is not a valid integer.
```

**Cause**: Using the wrong start command (uvicorn instead of worker)

**Solution**:
- Override start command: `python -m src.cloud_worker`
- Remove/disable healthcheck

### Issue 2: API Key Missing

**Symptom**:
```
ValueError: ANTHROPIC_API_KEY not found in environment
```

**Solution**:
- Add `ANTHROPIC_API_KEY` to service environment variables
- Restart service

### Issue 3: Database Connection Failed

**Symptom**:
```
Error: Failed to connect to Supabase
```

**Solution**:
- Verify `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`
- Check Supabase project is active
- Test connection from main web service

### Issue 4: Worker Exits Immediately

**Symptom**: Service shows "Crashed" status

**Cause**: Python module import error or missing dependencies

**Solution**:
1. Check build logs for errors
2. Verify Dockerfile builds correctly
3. Ensure all dependencies in requirements.txt
4. Test locally: `python -m src.cloud_worker`

## Testing Locally

### Test Worker Locally

```bash
# Set environment variables
export ANTHROPIC_API_KEY=sk-ant-...
export SUPABASE_URL=https://...
export SUPABASE_SERVICE_KEY=...

# Run once
export RUN_ONCE=true
python -m src.cloud_worker

# Run continuously (Ctrl+C to stop)
export RUN_ONCE=false
python -m src.cloud_worker
```

### Test Specific Function

```python
from src.cloud_worker import CloudWorker

# Initialize
worker = CloudWorker()

# Run job
stats = worker.scrape_and_process(year=2025)
print(stats)

# Health check
healthy = worker.health_check()
print(f"Healthy: {healthy}")
```

## Resource Usage

Expected resource usage:
- **Memory**: 200-400 MB
- **CPU**: Spikes during PDF processing, low during idle
- **Network**: Moderate (downloading PDFs, API calls)
- **Storage**: Temporary (uses temp directories)

## Scheduling Alternatives

### Option 1: Railway Cron (Recommended)

Use Railway's cron feature (if available):
1. Set `RUN_ONCE=true`
2. Configure cron schedule in Railway
3. Worker runs and exits each time

### Option 2: External Cron

Use an external service (GitHub Actions, Render Cron, etc.):
1. Set `RUN_ONCE=true`
2. Call: `railway run python -m src.cloud_worker`
3. Schedule via external service

### Option 3: Continuous (Current Setup)

Worker runs 24/7 with internal scheduling:
- Uses `schedule` library
- Runs at 2:00 AM UTC daily
- Always running, uses minimal resources when idle

## Deployment Checklist

- [ ] Create new Railway service
- [ ] Set start command: `python -m src.cloud_worker`
- [ ] Disable healthcheck or set custom path
- [ ] Add all required environment variables
- [ ] Set `RUN_ONCE=false` for continuous mode
- [ ] Verify service builds successfully
- [ ] Check logs for successful initialization
- [ ] Wait for first scheduled run (or trigger manually)
- [ ] Verify PDFs appear in Supabase Storage
- [ ] Verify matches appear in database

## Architecture Diagram

```
Railway Project
├── cbf-dashboard (Web Service)
│   ├── Port: $PORT (provided by Railway)
│   ├── Start: uvicorn src.api.main:app
│   ├── Healthcheck: /health
│   └── Serves: Frontend + API
│
└── cbf-scraper-daily (Worker Service)
    ├── Port: NONE (no web server)
    ├── Start: python -m src.cloud_worker
    ├── Healthcheck: NONE
    └── Job: Daily PDF scraping at 2 AM UTC
```

## Summary

✅ Worker service, NOT a web service
✅ Start command: `python -m src.cloud_worker`
✅ NO PORT required
✅ NO healthcheck needed
✅ Runs scheduled jobs (daily at 2 AM UTC)
✅ Same environment variables as web service
✅ Logs visible in Railway dashboard

Your scraper worker is now configured correctly! 🎉
