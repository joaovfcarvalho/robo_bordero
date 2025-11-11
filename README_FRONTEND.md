# CBF Borderô Robot - Frontend Refactoring Guide

## What Changed?

The application has been refactored from Streamlit to a modern **FastAPI + React** architecture for improved robustness, scalability, and maintainability.

### Previous Architecture (Streamlit)
- Single monolithic Streamlit app
- Python-based UI rendering
- Limited customization options
- All processing in the main thread

### New Architecture (FastAPI + React)
- **Backend**: FastAPI REST API (Python)
- **Frontend**: React with TypeScript (Vite)
- **API Documentation**: Auto-generated Swagger/OpenAPI docs
- **State Management**: TanStack Query for server state
- **Styling**: Tailwind CSS for modern, responsive design

## Features

### 🎯 Analytics Dashboard (Public)
- **General Statistics**: Total matches, attendance, revenue, ticket prices
- **Competition Analysis**: Games, revenue, and attendance by competition
- **Team Rankings**: Top teams by average attendance
- **Stadium Statistics**: Top stadiums with attendance data
- **Interactive Filters**: Filter by competition, team, date range
- **Visualizations**: Charts and graphs using Recharts

### 🔒 PDF Manager (Admin Only)
- **List Available PDFs**: View all CBF borderôs
- **Force Scrape Button**: Process specific PDFs on demand
- **Bulk Scraping**: Process entire year/competition at once
- **Queue Status**: Real-time view of processing queue
- **Retry Failed Jobs**: Retry PDFs that failed processing
- **Admin Statistics**: Overview of system status

### 🔐 Authentication
- Password-protected admin features
- JWT token-based authentication
- Automatic token refresh
- Secure API endpoints

## Quick Start

### Development Mode

1. **Start both backend and frontend**:
   ```bash
   chmod +x start.sh
   ./start.sh
   ```

   This will start:
   - FastAPI backend on http://localhost:8000
   - React frontend on http://localhost:3000

2. **Or start manually**:

   **Backend**:
   ```bash
   # Install dependencies
   pip install -r requirements.txt

   # Run FastAPI
   uvicorn src.api.main:app --reload --port 8000
   ```

   **Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Access the application**:
   - Frontend: http://localhost:3000
   - API Docs: http://localhost:8000/docs
   - API: http://localhost:8000/api

### Production Deployment

#### Option 1: Docker

```bash
# Build and run with docker-compose
docker-compose up -d

# Or build manually
docker build -t cbf-bordero .
docker run -p 8000:8000 \
  -e ANTHROPIC_API_KEY=your_key \
  -e SUPABASE_URL=your_url \
  -e SUPABASE_SERVICE_KEY=your_key \
  cbf-bordero
```

#### Option 2: Railway

1. Connect your GitHub repository
2. Railway will automatically detect the Dockerfile
3. Set environment variables in Railway dashboard:
   - `ANTHROPIC_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
   - `ADMIN_PASSWORD`
4. Deploy!

The frontend is built and served from the same container as the backend.

## API Endpoints

### Analytics (Public)
- `GET /api/analytics/overview` - Get analytics overview with filters
- `GET /api/analytics/matches` - Get list of matches
- `GET /api/analytics/matches/{id}` - Get detailed match info
- `GET /api/analytics/filters/competitions` - Get available competitions
- `GET /api/analytics/filters/teams` - Get available teams
- `GET /api/analytics/filters/stadiums` - Get available stadiums

### PDF Management (Admin)
- `GET /api/pdfs/available` - List available PDFs
- `GET /api/pdfs/queue` - Get processing queue status
- `POST /api/pdfs/scrape` - Force scrape a specific PDF
- `DELETE /api/pdfs/queue/{id}` - Remove from queue
- `POST /api/pdfs/queue/retry/{id}` - Retry failed item

### Admin (Protected)
- `POST /api/admin/login` - Admin login
- `POST /api/admin/logout` - Admin logout
- `POST /api/admin/bulk-scrape` - Start bulk scraping
- `GET /api/admin/stats` - Get system statistics
- `POST /api/admin/refresh-normalizations` - Refresh name normalizations
- `DELETE /api/admin/matches/{id}` - Delete a match

## Environment Variables

### Backend
```env
# Required
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...

# Optional
ADMIN_PASSWORD=cbf2025admin
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

### Frontend (Development)
```env
VITE_API_URL=http://localhost:8000  # Optional, defaults to /api
```

## Technology Stack

### Backend
- **FastAPI** 0.109+ - Modern Python web framework
- **Uvicorn** - ASGI server
- **Pydantic** 2.0+ - Data validation
- **Anthropic SDK** - Claude API integration
- **Supabase** - Database and storage
- **Pandas** - Data analysis

### Frontend
- **React** 18 - UI library
- **TypeScript** 5+ - Type safety
- **Vite** 5 - Build tool and dev server
- **TanStack Query** 5 - Data fetching and caching
- **React Router** 6 - Client-side routing
- **Tailwind CSS** 3 - Utility-first CSS
- **Recharts** 2 - Data visualization
- **Axios** - HTTP client
- **Lucide React** - Icon library

## Project Structure

```
robo_bordero/
├── src/
│   ├── api/                      # NEW: FastAPI backend
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── models.py            # Pydantic models
│   │   ├── auth.py              # Authentication
│   │   └── routes/
│   │       ├── analytics.py     # Analytics endpoints
│   │       ├── pdfs.py          # PDF management endpoints
│   │       └── admin.py         # Admin endpoints
│   ├── database.py
│   ├── storage.py
│   ├── scraper.py
│   ├── claude.py
│   ├── cloud_worker.py
│   └── dashboard.py             # OLD: Streamlit (deprecated)
│
├── frontend/                     # NEW: React frontend
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts        # API client
│   │   ├── components/
│   │   │   └── Layout.tsx       # Main layout
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx    # Analytics page
│   │   │   ├── PDFManager.tsx   # PDF management page
│   │   │   └── AdminLogin.tsx   # Login page
│   │   ├── types.ts             # TypeScript types
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── Dockerfile                    # NEW: Multi-stage build
├── docker-compose.yml           # NEW: Docker Compose config
├── start.sh                     # NEW: Development startup script
├── requirements.txt             # Updated with FastAPI
└── railway.json                 # Updated for new deployment

```

## Migration Notes

### For Developers

1. **Streamlit is deprecated** but still available for backward compatibility
2. All new features should use the FastAPI + React architecture
3. The old Streamlit dashboard is at `/src/dashboard.py`
4. The new API is fully documented at `/docs` (Swagger UI)

### For Users

1. The UI looks different but has the same features plus more
2. Admin password is the same (`ADMIN_PASSWORD` env variable)
3. All existing data is compatible
4. No database migration needed

### Breaking Changes

- Streamlit UI is no longer the default
- Must run both backend and frontend (or use Docker)
- New authentication system for admin features

## Benefits of New Architecture

### ✅ Performance
- React's virtual DOM for fast UI updates
- API responses are cached with TanStack Query
- Backend can handle concurrent requests efficiently

### ✅ Scalability
- Backend and frontend can scale independently
- API can serve multiple clients (web, mobile, etc.)
- Better resource utilization

### ✅ Developer Experience
- TypeScript for type safety
- Auto-generated API documentation
- Hot module replacement in development
- Better debugging tools

### ✅ Production Ready
- Proper error handling
- Health checks
- Rate limiting support
- CORS configuration
- Docker support

### ✅ Maintainability
- Separation of concerns
- RESTful API design
- Reusable components
- Comprehensive testing support

## Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is available
lsof -ti:8000 | xargs kill -9

# Check environment variables
python -c "import os; print(os.getenv('ANTHROPIC_API_KEY'))"
```

### Frontend won't start
```bash
# Clear node_modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### API requests failing
- Check CORS configuration in backend
- Verify API URL in frontend `.env`
- Check network tab in browser dev tools
- Review backend logs for errors

### Authentication issues
- Clear localStorage in browser
- Check `ADMIN_PASSWORD` environment variable
- Verify token is being sent in requests

## Support

For issues or questions:
1. Check the API docs at `/docs`
2. Review logs in the console
3. Check the GitHub repository issues

## Next Steps

- [ ] Add WebSocket support for real-time updates
- [ ] Implement user roles (beyond admin/public)
- [ ] Add export functionality for reports
- [ ] Create mobile-responsive improvements
- [ ] Add unit tests for frontend components
- [ ] Set up CI/CD pipeline
