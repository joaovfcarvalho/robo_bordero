# CBF Robot - Cost Breakdown & Optimization

## 💰 Expected Monthly Costs

### Cloud Infrastructure

| Service | Cost | Usage |
|---------|------|-------|
| **Railway Dashboard** | $3-5/month | Always-on Streamlit web app |
| **Railway Worker** | $1-2/month | Runs ~1 hour/day (30 hours/month) |
| **Supabase Free Tier** | $0 | 500MB database + 1GB storage |
| **Claude Haiku 4.5 API** | $5-15/month | See breakdown below |
| **Total** | **$9-22/month** | Varies by PDF volume |

---

## 🤖 Claude API Cost Breakdown

### Claude Haiku 4.5 Pricing (as of 2025)
- **Input**: $0.80 per million tokens
- **Output**: $4.00 per million tokens

### Typical PDF Processing:
- **Input tokens**: ~2,000-3,000 per PDF (image analysis)
- **Output tokens**: ~500-800 per PDF (structured JSON)
- **Cost per PDF**: ~$0.008-0.015 (less than 2 cents!)

### Monthly Estimates:

| Scenario | PDFs/Day | PDFs/Month | Claude API Cost |
|----------|----------|------------|-----------------|
| **Low volume** | 5 new PDFs | 150 | ~$1.50/month |
| **Medium volume** | 20 new PDFs | 600 | ~$6.00/month |
| **High volume** | 50 new PDFs | 1,500 | ~$15.00/month |

---

## ✅ Cost-Saving Features (Already Implemented!)

### 1. **Database Deduplication** ✅

**Location**: `src/cloud_worker.py:124-127`

```python
# Check if already processed
if self.db.match_exists(id_jogo_cbf):
    logger.debug(f"Skipping already processed: {id_jogo_cbf}")
    stats["pdfs_skipped"] += 1
    continue  # ← Skips Claude API call entirely!
```

**Benefit**: If a PDF was already processed and is in the database, the worker **completely skips it** - no Claude API call, no cost!

---

### 2. **Storage Deduplication** ✅

**Location**: `src/storage.py:82-92`

```python
# Check if file already exists
if not overwrite:
    try:
        existing = self.storage.from_(BUCKET_PDF).list(path=str(year))
        existing_files = [f["name"] for f in existing]
        if f"{id_jogo_cbf}.pdf" in existing_files:
            logger.debug(f"PDF already exists in storage: {storage_path}")
            return storage_path  # ← Skips upload!
    except Exception:
        pass
```

**Benefit**: If a PDF is already in Supabase Storage, it **skips re-uploading** - saves bandwidth and time!

---

### 3. **Only New PDFs Downloaded**

**Location**: `src/scraper.py` (CBF scraper module)

The scraper only downloads PDFs that don't already exist locally. Combined with the database check above, this ensures:
- ✅ Download only new PDFs from CBF website
- ✅ Check database before processing
- ✅ Skip Claude API call if already processed
- ✅ Skip storage upload if already exists

---

## 📊 Real-World Cost Example

Let's say you're tracking **Brasileiro Série A** (38 rounds, ~10 matches per round):

### Initial Setup (First Run):
- **Total matches**: ~380 matches
- **Claude API calls**: 380 (all new)
- **Cost**: 380 × $0.01 = **~$3.80 one-time**

### Ongoing (Daily Runs):
- **New matches per day**: 2-5 (only on match days)
- **Claude API calls per day**: 2-5
- **Daily cost**: $0.02-0.05
- **Monthly cost**: ~$0.60-1.50

### Re-running the Worker:
- **Second run on same data**: $0 (all skipped!)
- **Third run**: $0 (all skipped!)
- **Only new matches cost money** ✅

---

## 🧪 Testing Before Full Deployment

### Manual Test Script (Provided)

Run `test_manual_run.py` locally to test with just 3 PDFs:

```bash
# Test with 3 PDFs from Brasileiro 2025
python test_manual_run.py --year 2025 --competition 142 --max-pdfs 3

# Expected output:
# PDFs downloaded:              3
# PDFs skipped (in DB):         0
# PDFs processed successfully:  3
# Claude API calls made:        3
# Estimated cost: $0.03 USD
```

### Test in Railway (Cloud):

1. Go to Railway → Your worker service
2. Set environment variable:
   ```
   CBF_COMPETITIONS=142
   RUN_ONCE=true
   ```
3. Click "Restart" to trigger manual run
4. Check logs to see:
   - How many PDFs downloaded
   - How many skipped (already in DB)
   - How many Claude API calls made

---

## 🛡️ Cost Protection Strategies

### Strategy 1: Rate Limiting ✅ (Built-in)

**Location**: `src/claude.py:39-40`

```python
self.requests_per_minute = 50
```

The Claude client has built-in rate limiting to prevent runaway API usage.

### Strategy 2: Manual Upload First

Instead of automated daily runs, you can:

1. **Upload existing PDFs manually** to Supabase Storage (no Claude cost)
2. **Run worker once** - it will see PDFs in storage but not in DB
3. **Worker processes** only what's needed
4. **Monitor costs** before enabling daily automation

### Strategy 3: Competition Filtering

Control which competitions to process via environment variable:

```bash
# Only track Brasileiro Série A (fewer matches)
CBF_COMPETITIONS=142

# Track multiple competitions
CBF_COMPETITIONS=142,424,242
```

---

## 📈 Cost Monitoring

### Check Claude API Usage:
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Click "Usage" → "API Usage"
3. See daily/monthly token usage and costs

### Check Railway Costs:
1. Go to Railway dashboard
2. Click "Usage" tab
3. See compute hours and estimated cost

### Check Supabase Usage:
1. Go to Supabase dashboard
2. Click "Usage" → "Database" / "Storage"
3. See bandwidth and storage usage

---

## 🎯 Recommended Testing Flow

1. ✅ **Manual test first** (3 PDFs):
   ```bash
   python test_manual_run.py --max-pdfs 3
   ```
   Expected cost: ~$0.03

2. ✅ **Small batch test** (20 PDFs):
   ```bash
   python test_manual_run.py --max-pdfs 20
   ```
   Expected cost: ~$0.20

3. ✅ **Single competition test** (all matches):
   ```bash
   # Set CBF_COMPETITIONS=142 in Railway
   # Trigger manual run
   ```
   Expected cost: $2-5 (one-time)

4. ✅ **Enable daily automation**:
   - Remove RUN_ONCE env var
   - Let Railway cron run daily
   - Daily cost: $0.02-0.10 (only new matches)

---

## 💡 Key Takeaways

1. ✅ **Deduplication works automatically** - no duplicate API calls
2. ✅ **Re-running is free** - already processed PDFs are skipped
3. ✅ **Cost scales with new content** - only pay for new matches
4. ✅ **Test safely** - start with 3 PDFs (~$0.03)
5. ✅ **Transparent costs** - monitor in real-time via Anthropic console

**Bottom line**: After initial setup, expect **$10-15/month total** for a fully automated, cloud-based football match analysis system! 🎉
