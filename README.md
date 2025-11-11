# CBF Borderô Robot 🤖⚽

Modern web application for automated collection and analysis of Brazilian Football Confederation (CBF) match financial reports (borderôs).

**Deployed on Railway** - Production-ready, cloud-native architecture

## 🏗️ Architecture

**FastAPI + React** - Modern, scalable stack

```
┌─────────────────────────────────────────┐
│         Railway Deployment              │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │   FastAPI Backend (Python)         │ │
│  │   • REST API endpoints             │ │
│  │   • Serves React frontend          │ │
│  │   • Supabase integration           │ │
│  │   • Claude AI processing           │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │   React Frontend (TypeScript)      │ │
│  │   • Analytics dashboard            │ │
│  │   • PDF management                 │ │
│  │   • Force scrape controls          │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## ✨ Features

### 📊 Analytics Dashboard (Public)
- General statistics (matches, attendance, revenue, ticket prices)
- Competition analysis with interactive charts
- Top teams and stadiums rankings
- Real-time filtering by competition, team, date

### 🔧 PDF Manager (Admin Only)
- **Force scrape individual PDFs** - Process any specific match on demand
- **Bulk scraping** - Process entire year/competition at once
- Real-time queue status (auto-refresh every 5 seconds)
- Retry failed jobs
- Admin statistics dashboard

### 🔐 Authentication
- Secure admin login
- JWT token-based authentication
- Protected endpoints for admin operations

### 🤖 Automated Processing
- Daily scheduled scraping (optional worker service)
- Claude AI analysis of PDFs (handles scanned documents)
- Automatic name normalization
- Supabase PostgreSQL database + storage

## 🚀 Deploy to Railway (Recommended)

### One-Click Deploy

1. **Fork this repository** to your GitHub account

2. **Go to Railway**: https://railway.app/new

3. **Deploy from GitHub**:
   - Click "Deploy from GitHub repo"
   - Select your forked `robo_bordero` repository
   - Railway automatically detects the Dockerfile

4. **Set environment variables**:
   ```env
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   SUPABASE_URL=https://xxxxx.supabase.co
   SUPABASE_SERVICE_KEY=your-service-role-key-here
   ADMIN_PASSWORD=your-secure-password
   ```

5. **Deploy!** Railway will:
   - ✅ Build Docker image (frontend + backend)
   - ✅ Start the application
   - ✅ Provide a public URL

**Your app will be live at**: `https://your-app-name.up.railway.app`

📖 **Detailed Railway Guide**: See [RAILWAY.md](RAILWAY.md)

## 💻 Local Development

### Quick Start

```bash
# Clone the repository
git clone https://github.com/joaovfcarvalho/robo_bordero.git
cd robo_bordero

# Copy environment variables
cp .env.example .env
# Edit .env with your API keys

# Start both backend and frontend
chmod +x start.sh
./start.sh
```

Access:
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Manual Start

**Backend:**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.api.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Docker

```bash
docker-compose up -d
```

## 🔑 Environment Variables

Required:
```env
ANTHROPIC_API_KEY=sk-ant-...        # Claude API key
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...         # Service role key
```

Optional:
```env
ADMIN_PASSWORD=cbf2025admin         # Admin login password
CORS_ORIGINS=*                      # CORS configuration
CBF_COMPETITIONS=142,424,242        # Competition codes to scrape
```

## 🎯 Usage

### 1. Access the Application

Open your Railway URL or `http://localhost:3000`

### 2. View Analytics (No Login Required)

- Browse general statistics
- Filter by competition, team, or date
- View interactive charts
- Explore match details

### 3. Admin Features (Login Required)

Click **"Admin Login"** and enter your password (default: `cbf2025admin`)

### 4. Force Scrape PDFs

1. Go to **PDF Manager**
2. Select year and competition
3. Click **"Processar"** next to any PDF
4. Watch real-time progress

### 5. Bulk Scraping

1. Go to **PDF Manager**
2. Select year and competition (or leave empty for all)
3. Click **"Processar em Lote"**
4. Monitor queue status

## 📁 Project Structure

```
robo_bordero/
├── src/
│   ├── api/                    # FastAPI backend
│   │   ├── main.py            # App entry (serves frontend)
│   │   ├── routes/
│   │   │   ├── analytics.py   # Analytics API
│   │   │   ├── pdfs.py        # PDF management
│   │   │   └── admin.py       # Admin endpoints
│   │   ├── models.py          # Pydantic models
│   │   └── auth.py            # JWT authentication
│   ├── database.py            # Supabase database
│   ├── storage.py             # Supabase storage
│   ├── claude.py              # Claude AI client
│   └── cloud_worker.py        # Background worker
│
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── pages/             # Dashboard, PDFManager, AdminLogin
│   │   ├── components/        # Reusable UI components
│   │   └── api/               # API client (axios)
│   └── package.json
│
├── Dockerfile                  # Multi-stage Docker build
├── docker-compose.yml          # Local development
├── railway.json                # Railway config
├── start.sh                    # Dev startup script
└── requirements.txt            # Python dependencies
```

## 🛠️ Technology Stack

### Backend
| Tech | Purpose |
|------|---------|
| FastAPI | Modern Python web framework |
| Anthropic Claude | AI-powered PDF analysis |
| Supabase | PostgreSQL database + file storage |
| Pydantic | Data validation |
| Uvicorn | ASGI server |

### Frontend
| Tech | Purpose |
|------|---------|
| React 18 | UI library |
| TypeScript | Type safety |
| Vite | Build tool (fast HMR) |
| TanStack Query | Data fetching & caching |
| Tailwind CSS | Utility-first CSS |
| Recharts | Data visualization |

### Infrastructure
| Tech | Purpose |
|------|---------|
| Railway | Primary deployment platform |
| Docker | Containerization |
| Supabase | Cloud database & storage |

## 🔧 API Endpoints

Full documentation at `/docs`

### Public
- `GET /api/analytics/overview` - Analytics dashboard data
- `GET /api/analytics/matches` - List matches with filters
- `GET /api/analytics/matches/{id}` - Match details

### Admin (Protected)
- `POST /api/admin/login` - Admin authentication
- `POST /api/pdfs/scrape` - Force scrape individual PDF
- `POST /api/admin/bulk-scrape` - Bulk scraping operation
- `GET /api/pdfs/queue` - Queue status
- `GET /api/admin/stats` - System statistics

## 📚 Documentation

- **[Railway Deployment](RAILWAY.md)** - Complete Railway guide
- **[Frontend Architecture](README_FRONTEND.md)** - React app documentation  
- **[Deployment Options](DEPLOYMENT.md)** - Docker, Render, Heroku
- **[Refactoring Summary](REFACTORING_SUMMARY.md)** - Architecture details

## 🧪 Testing

```bash
# Test API
python test_api.py

# Interactive API docs
open http://localhost:8000/docs
```

## 🔐 Security

- ✅ JWT token authentication
- ✅ Protected admin endpoints
- ✅ Environment-based secrets
- ✅ CORS configuration
- ✅ Supabase RLS policies

## 📊 Monitoring

### Railway Dashboard
- Real-time logs
- CPU, memory, network metrics
- Deployment history
- Health checks (pings `/health`)

### Health Check
```bash
curl https://your-app.railway.app/health
```

Response:
```json
{
  "status": "healthy",
  "database": "connected",
  "frontend": "available"
}
```

## 💰 Cost Estimation

| Service | Plan | Cost/Month |
|---------|------|------------|
| Railway | Hobby | $5 |
| Supabase | Free/Pro | $0-25 |
| Anthropic API | Pay-per-use | $10-50 |
| **Total** | | **$15-80** |

## 🚀 Production Checklist

- [ ] Deploy to Railway
- [ ] Set environment variables
- [ ] Change admin password
- [ ] Test force scrape
- [ ] Set up monitoring (UptimeRobot, etc.)
- [ ] Configure custom domain (optional)
- [ ] Add worker service for automation (optional)
- [ ] Enable Supabase backups

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🆘 Support

- **Railway Issues**: [RAILWAY.md](RAILWAY.md)
- **API Documentation**: Visit `/docs` on your deployment
- **GitHub Issues**: Report bugs and feature requests

## 📄 License

MIT License - see LICENSE file

## 🎉 What's New (v2.0)

- ✨ **FastAPI + React** architecture (replaced Streamlit)
- ✨ **Force scrape buttons** for individual PDFs
- ✨ **Bulk scraping** for batch operations
- ✨ **Real-time queue** with auto-refresh
- ✨ **JWT authentication** for admin features
- ✨ **Modern UI** with Tailwind CSS
- ✨ **One-click Railway deployment**
- ✨ **RESTful API** for integrations
- ✨ **TypeScript** throughout frontend

Migration from v1: See [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)

---

**Built with ❤️ for Brazilian Football Analytics**

Powered by: FastAPI • React • Railway • Supabase • Claude AI
