# CBF Robot

## Overview
The CBF Robot is a Python-based application designed to automate the collection and intelligent analysis of match reports (borderôs) from the Brazilian Football Confederation (CBF) website. It utilizes web scraping techniques to gather data, integrates with Anthropic's Claude Haiku 4.5 API for AI-powered analysis, and stores structured data in Supabase (cloud PostgreSQL database). The application provides both a traditional GUI and a modern Natural Language Query (NLQ) dashboard for interaction.

## Features
- **Web Scraping:** Automatically downloads PDF match reports (borderôs) from the CBF website for specified competitions and years
- **AI-Powered Data Extraction:** Uses Claude Haiku 4.5 to analyze PDF reports (including image-based/scanned PDFs), extracting match details, financial data, and audience statistics
- **Cloud Storage:** Stores PDFs in Supabase Storage and structured data in PostgreSQL database - no more git bloat!
- **Natural Language Queries:** Ask questions in plain Portuguese like "O que o Santos cobrou do Flamengo?" and get instant answers
- **Interactive Dashboard:** Modern Streamlit dashboard with natural language query interface
- **GUI Interface:** Traditional Tkinter-based GUI for batch operations
- **Smart Name Normalization:** AI-powered normalization of team, stadium, and competition names for consistency
- **Secure Configuration:** API keys stored in environment variables, not plaintext files
- **Comprehensive Logging:** Structured logging with rotation and context
- **Data Validation:** Automated integrity checks with alert logging

## Project Structure
```
cbf-robot/
├── csv/                  # Directory for output CSV files
├── pdfs/                 # Directory for downloaded PDF borderôs
├── src/
│   ├── main.py           # Main application script with GUI
│   ├── scraper.py        # Functions for downloading PDFs
│   ├── gemini.py         # Functions for interacting with Google Gemini API
│   ├── db.py             # Functions for reading/writing CSV files
│   ├── utils.py          # Utility functions (URL generation, logging setup)
│   ├── normalize.py      # Name normalization logic
│   ├── validation.py     # Data validation logic
│   ├── data_validator.py # Data integrity checks
│   ├── dashboard.py      # Streamlit dashboard
│   └── __pycache__/      # Python cache files (auto-generated)
├── tests/                # Unit and integration tests
├── config.json           # Configuration file (user-managed or auto-generated)
├── requirements.txt      # Project dependencies
├── README.md             # This file
└── cbf_robot.log         # Log file (auto-generated)
```

## Setup Instructions

### Prerequisites
- Python 3.7 or higher
- Git
- A Supabase account (free tier available)
- An Anthropic API key for Claude

### 1. Clone the Repository
```bash
git clone <repository-url>
cd cbf-robot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up Supabase (Cloud Storage & Database)

#### 3.1 Create Supabase Project
1. Go to [https://supabase.com](https://supabase.com) and sign up/log in
2. Click "New Project"
3. Choose a name: "cbf-robot-storage"
4. Set a strong database password
5. Select a region (choose closest to your location)
6. Wait for project to be created (~2 minutes)

#### 3.2 Configure Database Schema
1. In your Supabase dashboard, go to "SQL Editor"
2. Copy and paste the schema from `migrations/001_initial_schema.sql`
3. Click "Run" to create tables and indexes

#### 3.3 Configure Storage Buckets
1. Go to "Storage" in Supabase dashboard
2. Click "Create bucket"
   - Name: `pdfs`
   - Public: Off (private)
   - Allowed MIME types: `application/pdf`
   - Max file size: 10MB
3. Create another bucket:
   - Name: `cache`
   - Public: Off
   - Max file size: 1MB

#### 3.4 Get Your Supabase Credentials
1. Go to "Settings" → "API"
2. Copy your:
   - Project URL (e.g., `https://xxxxx.supabase.co`)
   - `anon` public key
   - (Optional) `service_role` key for admin operations

### 4. Configure API Keys (ONE-TIME SETUP)

**✨ Recommended: Secure OS Keyring (Easiest!)**

Run the setup script **once** to save your API key securely:

```bash
python setup_credentials.py
```

This will:
- ✅ Save your API key in your **OS keyring** (Windows Credential Manager, macOS Keychain, Linux Secret Service)
- ✅ **Persist forever** - you only do this once!
- ✅ **Secure** - encrypted by your operating system
- ✅ **No .env file needed** - no risk of accidentally committing credentials

**Alternative: .env File (if keyring doesn't work)**

If the keyring method doesn't work on your system, create a `.env` file:

```bash
# Anthropic Claude API
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Supabase Configuration (Phase 2)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here
SUPABASE_SERVICE_KEY=your_service_role_key_here
```

**Where to get API keys:**
- **Anthropic API Key**: Get it from [Anthropic Console](https://console.anthropic.com/)
- **Supabase Keys**: Found in your Supabase project settings → API (Phase 2)

⚠️ **Important**: If using .env, never commit it to git (already in `.gitignore`)

**Manage Credentials:**
```bash
# Check what's configured
python -m src.config_manager list

# Update/change credentials
python setup_credentials.py

# Delete all credentials
python -m src.config_manager delete
```

### 5. Migrate Existing Data (If You Have CSV/PDF Files)

If you're upgrading from a previous version with local CSV/PDF files:

```bash
# Make sure .env is configured first
python scripts/migrate_csv_to_supabase.py
```

This script will:
- Upload all PDFs to Supabase Storage
- Migrate all CSV data to PostgreSQL
- Preserve all historical data

### 6. Run the Application

#### Main GUI Application
```bash
python src/main.py
```
or
```bash
python run.py
```

#### Natural Language Query Dashboard
```bash
streamlit run src/dashboard_nlq.py
```

This will open an interactive dashboard where you can ask questions like:
- "O que o Santos cobrou do Flamengo no seu jogo como visitante?"
- "Qual foi o público médio do Corinthians em 2025?"
- "Quais foram os 5 jogos com maior receita?"

## Usage

When you run the application, a small window will appear. Use the "Configurações" menu to set your API key and other preferences if you haven't already.

The main window has five buttons for operations:

1.  **1. Apenas download de novos borderôs:** Downloads PDF borderôs for the year and competitions specified in your settings. It only downloads files not already present.
2.  **2. Apenas análise de borderôs não processados:** Analyzes PDFs in the `PDF_DIR` using the Gemini API. It checks `jogos_resumo.csv` and processes only new PDFs.
3.  **3. Download e análise (execução completa):** Performs both download and analysis sequentially.
4.  **4. Normalizar Nomes (CSV):** Processes `jogos_resumo.csv` to create/update `jogos_resumo_clean.csv` by normalizing team, stadium, and competition names using lookups (which may also be refreshed using the Gemini API if new names are found).
5.  **5. Validar Dados (jogos_resumo.csv):** Runs data integrity checks and logs alerts for anomalies.

A message box will indicate when an operation is complete. Progress is shown in a bar at the bottom of the window.

## Data Storage

### Cloud Storage (Supabase)
-   **PDFs**: Stored in Supabase Storage bucket `pdfs/` organized by year
-   **Database Tables**:
    -   `jogos_resumo`: Match summary information with financial data and statistics
    -   `receitas_detalhe`: Detailed revenue breakdown by source
    -   `despesas_detalhe`: Detailed expense breakdown by category

### Local Files
-   **`lookups/`**: JSON files for name normalization (teams, stadiums, competitions)
-   **`cbf_robot.log`**: Application logs with rotation (7-day retention)
-   **`data_validation_alerts.log`**: Data integrity validation alerts
-   **`.env`**: Environment variables (API keys, Supabase credentials) - **DO NOT COMMIT**

### Legacy (For Migration Only)
-   **`pdfs/`**: Local PDF cache (will be uploaded to Supabase)
-   **`csv/`**: CSV files (will be migrated to database)

## Security Best Practices

### API Key Management
✅ **DO:**
- Store API keys in `.env` file (never commit this file)
- Use environment variables for all sensitive credentials
- Add `.env` to `.gitignore` (already configured)
- Rotate API keys periodically

❌ **DON'T:**
- Hardcode API keys in source code
- Commit API keys to version control
- Share API keys in chat/email

### Supabase Security
- Use **anon key** for client-side operations (already has Row Level Security)
- Use **service_role key** only for admin scripts (has full access)
- Enable Row Level Security (RLS) policies on all tables
- Regularly review Supabase audit logs

### Data Protection
- PDFs are stored in private Supabase buckets (authentication required)
- Database uses SSL/TLS encryption in transit
- Supabase provides automatic backups (enable in dashboard)

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. (You may want to add a LICENSE file).

## Migration Roadmap

See [ROADMAP.md](./ROADMAP.md) for detailed implementation plan including:

### ✅ Completed
- Traditional Tkinter GUI
- PDF scraping and processing
- CSV-based storage
- Basic Streamlit dashboard

### 🚧 In Progress (See ROADMAP.md)
- **Phase 1**: Migration to Claude Haiku 4.5 API
  - Better handling of image-based PDFs
  - Improved extraction accuracy
  - Lower latency and cost
- **Phase 2**: Supabase cloud storage migration
  - PostgreSQL database for structured data
  - Cloud storage for PDFs
  - Remove 296MB of files from git
- **Phase 3**: Natural Language Query dashboard
  - Ask questions in Portuguese
  - AI-powered SQL generation
  - Interactive results with explanations

### 🔮 Future Enhancements
- Multi-user authentication
- Advanced predictive analytics
- Mobile app (React Native/Flutter)
- REST API for third-party integrations
- Automated anomaly detection
- Real-time notifications for new borderôs

## Natural Language Query Examples

Once the NLQ dashboard is implemented, you'll be able to ask questions like:

```
💬 "O que o Santos cobrou do Flamengo no seu jogo como visitante?"
💬 "Qual foi o público médio do Corinthians em 2025?"
💬 "Quais foram os 5 jogos com maior receita?"
💬 "Compare a receita do Palmeiras em casa vs visitante"
💬 "Qual estádio teve maior público médio?"
```

The system will:
1. Convert your question to SQL
2. Query the database
3. Return results with natural language explanation
4. Show visualizations when relevant

## Contributing

Contributions are welcome! Please:
1. Read [ROADMAP.md](./ROADMAP.md) to understand the project direction
2. Check open issues or create a new one
3. Fork the repository
4. Create a feature branch
5. Submit a pull request

For major changes, please open an issue first to discuss what you would like to change.