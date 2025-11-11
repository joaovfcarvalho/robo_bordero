# CBF Robot - Implementation Roadmap

## 🎯 Project Goals

This roadmap outlines the migration of CBF Robot from:
- **Google Gemini API** → **Anthropic Claude Haiku 4.5** ✅ COMPLETED
- **Local CSV/PDF Storage** → **Supabase Cloud Storage + PostgreSQL** ✅ COMPLETED
- **Local Desktop App** → **Fully Cloud-Based Application (Railway/Render)** ✅ COMPLETED
- **Static Dashboard** → **Interactive Cloud Dashboard with Natural Language Queries** 🚧 IN PROGRESS

## 📊 Current State Analysis

### What We Have NOW (Cloud Architecture)
- ✅ **Claude Haiku 4.5 API** integration with vision support for image-based PDFs
- ✅ **Supabase Cloud Storage** for PDFs (no more git bloat!)
- ✅ **Supabase PostgreSQL** for structured data (replaces CSV)
- ✅ **Cloud Worker** (src/cloud_worker.py) for automated scheduled processing
- ✅ **Streamlit Dashboard** connected to Supabase (cloud-ready)
- ✅ **Railway/Render deployment configs** for full cloud deployment
- ✅ **Name normalization** with AI-powered lookups stored in database

### Cloud Architecture Overview
```
┌─────────────────────────────────────────────────────┐
│              CLOUD DEPLOYMENT (Railway)              │
├─────────────────────────────────────────────────────┤
│                                                       │
│  ┌──────────────────┐      ┌──────────────────┐    │
│  │  Service 1:      │      │  Service 2:      │    │
│  │  Dashboard       │      │  Scheduled Worker│    │
│  │  (Streamlit)     │      │  (Cron: 2 AM)    │    │
│  └────────┬─────────┘      └────────┬─────────┘    │
│           │                         │               │
│           │  Read data             │ Write data    │
│           ├────────────┬────────────┤               │
│           ▼            ▼            ▼               │
│     ┌─────────────────────────────────┐            │
│     │       SUPABASE                  │            │
│     │  - PostgreSQL (data)            │            │
│     │  - Storage (PDFs)               │            │
│     └─────────────────────────────────┘            │
│                                                      │
│  External APIs:                                     │
│  - Claude Haiku 4.5 (PDF processing)                │
│  - CBF Website (PDF downloads)                      │
└─────────────────────────────────────────────────────┘
```

### Former Challenges (NOW SOLVED)
- ✅ **Image-based PDFs**: Solved with Claude Haiku 4.5's vision capabilities
- ✅ **Inconsistent Structures**: Claude handles layout variations better than Gemini
- ✅ **Non-standardized Names**: AI-powered normalization with database lookups
- ✅ **Git Bloat**: PDFs now in Supabase Storage (removed 296MB from git)
- ✅ **API Key Security**: Secure environment variable management
- ✅ **CSV Limitations**: PostgreSQL with transactions and concurrent access
- ✅ **Local Machine Dependency**: Fully cloud-based, runs 24/7 without your machine

---

## 🗓️ Implementation Timeline

### **PHASE 1: Foundation & API Migration** (Week 1-2)

#### **Milestone 1.1: Secure API Key Management** ⏱️ 1-2 days
**Priority:** CRITICAL

**Tasks:**
- [ ] Install `python-dotenv` package
- [ ] Create `.env` file for API keys
- [ ] Add `.env` to `.gitignore`
- [ ] Update `main.py` to load from environment variables
- [ ] Add `keyring` package for OS-level secure storage
- [ ] Sanitize logs to mask API keys
- [ ] Update documentation with new setup instructions

**Files to Modify:**
- `requirements.txt` - Add `python-dotenv`, `keyring`
- `src/main.py` - Load API key from env vars
- `src/gemini.py` - Remove hardcoded key references
- `src/normalize.py` - Remove hardcoded key references
- `.gitignore` - Add `.env`, `config.json`
- `README.md` - Update setup instructions

**Implementation Details:**
```python
# .env file
ANTHROPIC_API_KEY=your_anthropic_key_here

# src/main.py
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('ANTHROPIC_API_KEY')

# Optional: OS keyring fallback
import keyring
if not api_key:
    api_key = keyring.get_password('cbf_robot', 'anthropic_api_key')
```

**Success Criteria:**
- ✅ No API keys in plaintext files
- ✅ Keys loaded from environment variables
- ✅ Logs do not expose keys
- ✅ Documentation updated

---

#### **Milestone 1.2: Claude Haiku 4.5 Integration** ⏱️ 3-5 days
**Priority:** CRITICAL

**Tasks:**
- [ ] Install `anthropic` SDK package
- [ ] Create new `src/claude.py` module
- [ ] Implement `analyze_pdf_with_claude()` function
- [ ] Handle image-based PDFs with vision capabilities
- [ ] Implement robust retry logic with exponential backoff
- [ ] Add rate limiting (TPM tracking)
- [ ] Create parallel testing suite (Gemini vs Claude)
- [ ] Update `main.py` to use Claude instead of Gemini
- [ ] Update `normalize.py` to use Claude for name normalization
- [ ] Run regression tests on sample PDFs
- [ ] Document Claude-specific best practices

**Files to Create:**
- `src/claude.py` - New Claude SDK integration module

**Files to Modify:**
- `requirements.txt` - Add `anthropic>=0.40.0`
- `src/main.py` - Import from `claude.py` instead of `gemini.py`
- `src/normalize.py` - Use Claude for normalization
- `tests/test_functions.py` - Add Claude integration tests

**Implementation Details:**

```python
# src/claude.py
import anthropic
import base64
import time
from typing import Dict, Any, Optional
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)

class ClaudeClient:
    """
    Claude Haiku 4.5 client for borderô analysis.
    Handles both native PDFs and image-based PDFs.
    """

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-haiku-4-5-20251001"
        self.max_retries = 3
        self.requests_per_minute = 50  # Adjust based on tier
        self.last_request_time = 0

    def _rate_limit(self):
        """Implement rate limiting to avoid API throttling."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 60.0 / self.requests_per_minute

        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def analyze_pdf(
        self,
        pdf_bytes: bytes,
        retry_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analyze a CBF borderô PDF and extract structured data.

        Handles both:
        - Native text PDFs (directly readable)
        - Image-based/scanned PDFs (uses vision)

        Args:
            pdf_bytes: Raw PDF bytes
            retry_count: Number of retry attempts (default: 3)

        Returns:
            Dict containing:
            - success: bool
            - data: Extracted match data (if successful)
            - error: Error message (if failed)
        """
        if retry_count is None:
            retry_count = self.max_retries

        # Encode PDF to base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

        # Define extraction prompt
        extraction_prompt = """
Você é um especialista em análise de borderôs da CBF (Confederação Brasileira de Futebol).

Analise este borderô e extraia as seguintes informações em formato JSON:

**ATENÇÃO ESPECIAL:**
1. **Nomes de Times**: Os times podem aparecer com diferentes formatos:
   - "SANTOS FUTEBOL CLUBE - SP" → normalizar para "Santos"
   - "CLUBE DE REGATAS DO FLAMENGO - RJ" → normalizar para "Flamengo"
   - "SÃO PAULO FUTEBOL CLUBE - SP" → normalizar para "São Paulo"
   - Remova sufixos como "FC", "SAF", "S/A", siglas de estados
   - Use o nome popular/comum do time

2. **Estádios**: Normalize os nomes dos estádios:
   - "ESTÁDIO MORUMBI - SÃO PAULO - SP" → normalizar para "Morumbi"
   - Remova cidade e estado a menos que necessário para desambiguação

3. **Competições**: Normalize os nomes:
   - "CAMPEONATO BRASILEIRO SÉRIE A 2025" → "Brasileiro - Série A"
   - "COPA DO BRASIL 2025" → "Copa do Brasil"

4. **Valores Financeiros**:
   - Aceite tanto formato brasileiro (1.234,56) quanto internacional (1234.56)
   - Converta para float decimal (use ponto como separador)

5. **Datas**: Aceite DD/MM/YYYY (formato brasileiro)

Retorne JSON no seguinte formato:

{
  "match_details": {
    "home_team": "nome normalizado do time mandante",
    "away_team": "nome normalizado do time visitante",
    "match_date": "DD/MM/YYYY",
    "stadium": "nome normalizado do estádio",
    "competition": "nome normalizado da competição"
  },
  "financial_data": {
    "gross_revenue": 123456.78,
    "total_expenses": 98765.43,
    "net_result": 24691.35,
    "revenue_details": [
      {
        "source": "Bilheteria",
        "quantity": 10000,
        "price": 50.0,
        "amount": 500000.0
      }
    ],
    "expense_details": [
      {
        "category": "Arbitragem",
        "amount": 15000.0
      }
    ]
  },
  "audience_statistics": {
    "paid_attendance": 10000,
    "non_paid_attendance": 500,
    "total_attendance": 10500
  }
}

Se não conseguir extrair algum valor, use null. Seja preciso com os números.
"""

        for attempt in range(1, retry_count + 1):
            try:
                self._rate_limit()

                logger.info(
                    "Calling Claude API",
                    attempt=attempt,
                    model=self.model
                )

                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    temperature=0.0,  # Deterministic extraction
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "document",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "application/pdf",
                                        "data": pdf_base64
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": extraction_prompt
                                }
                            ]
                        }
                    ]
                )

                # Extract text response
                response_text = ""
                for block in message.content:
                    if block.type == "text":
                        response_text += block.text

                # Parse JSON from response
                import json
                import re

                # Try to find JSON in response
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())

                    logger.info(
                        "Successfully extracted data",
                        home_team=data.get('match_details', {}).get('home_team'),
                        away_team=data.get('match_details', {}).get('away_team')
                    )

                    return {
                        "success": True,
                        "data": data
                    }
                else:
                    raise ValueError("No JSON found in response")

            except anthropic.RateLimitError as e:
                logger.warning(
                    "Rate limit hit",
                    attempt=attempt,
                    error=str(e)
                )
                if attempt < retry_count:
                    backoff = 2 ** attempt
                    logger.info(f"Backing off {backoff}s before retry")
                    time.sleep(backoff)
                else:
                    return {
                        "success": False,
                        "error": f"Rate limit exceeded after {retry_count} attempts"
                    }

            except anthropic.APIError as e:
                logger.error(
                    "Claude API error",
                    attempt=attempt,
                    error=str(e)
                )
                if attempt < retry_count:
                    backoff = 2 ** attempt
                    time.sleep(backoff)
                else:
                    return {
                        "success": False,
                        "error": f"API error: {str(e)}"
                    }

            except Exception as e:
                logger.error(
                    "Unexpected error during PDF analysis",
                    attempt=attempt,
                    error=str(e),
                    error_type=type(e).__name__
                )
                if attempt < retry_count:
                    time.sleep(2 ** attempt)
                else:
                    return {
                        "success": False,
                        "error": f"Extraction failed: {str(e)}"
                    }

        return {
            "success": False,
            "error": "Failed after all retry attempts"
        }

    def normalize_names(
        self,
        names: list[str],
        category: str,
        existing_mappings: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Use Claude to normalize team/stadium/competition names.

        Args:
            names: List of names to normalize
            category: "teams", "stadiums", or "competitions"
            existing_mappings: Already-known mappings to maintain consistency

        Returns:
            Dict mapping original names to normalized names
        """
        if not names:
            return {}

        if existing_mappings is None:
            existing_mappings = {}

        prompt = f"""
Você é um especialista em futebol brasileiro.

Normalize os seguintes nomes de {category} para formatos padronizados e curtos.

**Regras:**
- Times: Use nome popular (ex: "Flamengo", "Santos", "São Paulo")
  - Remova "FC", "SAF", "S/A", "FUTEBOL CLUBE"
  - Mantenha estado apenas se necessário (ex: "Botafogo-RJ" vs "Botafogo-PB")
- Estádios: Use nome comum, sem cidade/estado
  - Ex: "MARACANÃ - RIO DE JANEIRO - RJ" → "Maracanã"
- Competições: Formato "Competição - Divisão"
  - Ex: "CAMPEONATO BRASILEIRO SÉRIE A 2025" → "Brasileiro - Série A"

**Nomes existentes (mantenha consistência):**
{json.dumps(existing_mappings, ensure_ascii=False, indent=2)}

**Nomes para normalizar:**
{json.dumps(names, ensure_ascii=False, indent=2)}

Retorne apenas JSON no formato:
{{
  "Nome Original 1": "Nome Normalizado 1",
  "Nome Original 2": "Nome Normalizado 2"
}}
"""

        try:
            self._rate_limit()

            message = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0.0,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            response_text = ""
            for block in message.content:
                if block.type == "text":
                    response_text += block.text

            # Parse JSON
            import json
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                mappings = json.loads(json_match.group())
                logger.info(
                    "Successfully normalized names",
                    category=category,
                    count=len(mappings)
                )
                return mappings
            else:
                logger.error("No JSON found in normalization response")
                return {}

        except Exception as e:
            logger.error(
                "Failed to normalize names",
                category=category,
                error=str(e)
            )
            return {}
```

**Handling Image-Based PDFs:**
Claude Haiku 4.5 has native vision capabilities, so image-based PDFs are handled automatically. The model can:
- Read text from scanned images
- Understand table structures
- Extract information from inconsistent layouts
- Handle Brazilian Portuguese text in images

**Rate Limiting Strategy:**
```python
# config.py (new file)
RATE_LIMITS = {
    "claude-haiku-4-5-20251001": {
        "requests_per_minute": 50,  # Adjust based on your tier
        "tokens_per_minute": 50000,
        "tokens_per_day": 1000000
    }
}
```

**Success Criteria:**
- ✅ Claude SDK installed and configured
- ✅ Image-based PDFs processed successfully
- ✅ Extraction accuracy ≥95% on test set
- ✅ Rate limiting prevents API throttling
- ✅ All tests pass
- ✅ Performance: <5s per PDF on average

---

### **PHASE 2: Cloud Storage Migration** (Week 3-4)

#### **Milestone 2.1: Supabase Setup** ⏱️ 1 day
**Priority:** HIGH

**Tasks:**
- [ ] Create Supabase account at https://supabase.com
- [ ] Create new project: "cbf-robot-storage"
- [ ] Note project URL and anon/service keys
- [ ] Enable Storage bucket for PDFs
- [ ] Create PostgreSQL database schema
- [ ] Configure Row Level Security (RLS) policies
- [ ] Install `supabase-py` package
- [ ] Create `src/storage.py` module
- [ ] Test connection and basic operations

**Supabase Configuration:**

**Database Schema:**
```sql
-- Create tables
CREATE TABLE jogos_resumo (
    id SERIAL PRIMARY KEY,
    id_jogo_cbf VARCHAR(50) UNIQUE NOT NULL,
    data_jogo DATE NOT NULL,
    time_mandante VARCHAR(100),
    time_visitante VARCHAR(100),
    estadio VARCHAR(200),
    competicao VARCHAR(100),
    publico_pagante INTEGER,
    publico_nao_pagante INTEGER,
    publico_total INTEGER,
    receita_bruta_total DECIMAL(12, 2),
    despesa_total DECIMAL(12, 2),
    resultado_liquido DECIMAL(12, 2),
    s3_pdf_path TEXT,  -- Supabase storage URL
    data_processamento TIMESTAMP DEFAULT NOW(),
    status VARCHAR(50),
    log_erro TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE receitas_detalhe (
    id SERIAL PRIMARY KEY,
    id_jogo_cbf VARCHAR(50) NOT NULL REFERENCES jogos_resumo(id_jogo_cbf),
    source VARCHAR(100),
    quantity INTEGER,
    price DECIMAL(10, 2),
    amount DECIMAL(12, 2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE despesas_detalhe (
    id SERIAL PRIMARY KEY,
    id_jogo_cbf VARCHAR(50) NOT NULL REFERENCES jogos_resumo(id_jogo_cbf),
    category VARCHAR(100),
    amount DECIMAL(12, 2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX idx_jogos_data ON jogos_resumo(data_jogo);
CREATE INDEX idx_jogos_mandante ON jogos_resumo(time_mandante);
CREATE INDEX idx_jogos_visitante ON jogos_resumo(time_visitante);
CREATE INDEX idx_jogos_competicao ON jogos_resumo(competicao);
CREATE INDEX idx_receitas_jogo ON receitas_detalhe(id_jogo_cbf);
CREATE INDEX idx_despesas_jogo ON despesas_detalhe(id_jogo_cbf);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_jogos_resumo_updated_at
    BEFORE UPDATE ON jogos_resumo
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

**Storage Buckets:**
```javascript
// In Supabase Dashboard -> Storage
// Create bucket: "pdfs"
// Settings:
// - Public: false (require authentication)
// - Allowed MIME types: application/pdf
// - Max file size: 10MB

// Create bucket: "cache"
// Settings:
// - Public: false
// - Max file size: 1MB
```

**Environment Variables:**
```bash
# Add to .env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here
SUPABASE_SERVICE_KEY=your_service_key_here  # For admin operations
```

**Files to Create:**
- `src/storage.py` - Supabase storage operations
- `migrations/001_initial_schema.sql` - Database schema

**Files to Modify:**
- `requirements.txt` - Add `supabase>=2.0.0`
- `.env` - Add Supabase credentials
- `README.md` - Add Supabase setup instructions

**Success Criteria:**
- ✅ Supabase project created
- ✅ Database schema deployed
- ✅ Storage buckets configured
- ✅ Connection tested successfully

---

#### **Milestone 2.2: Implement Storage Layer** ⏱️ 3-4 days
**Priority:** HIGH

**Tasks:**
- [ ] Create `src/storage.py` with SupabaseStorage class
- [ ] Implement PDF upload to Supabase Storage
- [ ] Implement PDF download/caching
- [ ] Create `src/database.py` with SupabaseDatabase class
- [ ] Implement CRUD operations for all tables
- [ ] Add transaction support
- [ ] Implement connection pooling
- [ ] Add error handling and retries
- [ ] Create data migration utility
- [ ] Write unit tests for storage operations

**Implementation:**

```python
# src/storage.py
from supabase import create_client, Client
from pathlib import Path
from typing import Optional
import structlog
import os

logger = structlog.get_logger(__name__)

class SupabaseStorage:
    """
    Manages PDF and cache file storage in Supabase.
    """

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        self.url = url or os.getenv('SUPABASE_URL')
        self.key = key or os.getenv('SUPABASE_KEY')

        if not self.url or not self.key:
            raise ValueError("Supabase URL and key must be provided")

        self.client: Client = create_client(self.url, self.key)
        self.pdf_bucket = "pdfs"
        self.cache_bucket = "cache"

    def upload_pdf(
        self,
        local_path: Path,
        year: int,
        id_jogo_cbf: str
    ) -> str:
        """
        Upload PDF to Supabase Storage.

        Args:
            local_path: Local file path
            year: Year of the match
            id_jogo_cbf: Match ID

        Returns:
            Supabase storage URL
        """
        try:
            # Create storage path: pdfs/2025/14210b_2025.pdf
            storage_path = f"{year}/{id_jogo_cbf}.pdf"

            # Check if already exists
            if self.pdf_exists(storage_path):
                logger.info(f"PDF already exists in storage: {storage_path}")
                return self.get_pdf_url(storage_path)

            # Read file
            with open(local_path, 'rb') as f:
                file_data = f.read()

            # Upload to Supabase
            response = self.client.storage.from_(self.pdf_bucket).upload(
                path=storage_path,
                file=file_data,
                file_options={"content-type": "application/pdf"}
            )

            logger.info(
                "PDF uploaded successfully",
                storage_path=storage_path,
                size_kb=len(file_data) / 1024
            )

            return self.get_pdf_url(storage_path)

        except Exception as e:
            logger.error(
                "Failed to upload PDF",
                local_path=str(local_path),
                error=str(e)
            )
            raise

    def download_pdf(
        self,
        storage_path: str,
        local_path: Path
    ) -> Path:
        """
        Download PDF from Supabase to local cache.

        Args:
            storage_path: Path in Supabase storage
            local_path: Where to save locally

        Returns:
            Local file path
        """
        try:
            # Download from Supabase
            response = self.client.storage.from_(self.pdf_bucket).download(
                storage_path
            )

            # Ensure parent directory exists
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to local file
            with open(local_path, 'wb') as f:
                f.write(response)

            logger.info(
                "PDF downloaded successfully",
                storage_path=storage_path,
                local_path=str(local_path)
            )

            return local_path

        except Exception as e:
            logger.error(
                "Failed to download PDF",
                storage_path=storage_path,
                error=str(e)
            )
            raise

    def pdf_exists(self, storage_path: str) -> bool:
        """Check if PDF exists in Supabase storage."""
        try:
            files = self.client.storage.from_(self.pdf_bucket).list(
                path=str(Path(storage_path).parent)
            )

            filename = Path(storage_path).name
            return any(f['name'] == filename for f in files)

        except Exception:
            return False

    def get_pdf_url(self, storage_path: str) -> str:
        """Get public URL for PDF (if bucket is public) or signed URL."""
        # For private buckets, use signed URL
        response = self.client.storage.from_(self.pdf_bucket).create_signed_url(
            path=storage_path,
            expires_in=3600 * 24 * 365  # 1 year
        )
        return response['signedURL']
```

```python
# src/database.py
from supabase import create_client, Client
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog
import os

logger = structlog.get_logger(__name__)

class SupabaseDatabase:
    """
    Manages database operations for CBF Robot using Supabase PostgreSQL.
    """

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        self.url = url or os.getenv('SUPABASE_URL')
        self.key = key or os.getenv('SUPABASE_KEY')

        if not self.url or not self.key:
            raise ValueError("Supabase URL and key must be provided")

        self.client: Client = create_client(self.url, self.key)

    def add_match(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert a new match record.

        Args:
            match_data: Dict with match information

        Returns:
            Inserted record with ID
        """
        try:
            response = self.client.table('jogos_resumo').insert(match_data).execute()

            logger.info(
                "Match added to database",
                id_jogo_cbf=match_data.get('id_jogo_cbf')
            )

            return response.data[0] if response.data else {}

        except Exception as e:
            logger.error(
                "Failed to add match",
                id_jogo_cbf=match_data.get('id_jogo_cbf'),
                error=str(e)
            )
            raise

    def match_exists(self, id_jogo_cbf: str) -> bool:
        """Check if match already exists in database."""
        try:
            response = self.client.table('jogos_resumo').select('id').eq(
                'id_jogo_cbf', id_jogo_cbf
            ).execute()

            return len(response.data) > 0

        except Exception as e:
            logger.error(
                "Failed to check match existence",
                id_jogo_cbf=id_jogo_cbf,
                error=str(e)
            )
            return False

    def add_revenue_details(
        self,
        id_jogo_cbf: str,
        revenue_details: List[Dict[str, Any]]
    ):
        """Insert revenue details for a match."""
        try:
            # Add id_jogo_cbf to each record
            records = [
                {**detail, 'id_jogo_cbf': id_jogo_cbf}
                for detail in revenue_details
            ]

            response = self.client.table('receitas_detalhe').insert(
                records
            ).execute()

            logger.info(
                "Revenue details added",
                id_jogo_cbf=id_jogo_cbf,
                count=len(records)
            )

        except Exception as e:
            logger.error(
                "Failed to add revenue details",
                id_jogo_cbf=id_jogo_cbf,
                error=str(e)
            )
            raise

    def add_expense_details(
        self,
        id_jogo_cbf: str,
        expense_details: List[Dict[str, Any]]
    ):
        """Insert expense details for a match."""
        try:
            records = [
                {**detail, 'id_jogo_cbf': id_jogo_cbf}
                for detail in expense_details
            ]

            response = self.client.table('despesas_detalhe').insert(
                records
            ).execute()

            logger.info(
                "Expense details added",
                id_jogo_cbf=id_jogo_cbf,
                count=len(records)
            )

        except Exception as e:
            logger.error(
                "Failed to add expense details",
                id_jogo_cbf=id_jogo_cbf,
                error=str(e)
            )
            raise

    def get_all_matches(
        self,
        limit: Optional[int] = None,
        order_by: str = 'data_jogo',
        ascending: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all matches from database.

        Args:
            limit: Max number of records
            order_by: Column to sort by
            ascending: Sort direction

        Returns:
            List of match records
        """
        try:
            query = self.client.table('jogos_resumo').select('*')

            if ascending:
                query = query.order(order_by, desc=False)
            else:
                query = query.order(order_by, desc=True)

            if limit:
                query = query.limit(limit)

            response = query.execute()

            return response.data

        except Exception as e:
            logger.error("Failed to retrieve matches", error=str(e))
            return []

    def search_matches(
        self,
        home_team: Optional[str] = None,
        away_team: Optional[str] = None,
        competition: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search matches with filters.

        Args:
            home_team: Home team name (partial match)
            away_team: Away team name (partial match)
            competition: Competition name (partial match)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            List of matching records
        """
        try:
            query = self.client.table('jogos_resumo').select('*')

            if home_team:
                query = query.ilike('time_mandante', f'%{home_team}%')

            if away_team:
                query = query.ilike('time_visitante', f'%{away_team}%')

            if competition:
                query = query.ilike('competicao', f'%{competition}%')

            if start_date:
                query = query.gte('data_jogo', start_date)

            if end_date:
                query = query.lte('data_jogo', end_date)

            response = query.execute()

            return response.data

        except Exception as e:
            logger.error("Failed to search matches", error=str(e))
            return []
```

**Files to Create:**
- `src/storage.py` - Supabase storage operations
- `src/database.py` - Supabase database operations
- `migrations/001_initial_schema.sql` - Database schema
- `scripts/migrate_csv_to_supabase.py` - Data migration utility

**Files to Modify:**
- `src/main.py` - Use new storage/database classes
- `src/scraper.py` - Upload PDFs after download
- `src/dashboard.py` - Read from database instead of CSV
- `tests/` - Add tests for storage and database

**Success Criteria:**
- ✅ Storage operations work reliably
- ✅ Database CRUD operations functional
- ✅ Transaction support implemented
- ✅ Error handling comprehensive
- ✅ Tests pass

---

#### **Milestone 2.3: Data Migration** ⏱️ 2-3 days
**Priority:** HIGH

**Tasks:**
- [ ] Create migration script `scripts/migrate_csv_to_supabase.py`
- [ ] Backup existing CSVs
- [ ] Migrate `jogos_resumo.csv` to database
- [ ] Migrate `receitas_detalhe.csv` to database
- [ ] Migrate `despesas_detalhe.csv` to database
- [ ] Upload existing PDFs to Supabase Storage
- [ ] Verify data integrity after migration
- [ ] Update `.gitignore` to exclude CSVs and PDFs
- [ ] Remove CSVs and PDFs from git history (optional)
- [ ] Update documentation

**Migration Script:**

```python
# scripts/migrate_csv_to_supabase.py
"""
Migrate existing CSV data and PDFs to Supabase.
Run once to migrate legacy data.
"""

import sys
from pathlib import Path
import pandas as pd
from tqdm import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from storage import SupabaseStorage
from database import SupabaseDatabase
import structlog

logger = structlog.get_logger(__name__)

def migrate_csvs_to_database():
    """Migrate CSV files to Supabase database."""

    db = SupabaseDatabase()

    # Migrate jogos_resumo
    print("Migrating jogos_resumo.csv...")
    df = pd.read_csv('csv/jogos_resumo.csv')

    for idx, row in tqdm(df.iterrows(), total=len(df)):
        match_data = {
            'id_jogo_cbf': row['id_jogo_cbf'],
            'data_jogo': row['data_jogo'],
            'time_mandante': row['time_mandante'],
            'time_visitante': row['time_visitante'],
            'estadio': row['estadio'],
            'competicao': row['competicao'],
            'publico_pagante': int(row['publico_pagante']) if pd.notna(row['publico_pagante']) else None,
            'publico_nao_pagante': int(row['publico_nao_pagante']) if pd.notna(row['publico_nao_pagante']) else None,
            'publico_total': int(row['publico_total']) if pd.notna(row['publico_total']) else None,
            'receita_bruta_total': float(row['receita_bruta_total']) if pd.notna(row['receita_bruta_total']) else None,
            'despesa_total': float(row['despesa_total']) if pd.notna(row['despesa_total']) else None,
            'resultado_liquido': float(row['resultado_liquido']) if pd.notna(row['resultado_liquido']) else None,
            'status': row.get('status', 'Sucesso'),
            'log_erro': row.get('log_erro', ''),
            's3_pdf_path': ''  # Will be updated when PDFs are migrated
        }

        try:
            if not db.match_exists(match_data['id_jogo_cbf']):
                db.add_match(match_data)
        except Exception as e:
            logger.error(f"Failed to migrate match {match_data['id_jogo_cbf']}: {e}")

    # Migrate receitas_detalhe
    print("\nMigrating receitas_detalhe.csv...")
    df_receitas = pd.read_csv('csv/receitas_detalhe.csv')

    # Group by id_jogo_cbf
    for id_jogo, group in tqdm(df_receitas.groupby('id_jogo_cbf')):
        revenue_details = []
        for _, row in group.iterrows():
            revenue_details.append({
                'source': row['source'],
                'quantity': int(row['quantity']) if pd.notna(row['quantity']) else None,
                'price': float(row['price']) if pd.notna(row['price']) else None,
                'amount': float(row['amount']) if pd.notna(row['amount']) else None
            })

        try:
            db.add_revenue_details(id_jogo, revenue_details)
        except Exception as e:
            logger.error(f"Failed to migrate revenue for {id_jogo}: {e}")

    # Migrate despesas_detalhe
    print("\nMigrating despesas_detalhe.csv...")
    df_despesas = pd.read_csv('csv/despesas_detalhe.csv')

    for id_jogo, group in tqdm(df_despesas.groupby('id_jogo_cbf')):
        expense_details = []
        for _, row in group.iterrows():
            expense_details.append({
                'category': row['category'],
                'amount': float(row['amount']) if pd.notna(row['amount']) else None
            })

        try:
            db.add_expense_details(id_jogo, expense_details)
        except Exception as e:
            logger.error(f"Failed to migrate expenses for {id_jogo}: {e}")

    print("\n✅ CSV migration complete!")

def migrate_pdfs_to_storage():
    """Upload existing PDFs to Supabase Storage."""

    storage = SupabaseStorage()
    db = SupabaseDatabase()

    pdf_dir = Path('pdfs')
    pdf_files = list(pdf_dir.glob('*.pdf'))

    print(f"\nMigrating {len(pdf_files)} PDFs to Supabase Storage...")

    for pdf_path in tqdm(pdf_files):
        # Extract year and ID from filename
        # Expected format: 14210b_2025.pdf
        filename = pdf_path.stem  # "14210b_2025"
        parts = filename.split('_')

        if len(parts) >= 2:
            id_jogo_cbf = filename
            year = int(parts[-1])
        else:
            logger.warning(f"Skipping invalid filename: {pdf_path.name}")
            continue

        try:
            # Upload to storage
            storage_url = storage.upload_pdf(pdf_path, year, id_jogo_cbf)

            # Update database with storage URL
            db.client.table('jogos_resumo').update({
                's3_pdf_path': storage_url
            }).eq('id_jogo_cbf', id_jogo_cbf).execute()

        except Exception as e:
            logger.error(f"Failed to migrate PDF {pdf_path.name}: {e}")

    print("\n✅ PDF migration complete!")

if __name__ == '__main__':
    print("=== CBF Robot Data Migration ===\n")
    print("This script will migrate your local CSV and PDF files to Supabase.")
    print("Make sure you have:")
    print("  1. SUPABASE_URL in your .env file")
    print("  2. SUPABASE_KEY in your .env file")
    print("  3. Created the database schema (migrations/001_initial_schema.sql)")
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    input()

    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    try:
        migrate_csvs_to_database()
        migrate_pdfs_to_storage()

        print("\n" + "="*50)
        print("✅ Migration completed successfully!")
        print("="*50)
        print("\nNext steps:")
        print("  1. Verify data in Supabase dashboard")
        print("  2. Update .gitignore to exclude csv/ and pdfs/")
        print("  3. Test the application with new storage")
        print("  4. (Optional) Remove old CSV/PDF files from git history")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        logger.error("Migration failed", error=str(e))
```

**Success Criteria:**
- ✅ All CSV data migrated to database
- ✅ All PDFs uploaded to Supabase Storage
- ✅ Data integrity verified
- ✅ Git repository cleaned up

---

### **PHASE 3: Natural Language Query Dashboard** (Week 5-6)

#### **Milestone 3.1: NLQ Engine** ⏱️ 3-4 days
**Priority:** MEDIUM

**Tasks:**
- [ ] Create `src/nlq.py` module for natural language queries
- [ ] Implement query understanding with Claude
- [ ] Convert natural language to SQL queries
- [ ] Add query validation and safety checks
- [ ] Implement caching for common queries
- [ ] Add query explanation feature
- [ ] Write unit tests for NLQ engine
- [ ] Document supported query types

**Implementation:**

```python
# src/nlq.py
"""
Natural Language Query (NLQ) engine for CBF Robot.
Converts natural language questions to SQL queries using Claude.
"""

import anthropic
from typing import Dict, Any, List, Optional
import structlog
import os
import re

logger = structlog.get_logger(__name__)

class NaturalLanguageQuery:
    """
    Processes natural language questions and converts them to SQL queries.

    Example questions:
    - "O que o Santos cobrou do Flamengo no seu jogo como visitante?"
    - "Qual foi o público médio do Corinthians em 2025?"
    - "Quais foram os 5 jogos com maior receita?"
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-haiku-4-5-20251001"

    def query(
        self,
        question: str,
        db: Any  # SupabaseDatabase instance
    ) -> Dict[str, Any]:
        """
        Process a natural language question and return results.

        Args:
            question: Natural language question
            db: Database instance

        Returns:
            Dict containing:
            - success: bool
            - sql: Generated SQL query
            - results: Query results
            - explanation: Natural language explanation of results
            - error: Error message (if failed)
        """
        try:
            # Step 1: Convert question to SQL
            sql_query = self._question_to_sql(question)

            if not sql_query:
                return {
                    "success": False,
                    "error": "Could not understand the question"
                }

            # Step 2: Validate SQL (safety check)
            if not self._is_safe_query(sql_query):
                return {
                    "success": False,
                    "error": "Query contains unsafe operations"
                }

            # Step 3: Execute query
            results = self._execute_sql(sql_query, db)

            # Step 4: Generate natural language explanation
            explanation = self._explain_results(question, results)

            return {
                "success": True,
                "sql": sql_query,
                "results": results,
                "explanation": explanation
            }

        except Exception as e:
            logger.error("NLQ failed", question=question, error=str(e))
            return {
                "success": False,
                "error": str(e)
            }

    def _question_to_sql(self, question: str) -> Optional[str]:
        """Convert natural language question to SQL query using Claude."""

        schema_description = """
Database Schema:

**Table: jogos_resumo**
- id_jogo_cbf (VARCHAR): Unique match ID
- data_jogo (DATE): Match date
- time_mandante (VARCHAR): Home team name
- time_visitante (VARCHAR): Away team name
- estadio (VARCHAR): Stadium name
- competicao (VARCHAR): Competition name
- publico_pagante (INTEGER): Paid attendance
- publico_nao_pagante (INTEGER): Non-paid attendance
- publico_total (INTEGER): Total attendance
- receita_bruta_total (DECIMAL): Total gross revenue
- despesa_total (DECIMAL): Total expenses
- resultado_liquido (DECIMAL): Net result (revenue - expenses)

**Table: receitas_detalhe**
- id_jogo_cbf (VARCHAR): Match ID (foreign key)
- source (VARCHAR): Revenue source (e.g., "Bilheteria", "Camarote")
- quantity (INTEGER): Number of tickets/items sold
- price (DECIMAL): Price per unit
- amount (DECIMAL): Total amount

**Table: despesas_detalhe**
- id_jogo_cbf (VARCHAR): Match ID (foreign key)
- category (VARCHAR): Expense category (e.g., "Arbitragem", "Segurança")
- amount (DECIMAL): Total amount

Common team names: Flamengo, Santos, Corinthians, São Paulo, Palmeiras, etc.
Competitions: "Brasileiro - Série A", "Copa do Brasil", etc.
"""

        prompt = f"""
Você é um especialista em SQL e futebol brasileiro.

Converta a seguinte pergunta em uma query SQL para PostgreSQL.

**Pergunta:** {question}

**Schema do Banco de Dados:**
{schema_description}

**Instruções:**
1. Retorne APENAS a query SQL, sem explicações
2. Use PostgreSQL syntax
3. Use JOINs quando necessário para combinar tabelas
4. Para "visitante" use WHERE time_visitante = '...'
5. Para "mandante" use WHERE time_mandante = '...'
6. Use ILIKE para busca case-insensitive: WHERE time_mandante ILIKE '%Santos%'
7. Para agregações, use SUM, AVG, COUNT, etc.
8. Limite resultados com LIMIT quando apropriado
9. Ordene resultados com ORDER BY quando relevante

**Exemplos:**

Pergunta: "O que o Santos cobrou do Flamengo no seu jogo como visitante?"
SQL:
SELECT
    jr.id_jogo_cbf,
    jr.data_jogo,
    jr.time_mandante,
    jr.time_visitante,
    jr.estadio,
    jr.receita_bruta_total,
    rd.source,
    rd.quantity,
    rd.price,
    rd.amount
FROM jogos_resumo jr
LEFT JOIN receitas_detalhe rd ON jr.id_jogo_cbf = rd.id_jogo_cbf
WHERE jr.time_mandante ILIKE '%Santos%'
  AND jr.time_visitante ILIKE '%Flamengo%'
ORDER BY jr.data_jogo DESC;

Pergunta: "Qual foi o público médio do Corinthians em 2025?"
SQL:
SELECT
    AVG(publico_total) as publico_medio,
    COUNT(*) as total_jogos
FROM jogos_resumo
WHERE (time_mandante ILIKE '%Corinthians%' OR time_visitante ILIKE '%Corinthians%')
  AND EXTRACT(YEAR FROM data_jogo) = 2025;

Agora converta a pergunta acima:
"""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.0,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            response_text = ""
            for block in message.content:
                if block.type == "text":
                    response_text += block.text

            # Extract SQL from response (remove markdown code blocks if present)
            sql = response_text.strip()
            sql = re.sub(r'^```sql\s*', '', sql)
            sql = re.sub(r'^```\s*', '', sql)
            sql = re.sub(r'\s*```$', '', sql)
            sql = sql.strip()

            logger.info("Generated SQL query", question=question, sql=sql)

            return sql

        except Exception as e:
            logger.error("Failed to generate SQL", question=question, error=str(e))
            return None

    def _is_safe_query(self, sql: str) -> bool:
        """
        Validate that SQL query is safe (read-only).
        Prevents DROP, DELETE, UPDATE, INSERT, etc.
        """
        sql_upper = sql.upper()

        # Forbidden keywords
        forbidden = [
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'TRUNCATE',
            'ALTER', 'CREATE', 'GRANT', 'REVOKE', 'EXEC',
            'EXECUTE', '--', ';--', '/*', '*/'
        ]

        for keyword in forbidden:
            if keyword in sql_upper:
                logger.warning(
                    "Unsafe SQL detected",
                    sql=sql,
                    keyword=keyword
                )
                return False

        # Must start with SELECT
        if not sql_upper.strip().startswith('SELECT'):
            return False

        return True

    def _execute_sql(
        self,
        sql: str,
        db: Any
    ) -> List[Dict[str, Any]]:
        """Execute SQL query against Supabase database."""
        try:
            # Use Supabase RPC to execute raw SQL
            response = db.client.rpc('execute_sql', {'query': sql}).execute()
            return response.data

        except Exception as e:
            logger.error("SQL execution failed", sql=sql, error=str(e))
            raise

    def _explain_results(
        self,
        question: str,
        results: List[Dict[str, Any]]
    ) -> str:
        """Generate natural language explanation of query results."""

        if not results:
            return "Não foram encontrados resultados para esta consulta."

        prompt = f"""
Você é um assistente amigável que explica resultados de consultas sobre futebol.

**Pergunta Original:** {question}

**Resultados (JSON):**
{results}

Forneça uma resposta em português brasileiro que:
1. Responda diretamente à pergunta
2. Seja concisa e clara
3. Use formatação de moeda para valores (ex: R$ 1.234.567,89)
4. Use formatação de números para público (ex: 10.543 pessoas)
5. Mencione datas se relevante

Exemplo:
"No jogo Santos x Flamengo em 15/03/2025, o Santos cobrou uma receita bruta total de R$ 2.500.000,00. As principais fontes foram:
- Bilheteria: R$ 1.800.000,00 (15.000 ingressos a R$ 120,00)
- Camarotes: R$ 500.000,00
- Estacionamento: R$ 200.000,00"
"""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.2,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            explanation = ""
            for block in message.content:
                if block.type == "text":
                    explanation += block.text

            return explanation.strip()

        except Exception as e:
            logger.error("Failed to generate explanation", error=str(e))
            return "Resultados obtidos, mas não foi possível gerar explicação."
```

**Supabase RPC Function:**
You'll need to create a PostgreSQL function in Supabase to execute dynamic SQL:

```sql
-- Run this in Supabase SQL Editor
CREATE OR REPLACE FUNCTION execute_sql(query TEXT)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result JSON;
BEGIN
    -- Security: Only allow SELECT queries
    IF NOT (query ~* '^\s*SELECT') THEN
        RAISE EXCEPTION 'Only SELECT queries are allowed';
    END IF;

    -- Execute query and return as JSON
    EXECUTE format('SELECT json_agg(t) FROM (%s) t', query) INTO result;

    RETURN COALESCE(result, '[]'::JSON);
END;
$$;
```

**Success Criteria:**
- ✅ NLQ engine converts questions to SQL
- ✅ Safety validation prevents dangerous queries
- ✅ Results formatted in natural language
- ✅ Tests pass for common query patterns

---

#### **Milestone 3.2: Interactive Dashboard UI** ⏱️ 3-4 days
**Priority:** MEDIUM

**Tasks:**
- [ ] Create `src/dashboard_nlq.py` - New Streamlit dashboard
- [ ] Add natural language query input box
- [ ] Display SQL query (for transparency)
- [ ] Show results in table format
- [ ] Add natural language explanation
- [ ] Implement query history
- [ ] Add example questions
- [ ] Add "Ask follow-up" feature
- [ ] Style UI with custom CSS
- [ ] Add loading states and error handling
- [ ] Deploy to Streamlit Cloud (optional)

**Implementation:**

```python
# src/dashboard_nlq.py
"""
Interactive dashboard with Natural Language Query support.
Run with: streamlit run src/dashboard_nlq.py
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from database import SupabaseDatabase
from nlq import NaturalLanguageQuery
import structlog

logger = structlog.get_logger(__name__)

# Page config
st.set_page_config(
    page_title="CBF Robot - Dashboard NLQ",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
.main-header {
    font-size: 3rem;
    font-weight: bold;
    color: #1E3A8A;
    text-align: center;
    margin-bottom: 2rem;
}
.query-box {
    background-color: #F0F9FF;
    padding: 1.5rem;
    border-radius: 0.5rem;
    border-left: 4px solid #3B82F6;
    margin: 1rem 0;
}
.result-box {
    background-color: #F0FDF4;
    padding: 1.5rem;
    border-radius: 0.5rem;
    border-left: 4px solid #10B981;
    margin: 1rem 0;
}
.sql-box {
    background-color: #F9FAFB;
    padding: 1rem;
    border-radius: 0.5rem;
    font-family: monospace;
    font-size: 0.9rem;
    border: 1px solid #E5E7EB;
}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'query_history' not in st.session_state:
    st.session_state.query_history = []

if 'db' not in st.session_state:
    st.session_state.db = SupabaseDatabase()

if 'nlq' not in st.session_state:
    st.session_state.nlq = NaturalLanguageQuery()

# Header
st.markdown('<div class="main-header">⚽ CBF Robot Dashboard</div>', unsafe_allow_html=True)
st.markdown("### Faça perguntas em linguagem natural sobre os borderôs da CBF")

# Example questions
with st.expander("📚 Exemplos de Perguntas"):
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **Receitas e Finanças:**
        - O que o Santos cobrou do Flamengo no seu jogo como visitante?
        - Quais foram os 5 jogos com maior receita em 2025?
        - Qual foi a receita média por jogo do Corinthians?
        - Mostre os jogos com resultado líquido negativo
        """)

    with col2:
        st.markdown("""
        **Público e Estatísticas:**
        - Qual foi o público médio do Palmeiras em casa?
        - Quais foram os 10 maiores públicos de 2025?
        - Compare o público do Flamengo em casa vs visitante
        - Qual estádio teve maior público médio?
        """)

# Main query input
st.markdown("---")
query_input = st.text_input(
    "🔍 Faça sua pergunta:",
    placeholder="Ex: O que o Santos cobrou do Flamengo no seu jogo como visitante?",
    key="query_input"
)

col1, col2, col3 = st.columns([1, 1, 4])

with col1:
    query_button = st.button("🚀 Consultar", type="primary", use_container_width=True)

with col2:
    clear_button = st.button("🗑️ Limpar Histórico", use_container_width=True)

if clear_button:
    st.session_state.query_history = []
    st.rerun()

# Process query
if query_button and query_input:
    with st.spinner("🤔 Processando sua pergunta..."):
        result = st.session_state.nlq.query(
            query_input,
            st.session_state.db
        )

        # Add to history
        st.session_state.query_history.insert(0, {
            "question": query_input,
            "result": result
        })

        # Limit history to 10 items
        st.session_state.query_history = st.session_state.query_history[:10]

# Display results
if st.session_state.query_history:
    st.markdown("---")
    st.markdown("## 📊 Resultados")

    for idx, item in enumerate(st.session_state.query_history):
        with st.container():
            # Question
            st.markdown(f'<div class="query-box"><strong>Pergunta:</strong> {item["question"]}</div>', unsafe_allow_html=True)

            result = item["result"]

            if result.get("success"):
                # Show explanation
                st.markdown(f'<div class="result-box">{result.get("explanation", "")}</div>', unsafe_allow_html=True)

                # Show SQL (collapsible)
                with st.expander("🔧 Ver SQL Gerado"):
                    st.code(result.get("sql", ""), language="sql")

                # Show results table
                if result.get("results"):
                    df = pd.DataFrame(result["results"])
                    st.dataframe(df, use_container_width=True, hide_index=True)

                    # Download button
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Baixar CSV",
                        data=csv,
                        file_name=f"cbf_query_{idx+1}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("Nenhum resultado encontrado.")

            else:
                st.error(f"❌ Erro: {result.get('error', 'Erro desconhecido')}")

            st.markdown("---")

# Sidebar with statistics
with st.sidebar:
    st.markdown("### 📈 Estatísticas Gerais")

    try:
        # Get total matches
        all_matches = st.session_state.db.get_all_matches(limit=1000)

        if all_matches:
            df_matches = pd.DataFrame(all_matches)

            # Total matches
            st.metric("Total de Jogos", len(df_matches))

            # Total revenue
            total_revenue = df_matches['receita_bruta_total'].sum()
            st.metric("Receita Total", f"R$ {total_revenue:,.2f}")

            # Average attendance
            avg_attendance = df_matches['publico_total'].mean()
            st.metric("Público Médio", f"{avg_attendance:,.0f}")

            # Competitions
            competitions = df_matches['competicao'].nunique()
            st.metric("Competições", competitions)

            st.markdown("---")
            st.markdown("### 🏆 Top Times por Receita")

            # Top teams by revenue (home games)
            top_teams = df_matches.groupby('time_mandante')['receita_bruta_total'].sum().sort_values(ascending=False).head(5)
            for team, revenue in top_teams.items():
                st.write(f"**{team}**: R$ {revenue:,.0f}")

    except Exception as e:
        st.error(f"Erro ao carregar estatísticas: {e}")

    st.markdown("---")
    st.markdown("### ℹ️ Sobre")
    st.info("""
    Este dashboard permite fazer perguntas em linguagem natural sobre os borderôs da CBF.

    Powered by:
    - 🤖 Claude Haiku 4.5
    - 🗄️ Supabase
    - 📊 Streamlit
    """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #6B7280;'>"
    "CBF Robot Dashboard | Desenvolvido com ❤️ por João Victor Fonseca Carvalho"
    "</div>",
    unsafe_allow_html=True
)
```

**Success Criteria:**
- ✅ Dashboard deployed and accessible
- ✅ Natural language queries work reliably
- ✅ Results displayed clearly
- ✅ Query history functional
- ✅ UI is intuitive and responsive

---

### **PHASE 4: Testing & Documentation** (Week 7)

#### **Milestone 4.1: Comprehensive Testing** ⏱️ 2-3 days
**Priority:** MEDIUM

**Tasks:**
- [ ] Add unit tests for `claude.py`
- [ ] Add unit tests for `storage.py`
- [ ] Add unit tests for `database.py`
- [ ] Add unit tests for `nlq.py`
- [ ] Add integration tests for full workflow
- [ ] Add performance tests
- [ ] Set up pytest configuration
- [ ] Configure test coverage reporting
- [ ] Run all tests and fix issues

**Files to Create:**
- `tests/test_claude.py`
- `tests/test_storage.py`
- `tests/test_database.py`
- `tests/test_nlq.py`
- `tests/test_integration.py`
- `pytest.ini`
- `.github/workflows/tests.yml` (CI/CD)

**Success Criteria:**
- ✅ Test coverage ≥80%
- ✅ All tests pass
- ✅ CI/CD pipeline configured

---

#### **Milestone 4.2: Documentation Updates** ⏱️ 1-2 days
**Priority:** MEDIUM

**Tasks:**
- [ ] Update README.md with Supabase setup
- [ ] Update README.md with Claude Haiku instructions
- [ ] Add NLQ dashboard usage guide
- [ ] Create ARCHITECTURE.md
- [ ] Create CONTRIBUTING.md
- [ ] Update code comments and docstrings
- [ ] Create deployment guide
- [ ] Record demo video (optional)

**Files to Update:**
- `README.md`
- `ROADMAP.md` (mark completed items)

**Files to Create:**
- `ARCHITECTURE.md`
- `CONTRIBUTING.md`
- `docs/DEPLOYMENT.md`
- `docs/NLQ_GUIDE.md`

**Success Criteria:**
- ✅ Documentation complete and clear
- ✅ Setup instructions tested by new user
- ✅ All features documented

---

## 📦 Dependencies to Add

Update `requirements.txt` with:

```txt
# Existing dependencies
beautifulsoup4>=4.12.0
requests>=2.31.0
pdfplumber>=0.10.0
pandas>=2.0.0
pydantic>=2.0.0
structlog>=23.1.0
pytest>=7.4.0
streamlit>=1.28.0
altair>=5.0.0

# NEW: API & Security
anthropic>=0.40.0
python-dotenv>=1.0.0
keyring>=24.0.0

# NEW: Cloud Storage & Database
supabase>=2.0.0
psycopg2-binary>=2.9.9  # PostgreSQL driver

# NEW: UI Enhancements
plotly>=5.18.0  # For interactive charts
streamlit-extras>=0.3.0

# Development
black>=23.0.0
mypy>=1.7.0
pytest-cov>=4.1.0
tqdm>=4.66.0  # Progress bars for migration scripts
```

---

## 🎯 Success Metrics

### **Phase 1 Success:**
- ✅ API keys secured (no plaintext)
- ✅ Claude Haiku 4.5 processes image PDFs successfully
- ✅ Extraction accuracy ≥95%
- ✅ Processing time <5s per PDF

### **Phase 2 Success:**
- ✅ All data migrated to Supabase
- ✅ Git repo size reduced by >90%
- ✅ No CSVs/PDFs in version control
- ✅ Database queries <100ms

### **Phase 3 Success:**
- ✅ NLQ answers 90%+ of questions correctly
- ✅ Dashboard loads in <3s
- ✅ User can ask follow-up questions
- ✅ Results formatted clearly

### **Phase 4 Success:**
- ✅ Test coverage ≥80%
- ✅ Documentation complete
- ✅ New contributors can set up in <30 minutes

---

## 🚧 Risk Mitigation

### **Risk 1: Claude API Cost**
**Mitigation:**
- Use Claude Haiku (most cost-effective)
- Implement caching for repeated queries
- Add monthly budget alerts

### **Risk 2: Image PDF Extraction Accuracy**
**Mitigation:**
- Create test suite of problematic PDFs
- Implement fallback to manual review
- Log low-confidence extractions for human review

### **Risk 3: Supabase Free Tier Limits**
**Mitigation:**
- Monitor usage in dashboard
- Implement data archiving after 1 year
- Plan for paid tier upgrade if needed

### **Risk 4: NLQ Generates Invalid SQL**
**Mitigation:**
- Comprehensive SQL validation
- Test suite of edge case questions
- Graceful error handling with suggestions

---

## 📞 Support & Maintenance

### **Monitoring:**
- Set up Supabase alerts for storage/DB limits
- Monitor Claude API usage and costs
- Track NLQ accuracy with user feedback

### **Backup:**
- Enable Supabase automatic backups
- Export data weekly to local backup
- Version control all schema changes

### **Updates:**
- Monthly dependency updates
- Quarterly feature reviews
- Annual security audit

---

## 🎉 Post-Launch Enhancements

### **Future Features (Post-Week 7):**

1. **Multi-user Support**
   - User authentication
   - Saved queries per user
   - Shared dashboards

2. **Advanced Analytics**
   - Predictive revenue modeling
   - Attendance forecasting
   - Anomaly detection

3. **Mobile App**
   - React Native or Flutter
   - Push notifications for new borderôs
   - Offline mode

4. **API Endpoints**
   - REST API for third-party integrations
   - Webhook support for new data
   - Rate limiting and API keys

5. **Data Quality Tools**
   - Automated anomaly detection
   - Bulk correction UI
   - Audit log

---

## 📋 Checklist Summary

### **Week 1-2: Foundation**
- [ ] Secure API keys with .env
- [ ] Implement Claude Haiku 4.5 integration
- [ ] Test image PDF extraction
- [ ] Update all imports and references

### **Week 3-4: Cloud Migration**
- [ ] Set up Supabase project
- [ ] Deploy database schema
- [ ] Implement storage/database layers
- [ ] Migrate existing data
- [ ] Clean up git repository

### **Week 5-6: NLQ Dashboard**
- [ ] Build NLQ engine
- [ ] Create interactive dashboard
- [ ] Test with real questions
- [ ] Deploy dashboard

### **Week 7: Polish**
- [ ] Write comprehensive tests
- [ ] Update all documentation
- [ ] Record demo
- [ ] Launch! 🚀

---

## 📚 Resources & References

### **Documentation:**
- [Anthropic Claude API Docs](https://docs.anthropic.com/)
- [Claude Haiku Model Card](https://www.anthropic.com/claude/haiku)
- [Supabase Documentation](https://supabase.com/docs)
- [Supabase Python Client](https://supabase.com/docs/reference/python)
- [Streamlit Documentation](https://docs.streamlit.io/)

### **Best Practices:**
- [SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [Secure API Key Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [PostgreSQL Performance Tips](https://wiki.postgresql.org/wiki/Performance_Optimization)

---

## ✅ Sign-off

**Project Owner:** João Victor Fonseca Carvalho
**Start Date:** [TBD]
**Target Completion:** [Start + 7 weeks]

---

*This roadmap is a living document and will be updated as the project progresses.*
