# Manual Testing Guide

## 🎯 Your Questions Answered

### Q1: Can I force the system to run once with only a few docs?

**Yes!** Use the test script I created:

```bash
# Test with just 3 PDFs (costs ~$0.03)
python test_manual_run.py --year 2025 --competition 142 --max-pdfs 3
```

**What this does:**
- Downloads 3 PDFs from CBF website (Brasileiro Série A 2025)
- Processes them with Claude API
- Uploads to Supabase
- Shows detailed logs and cost estimate

**To test different scenarios:**
```bash
# Test with 1 PDF (ultra-safe)
python test_manual_run.py --max-pdfs 1

# Test with 10 PDFs
python test_manual_run.py --max-pdfs 10

# Test Copa do Brasil instead
python test_manual_run.py --competition 424 --max-pdfs 5
```

---

### Q2: Is the code handling deduplication correctly?

**Yes! ✅ Both checks are implemented:**

#### 1. Skip PDFs Already in Database (Saves Claude API $$$)

**Location**: `src/cloud_worker.py:124-127`

```python
# Check if already processed
if self.db.match_exists(id_jogo_cbf):
    logger.debug(f"Skipping already processed: {id_jogo_cbf}")
    stats["pdfs_skipped"] += 1
    continue  # ← STOPS HERE - No Claude API call!
```

**Result**: If match is in database, worker **completely skips it** - no Claude API call, **$0 cost**!

#### 2. Skip PDFs Already in Storage (Saves Upload Bandwidth)

**Location**: `src/storage.py:82-92`

```python
if not overwrite:
    existing = self.storage.from_(BUCKET_PDF).list(path=str(year))
    existing_files = [f["name"] for f in existing]
    if f"{id_jogo_cbf}.pdf" in existing_files:
        logger.debug(f"PDF already exists in storage: {storage_path}")
        return storage_path  # ← Skips re-upload!
```

**Result**: If PDF is in storage, it **skips re-uploading** - saves bandwidth!

---

### Q3: Why is my dashboard blank?

Your dashboard at `https://cbf-dashboard.railway.app/` is blank because:

**Reason: Database is empty (no data yet)**

The worker hasn't run yet, so there's no data to display. The dashboard works, it just has nothing to show!

---

## 🧪 Complete Testing Flow

### Step 1: Test Supabase Connection

```bash
python test_dashboard_connection.py
```

**This checks:**
- ✓ Environment variables are set
- ✓ Can connect to Supabase
- ✓ Database schema exists
- ✓ How many matches are in database

**Expected output:**
```
✓ SUPABASE_URL: https://xxxxx.supabase.co...
✓ SUPABASE_KEY: eyJh...
✓ Database query successful! Found 0 matches

⚠️  Database is EMPTY - no matches found
→ This is why your dashboard is blank!
```

---

### Step 2: Process 3 Test PDFs Locally

```bash
python test_manual_run.py --max-pdfs 3
```

**Expected output:**
```
[1/3] Processing: 142-2025-001234
  → Uploading PDF to Supabase Storage...
  → Analyzing with Claude Haiku 4.5... ($$)
     PDF size: 0.87 MB
  → Saving to database...
  ✓ SUCCESS - Processed and saved!

[2/3] Processing: 142-2025-001235
  → Uploading PDF to Supabase Storage...
  → Analyzing with Claude Haiku 4.5... ($$)
  → Saving to database...
  ✓ SUCCESS - Processed and saved!

[3/3] Processing: 142-2025-001236
  → Uploading PDF to Supabase Storage...
  → Analyzing with Claude Haiku 4.5... ($$)
  → Saving to database...
  ✓ SUCCESS - Processed and saved!

=====================================
TEST RUN COMPLETE
=====================================
PDFs downloaded:              3
PDFs skipped (in DB):         0
PDFs processed successfully:  3
Claude API calls made:        3
Errors:                       0

💰 Estimated cost: $0.03 USD
```

---

### Step 3: Verify Data in Supabase

1. Go to your Supabase dashboard
2. Click "Table Editor"
3. Select `jogos_resumo` table
4. You should see 3 new rows!

---

### Step 4: Test Dashboard Locally

```bash
streamlit run src/dashboard.py
```

**Expected result:**
- Opens browser at `http://localhost:8501`
- Shows 3 matches you just processed
- Filters and visualizations work

---

### Step 5: Test Deduplication (Re-run)

```bash
python test_manual_run.py --max-pdfs 3
```

**Expected output (second run):**
```
[1/3] Processing: 142-2025-001234
  ✓ SKIPPED - Already in database (no Claude API call!)

[2/3] Processing: 142-2025-001235
  ✓ SKIPPED - Already in database (no Claude API call!)

[3/3] Processing: 142-2025-001236
  ✓ SKIPPED - Already in database (no Claude API call!)

=====================================
PDFs downloaded:              3
PDFs skipped (in DB):         3  ← ALL SKIPPED!
PDFs processed successfully:  0
Claude API calls made:        0  ← NO API CALLS!
Errors:                       0

💰 Estimated cost: $0.00 USD  ← FREE!
```

**Result**: Deduplication works! Second run is FREE! ✅

---

### Step 6: Deploy to Railway (After Verifying Costs)

Once you're happy with local testing:

1. **In Railway dashboard** → Your worker service
2. **Set environment variable**:
   ```
   RUN_ONCE=true
   ```
3. **Click "Restart"** to trigger manual run in cloud
4. **Check logs** to see what it processed
5. **Refresh dashboard** → Data should appear!

---

### Step 7: Enable Automated Daily Runs

When ready for full automation:

1. **In Railway** → Worker service → Variables
2. **Remove** `RUN_ONCE` variable (or set to `false`)
3. **Set** `CBF_COMPETITIONS=142` (or `142,424,242` for multiple)
4. **Save**
5. Worker will now run daily at 2 AM UTC automatically!

---

## 📊 Cost Control Checklist

Before enabling automation, verify:

- ✅ Tested locally with 3 PDFs (~$0.03)
- ✅ Verified deduplication works (second run = $0)
- ✅ Checked Anthropic console for actual API usage
- ✅ Understand daily cost: ~$0.02-0.10 (only new matches)
- ✅ Set `CBF_COMPETITIONS` to limit scope
- ✅ Can disable worker anytime in Railway

---

## 🚨 Troubleshooting

### Dashboard shows "Error loading data from Supabase"

**Fix**:
1. Check Railway logs for the dashboard service
2. Verify environment variables are set:
   - `SUPABASE_URL`
   - `SUPABASE_KEY` (anon key, NOT service_role)
3. Test connection: `python test_dashboard_connection.py`

### Worker shows "ANTHROPIC_API_KEY not found"

**Fix**:
1. In Railway → Worker service → Variables
2. Add `ANTHROPIC_API_KEY=sk-ant-...`
3. Restart service

### "Failed to upload PDF" errors

**Fix**:
1. Check Railway logs for error details
2. Verify `SUPABASE_SERVICE_KEY` is set (worker needs service role key)
3. Check Supabase Storage buckets exist (`pdfs` and `cache`)

---

## 💡 Pro Tips

### Tip 1: Monitor Costs Daily
Check [console.anthropic.com/settings/billing](https://console.anthropic.com/settings/billing) daily for first week

### Tip 2: Start with One Competition
Use `CBF_COMPETITIONS=142` to only track Brasileiro Série A (fewer matches = lower cost)

### Tip 3: Disable Worker on Off-Season
During off-season (no matches), pause the Railway worker service to save compute costs

### Tip 4: Check Logs for Efficiency
Railway logs show:
- How many PDFs downloaded
- How many skipped (already in DB)
- How many Claude API calls made
- Any errors

### Tip 5: Manual Triggers for Control
Instead of daily automation, trigger manually via Railway dashboard when you know there are new matches

---

## 📝 Quick Reference

### Test Commands
```bash
# Connection test
python test_dashboard_connection.py

# Process 3 PDFs
python test_manual_run.py --max-pdfs 3

# Run dashboard locally
streamlit run src/dashboard.py

# Check database
python -c "from src.database import get_database_client; print(len(get_database_client().get_all_matches()))"
```

### Competition Codes
- `142` - Campeonato Brasileiro Série A
- `424` - Copa do Brasil
- `242` - Campeonato Brasileiro Série B
- `341` - Copa Sul-Americana (if available)
- `372` - Copa Libertadores (if available)

### Environment Variables (Railway)
```bash
# Dashboard service
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJh... (anon key)

# Worker service
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJh... (service role key)
CBF_COMPETITIONS=142,424,242
RUN_ONCE=true  # For manual triggers only
```

---

## ✅ Ready to Deploy Checklist

Before going live:

- [ ] Supabase project created and schema deployed
- [ ] Environment variables set in Railway (both services)
- [ ] Local test completed: `python test_manual_run.py --max-pdfs 3`
- [ ] Deduplication verified (second run = $0)
- [ ] Dashboard loads locally with test data
- [ ] Understand costs: ~$10-15/month total
- [ ] Can monitor costs via Anthropic console
- [ ] Can pause/disable worker anytime in Railway

**Once all checked, you're ready to deploy! 🚀**
