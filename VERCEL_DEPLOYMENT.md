# Vercel Deployment Guide

This guide explains how to deploy the CBF Borderô Robot frontend to Vercel while keeping the backend on Railway.

## Architecture

- **Frontend**: React + TypeScript on Vercel
- **Backend**: FastAPI + Python on Railway
- **Database**: Supabase PostgreSQL
- **Storage**: Supabase Storage

## Features

1. ✅ **Password Protected**: Simple hardcoded password (`cbf2024`) protects the entire app
2. ✅ **PDF Analysis**: Upload and analyze single CBF borderô PDFs
3. ✅ **Interactive Dashboard**: View analytics and financial data
4. ✅ **Context-Aware LLM**: Improved team name disambiguation using match context

## Deployment Steps

### 1. Deploy Frontend to Vercel

#### Option A: Using Vercel CLI

```bash
cd frontend
npm install -g vercel
vercel login
vercel --prod
```

#### Option B: Using Vercel Dashboard

1. Go to [vercel.com](https://vercel.com) and sign in
2. Click "Add New Project"
3. Import your GitHub repository
4. Configure project:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. Add environment variable:
   - **Name**: `VITE_API_URL`
   - **Value**: `https://your-railway-backend.railway.app/api`
6. Click "Deploy"

### 2. Update Railway Backend CORS

After deploying to Vercel, update your Railway environment variables:

1. Go to your Railway project dashboard
2. Click on your service
3. Go to "Variables" tab
4. Add or update:
   ```
   CORS_ORIGINS=https://your-frontend.vercel.app
   ```

   For multiple domains:
   ```
   CORS_ORIGINS=https://your-frontend.vercel.app,https://www.your-custom-domain.com
   ```

5. Click "Save" and redeploy

### 3. Test the Deployment

1. Visit your Vercel URL: `https://your-frontend.vercel.app`
2. Enter password: `cbf2024`
3. Test dashboard - should show analytics data
4. Test PDF upload - submit a borderô URL for analysis

## Configuration Files

### Frontend Environment Variables

Create `.env.local` for local development:

```bash
# .env.local
VITE_API_URL=http://localhost:8000/api
```

For production, set in Vercel dashboard:
```
VITE_API_URL=https://your-railway-backend.railway.app/api
```

### Backend Environment Variables (Railway)

Required variables:
```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...

# CORS (Vercel frontend URL)
CORS_ORIGINS=https://your-frontend.vercel.app

# Optional: Admin JWT secret
JWT_SECRET=your-secret-key
ADMIN_PASSWORD=your-admin-password
```

## Changing the Password

The default password is `cbf2024`. To change it:

1. Open `frontend/src/components/PasswordGate.tsx`
2. Modify line 4:
   ```typescript
   const CORRECT_PASSWORD = 'your-new-password'
   ```
3. Commit and redeploy to Vercel

## Features Overview

### 1. Dashboard (`/`)
- View general statistics
- Filter by competition and team
- View charts and top performers
- Analyze matches, revenue, and attendance

### 2. PDF Upload (`/upload`)
- Analyze borderôs by URL
- Enter match ID, competition code, year
- Submit PDF for LLM analysis
- View processing status

### 3. Context-Aware Team Disambiguation

The LLM now uses match context to disambiguate team names:

**Example**: Botafogo SAF
- **Série A + Rio de Janeiro stadium** → "Botafogo-RJ" ✅
- **Série B + São Paulo stadium** → "Botafogo-SP" ✅

The system considers:
- Competition tier (Série A, B, C)
- Stadium location (city, state)
- Opponent team (helps determine division)

## Troubleshooting

### CORS Errors

**Problem**: "Access to XMLHttpRequest has been blocked by CORS policy"

**Solution**:
1. Check Railway environment variable `CORS_ORIGINS`
2. Make sure it includes your Vercel URL
3. Restart the Railway service

### API Not Found (404)

**Problem**: Frontend can't reach backend API

**Solution**:
1. Check `VITE_API_URL` in Vercel environment variables
2. Make sure it points to your Railway backend
3. Verify Railway backend is running (`/health` endpoint)

### Password Not Working

**Problem**: Password `cbf2024` not working

**Solution**:
1. Clear browser session storage
2. Hard refresh (Ctrl+Shift+R / Cmd+Shift+R)
3. Check `PasswordGate.tsx` for correct password

### PDF Processing Fails

**Problem**: PDF stuck in queue or fails

**Solution**:
1. Check Railway logs for errors
2. Verify `ANTHROPIC_API_KEY` is set
3. Check Supabase connection
4. Ensure PDF URL is accessible

## Custom Domain (Optional)

### Add Custom Domain to Vercel

1. Go to Vercel project settings
2. Click "Domains"
3. Add your domain: `bordero.yourdomain.com`
4. Update DNS records as instructed
5. Update Railway `CORS_ORIGINS`:
   ```
   CORS_ORIGINS=https://bordero.yourdomain.com,https://your-frontend.vercel.app
   ```

## Monitoring

### Vercel
- **Analytics**: Vercel dashboard → Analytics tab
- **Logs**: Vercel dashboard → Deployments → View logs

### Railway
- **Logs**: Railway dashboard → Service → Logs tab
- **Health**: Check `/health` endpoint

### Supabase
- **Database**: Supabase dashboard → Table Editor
- **Storage**: Supabase dashboard → Storage → pdfs bucket

## Security Notes

1. **Password**: Change default password before production use
2. **CORS**: Use specific origins in production (not `*`)
3. **Environment Variables**: Never commit `.env` files
4. **API Keys**: Rotate keys regularly
5. **JWT Secret**: Use strong random secret in production

## Performance

### Vercel Edge Network
- Global CDN for fast frontend delivery
- Automatic SSL/TLS certificates
- DDoS protection

### Railway Backend
- Keep-alive connections to Supabase
- Claude API rate limiting (50 RPM)
- Parallel PDF processing with ThreadPoolExecutor

## Cost Estimates

### Vercel (Hobby Plan - Free)
- 100 GB bandwidth/month
- Unlimited projects
- Automatic SSL

### Railway (Starter Plan - $5/month)
- $5 credit/month
- Additional usage billed
- ~$10-20/month depending on usage

### Supabase (Free Tier)
- 500 MB database storage
- 1 GB file storage
- 50,000 monthly active users

### Anthropic Claude
- Haiku 4.5: $0.25/MTok input, $1.25/MTok output
- ~$0.01-0.05 per borderô analysis

## Support

For issues or questions:
1. Check this deployment guide
2. Review Railway/Vercel logs
3. Check GitHub repository issues
4. Contact development team

## Next Steps

After deployment:
1. ✅ Test password protection
2. ✅ Upload a sample PDF
3. ✅ Verify dashboard shows data
4. ✅ Check backend logs for errors
5. ✅ Set up monitoring/alerts
6. ✅ Change default password
7. ✅ Add custom domain (optional)

---

**Last Updated**: 2024
**Version**: 2.0.0
