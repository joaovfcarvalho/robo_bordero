# CBF Borderô Robot - Frontend

Modern React frontend for the CBF Borderô Robot analytics dashboard.

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Fast build tool
- **TanStack Query** - Server state management
- **Tailwind CSS** - Styling
- **Recharts** - Data visualization
- **React Router** - Routing

## Features

### Analytics Dashboard
- General statistics (matches, attendance, revenue, ticket prices)
- Competition summaries with charts
- Top teams by attendance
- Top stadiums
- Interactive filters

### PDF Manager (Admin Only)
- List all available PDFs from CBF
- Force scrape specific PDFs
- Bulk scraping operations
- Real-time queue status
- Retry failed jobs
- View processing history

### Authentication
- Password-protected admin area
- JWT token-based authentication
- Secure API calls

## Development

### Prerequisites
- Node.js 18+ and npm

### Installation

```bash
cd frontend
npm install
```

### Running Development Server

```bash
npm run dev
```

The app will be available at http://localhost:3000

The Vite dev server will proxy API requests to http://localhost:8000 (FastAPI backend).

### Building for Production

```bash
npm run build
```

The optimized build will be in the `dist` directory.

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── api/
│   │   └── client.ts          # API client and endpoints
│   ├── components/
│   │   └── Layout.tsx          # Main layout with navigation
│   ├── pages/
│   │   ├── Dashboard.tsx       # Analytics dashboard
│   │   ├── PDFManager.tsx      # PDF management interface
│   │   └── AdminLogin.tsx      # Admin login page
│   ├── types.ts                # TypeScript types
│   ├── App.tsx                 # Main app component
│   ├── main.tsx                # App entry point
│   └── index.css               # Global styles
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

## Environment Variables

Create a `.env` file in the frontend directory:

```env
VITE_API_URL=http://localhost:8000  # API base URL (optional, defaults to /api)
```

## API Integration

The frontend connects to the FastAPI backend running on port 8000. All API calls are automatically proxied in development mode.

### Key API Endpoints

- `GET /api/analytics/overview` - Get analytics overview
- `GET /api/analytics/matches` - Get matches list
- `GET /api/pdfs/available` - Get available PDFs
- `GET /api/pdfs/queue` - Get queue status
- `POST /api/pdfs/scrape` - Force scrape a PDF (admin)
- `POST /api/admin/bulk-scrape` - Bulk scraping (admin)

## Authentication

Admin features require authentication. Default password: `cbf2025admin` (change via `ADMIN_PASSWORD` environment variable in backend).

To access admin features:
1. Go to "Admin Login"
2. Enter admin password
3. Access "PDF Manager" section

## Deployment

### Option 1: Static Hosting (Vercel, Netlify, etc.)

1. Build the frontend:
   ```bash
   npm run build
   ```

2. Deploy the `dist` directory to your hosting provider

3. Configure environment variables:
   - Set `VITE_API_URL` to your FastAPI backend URL

### Option 2: Docker

See the main project README for Docker deployment instructions.

### Option 3: Railway/Render

The frontend can be deployed alongside the backend. See deployment configs in the root directory.

## Development Tips

- The app uses TanStack Query for data fetching with automatic caching
- All API calls are centralized in `src/api/client.ts`
- Authentication state is stored in localStorage
- The app automatically refreshes queue status every 5 seconds
- Use React DevTools and TanStack Query DevTools for debugging
