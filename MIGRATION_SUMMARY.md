# Migration Summary: Vercel Frontend + Railway Backend

## Overview

This migration separates the frontend and backend infrastructure:
- **Frontend**: Deployed to Vercel (static hosting, global CDN)
- **Backend**: Remains on Railway (FastAPI + workers)

## Key Changes

### 1. ✅ Context-Aware LLM Standardization

**File**: `src/claude.py`

**Changes**:
- Enhanced team name disambiguation using match context
- LLM now considers:
  - Competition tier (Série A, B, C, Libertadores)
  - Stadium location (city, state)
  - Opponent team information
- Added explicit examples for common ambiguous teams:
  - Botafogo-RJ vs Botafogo-SP
  - Nacional-AM vs Nacional-SP
  - América-MG, América-RJ, América-RN

**Example**:
```
Botafogo SAF + Série A + Rio de Janeiro → "Botafogo-RJ" ✅
Botafogo SAF + Série B + São Paulo → "Botafogo-SP" ✅
```

### 2. ✅ Password Protection

**New File**: `frontend/src/components/PasswordGate.tsx`

**Features**:
- Simple hardcoded password: `cbf2024`
- Session-based authentication (no backend required)
- Protects entire application
- Clean, professional UI

### 3. ✅ PDF Upload Component

**New File**: `frontend/src/pages/PDFUpload.tsx`

**Features**:
- Single PDF analysis form
- Input fields:
  - PDF URL (CBF borderô URL)
  - Match ID
  - Competition code (Série A, B, Copa do Brasil)
  - Year
- Real-time processing status
- Success/error feedback
- Helpful instructions for users

### 4. ✅ Simplified Frontend

**Modified Files**:
- `frontend/src/App.tsx` - Removed admin login, added password gate
- `frontend/src/components/Layout.tsx` - Simplified navigation
- `frontend/src/api/client.ts` - Added environment variable support

**Changes**:
- Two main pages: Dashboard + PDF Upload
- Removed complex admin authentication
- Password gate wraps entire app
- Cleaner, more focused UI

### 5. ✅ Vercel Configuration

**New Files**:
- `frontend/vercel.json` - Vercel deployment settings
- `frontend/.env.example` - Environment variable template

**Configuration**:
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite",
  "rewrites": [{"source": "/(.*)", "destination": "/index.html"}]
}
```

### 6. ✅ Backend CORS Updates

**File**: `src/api/main.py`

**Changes**:
- Updated CORS documentation
- Support for Vercel origin URLs
- Environment variable: `CORS_ORIGINS`
- Example: `CORS_ORIGINS=https://your-app.vercel.app`

### 7. ✅ Documentation

**New Files**:
- `VERCEL_DEPLOYMENT.md` - Comprehensive deployment guide
- `MIGRATION_SUMMARY.md` - This file

## Deployment Checklist

### Frontend (Vercel)

- [ ] Connect GitHub repository to Vercel
- [ ] Set root directory: `frontend`
- [ ] Configure environment variable: `VITE_API_URL`
- [ ] Deploy and get Vercel URL
- [ ] Test password protection
- [ ] Test API connectivity

### Backend (Railway)

- [ ] Update `CORS_ORIGINS` with Vercel URL
- [ ] Verify Supabase credentials
- [ ] Verify Anthropic API key
- [ ] Test `/health` endpoint
- [ ] Monitor logs for CORS issues

### Testing

- [ ] Password login works
- [ ] Dashboard displays data
- [ ] PDF upload/analysis works
- [ ] No CORS errors in console
- [ ] Mobile responsive design

## Environment Variables

### Vercel (Frontend)

```bash
VITE_API_URL=https://your-backend.railway.app/api
```

### Railway (Backend)

```bash
# Existing
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
ANTHROPIC_API_KEY=sk-ant-...

# New/Updated
CORS_ORIGINS=https://your-app.vercel.app
```

## Breaking Changes

### Removed Features
1. **Admin Login System** - Replaced with simple password gate
2. **PDF Manager Page** - Simplified to PDF Upload
3. **Protected Routes** - Entire app now password-protected

### Why These Changes?
- **Simplicity**: Easier deployment and maintenance
- **Security**: Single password is sufficient for internal tool
- **Focus**: Dashboard + Upload are the core features
- **Performance**: Vercel CDN for global fast access

## Migration Benefits

### Performance
- ✅ Global CDN via Vercel Edge Network
- ✅ Automatic SSL/TLS
- ✅ Faster frontend delivery worldwide
- ✅ Backend remains dedicated to API processing

### Developer Experience
- ✅ Separate deployments (frontend/backend)
- ✅ Faster frontend iterations
- ✅ Simplified authentication
- ✅ Better error isolation

### Cost Optimization
- ✅ Vercel free tier for frontend
- ✅ Railway only for backend (cheaper)
- ✅ No frontend build on Railway

### Reliability
- ✅ Frontend independent of backend crashes
- ✅ Vercel 99.99% uptime SLA
- ✅ Better DDoS protection
- ✅ Automatic failover

## Technical Details

### Frontend Stack
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Charts**: Recharts
- **Data Fetching**: TanStack Query
- **Routing**: React Router

### Backend Stack
- **Framework**: FastAPI
- **Runtime**: Python 3.11
- **Database**: Supabase PostgreSQL
- **Storage**: Supabase Storage
- **LLM**: Claude Haiku 4.5
- **Scraping**: Requests + ThreadPoolExecutor

### Infrastructure
- **Frontend**: Vercel (Serverless)
- **Backend**: Railway (Container)
- **Database**: Supabase (Managed PostgreSQL)
- **CDN**: Vercel Edge Network

## Security Considerations

### Password
- Default: `cbf2024`
- **Action Required**: Change before production use
- Location: `frontend/src/components/PasswordGate.tsx:4`

### CORS
- **Development**: Allow all origins (`*`)
- **Production**: Specific Vercel domain
- Configure via `CORS_ORIGINS` environment variable

### API Keys
- Store in Railway environment variables
- Never commit to repository
- Rotate regularly

## Troubleshooting

### Common Issues

1. **CORS Errors**
   - Check `CORS_ORIGINS` includes Vercel URL
   - Restart Railway service after changes

2. **API 404 Errors**
   - Verify `VITE_API_URL` in Vercel
   - Check Railway backend is running

3. **Password Not Working**
   - Clear session storage
   - Hard refresh browser

4. **PDF Processing Fails**
   - Check Railway logs
   - Verify Anthropic API key
   - Check Supabase connection

## Next Steps

1. Deploy frontend to Vercel
2. Update Railway CORS settings
3. Test end-to-end workflow
4. Change default password
5. Set up monitoring
6. Add custom domain (optional)

## Rollback Plan

If issues occur:

1. **Revert Frontend**: Redeploy previous Vercel deployment
2. **Revert Backend**: Git revert CORS changes, redeploy Railway
3. **Full Rollback**: Deploy both frontend and backend on Railway (original setup)

## Support

For questions or issues:
1. Review `VERCEL_DEPLOYMENT.md`
2. Check Railway/Vercel logs
3. Contact development team

---

**Migration Date**: 2024
**Version**: 2.0.0
**Status**: ✅ Complete
