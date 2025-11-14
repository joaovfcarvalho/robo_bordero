"""
Claude Haiku 4.5 integration for CBF Robot.
Handles PDF analysis and name normalization using Anthropic's Claude API.
"""

import anthropic
import base64
import time
import json
import re
from typing import Dict, Any, Optional, List
from pathlib import Path
import structlog
import os

logger = structlog.get_logger(__name__)


class ClaudeClient:
    """
    Claude Haiku 4.5 client for borderô analysis.
    Handles both native PDFs and image-based/scanned PDFs.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Claude client.

        Args:
            api_key: Anthropic API key. If not provided, loads from environment.
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')

        if not self.api_key:
            raise ValueError(
                "Anthropic API key not found. "
                "Set ANTHROPIC_API_KEY environment variable or pass api_key parameter."
            )

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-haiku-4-5-20251001"
        self.max_retries = 3
        self.requests_per_minute = 50  # Adjust based on your tier
        self.last_request_time = 0

        logger.info(
            "Claude client initialized",
            model=self.model,
            rate_limit=f"{self.requests_per_minute} RPM"
        )

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
            - success: bool (whether extraction succeeded)
            - data: Extracted match data (if successful)
            - error: Error message (if failed)
        """
        if retry_count is None:
            retry_count = self.max_retries

        # Encode PDF to base64
        pdf_base64 = base64.standard_b64encode(pdf_bytes).decode('utf-8')

        # Define extraction prompt optimized for Brazilian borderôs
        extraction_prompt = """
Você é um especialista em análise de borderôs da CBF (Confederação Brasileira de Futebol).

Analise este borderô e extraia as seguintes informações em formato JSON.

**ATENÇÃO ESPECIAL - DESAFIOS CONHECIDOS:**

1. **Nomes de Times - NORMALIZAÇÃO CONSCIENTE DE CONTEXTO**: Os times aparecem com diferentes formatos e precisam ser normalizados usando CONTEXTO da partida:

   **REGRAS DE DESAMBIGUAÇÃO OBRIGATÓRIAS:**
   - Use COMPETIÇÃO + ESTÁDIO + ADVERSÁRIO para identificar o time correto
   - NUNCA confie apenas no sufixo "SAF" ou nome do time

   **EXEMPLOS CRÍTICOS:**

   a) **Botafogo SAF/RJ vs Botafogo SP**:
      - Se a competição é SÉRIE A ou LIBERTADORES e o estádio está no RJ (Nilton Santos, Maracanã): → "Botafogo-RJ"
      - Se a competição é SÉRIE B ou SÉRIE C e o estádio está em SP (Ribeirão Preto, Araraquara): → "Botafogo-SP"
      - Se o adversário é time da Série A (Flamengo, Palmeiras): provavelmente → "Botafogo-RJ"
      - Se o adversário é time da Série B (Vila Nova, Avaí): provavelmente → "Botafogo-SP"

   b) **Nacional AM vs Nacional SP**:
      - Se estádio está em Manaus (Arena da Amazônia): → "Nacional-AM"
      - Se estádio está em São Paulo: → "Nacional-SP"

   c) **América-MG, América-RJ, América-RN**:
      - Arena Independência (Belo Horizonte): → "América-MG"
      - São Januário (Rio de Janeiro): → "América-RJ"
      - Machadão (Natal): → "América-RN"

   **REGRAS GERAIS:**
   - "SANTOS FUTEBOL CLUBE - SP" → normalizar para "Santos"
   - "CLUBE DE REGATAS DO FLAMENGO - RJ" → normalizar para "Flamengo"
   - "SÃO PAULO FUTEBOL CLUBE - SP" → normalizar para "São Paulo"
   - "SPORT CLUB CORINTHIANS PAULISTA - SP" → normalizar para "Corinthians"
   - Remova sufixos como "FC", "SAF", "S/A", "FUTEBOL CLUBE", "CLUB", etc.
   - Use o nome popular/comum do time
   - Mantenha estado SEMPRE que houver ambiguidade possível (ex: "Botafogo-RJ" vs "Botafogo-SP")

2. **Estádios**: Normalize os nomes dos estádios:
   - "ESTÁDIO MORUMBI - SÃO PAULO - SP" → normalizar para "Morumbi"
   - "MARACANÃ - RIO DE JANEIRO - RJ" → normalizar para "Maracanã"
   - Remova cidade e estado a menos que necessário para desambiguação
   - Mantenha acentos e caracteres especiais

3. **Competições**: Normalize os nomes:
   - "CAMPEONATO BRASILEIRO SÉRIE A 2025" → "Brasileiro - Série A"
   - "COPA DO BRASIL 2025" → "Copa do Brasil"
   - "CAMPEONATO BRASILEIRO SÉRIE B" → "Brasileiro - Série B"

4. **Valores Financeiros**:
   - Aceite tanto formato brasileiro (1.234,56) quanto internacional (1234.56)
   - Converta SEMPRE para float decimal (use ponto como separador)
   - Se o valor for "0,00" ou vazio, use 0.0
   - Alguns borderôs têm valores em formato de tabela ou espalhados

5. **Datas**:
   - Formato: DD/MM/YYYY (formato brasileiro)
   - Exemplo: "15/03/2025"

6. **Público**:
   - Extraia "pagante", "não pagante" e "total"
   - Se algum campo estiver ausente, use 0
   - Valores típicos: entre 1.000 e 60.000

7. **Tabelas de Receitas e Despesas**:
   - As receitas geralmente têm: tipo (ex: "Bilheteria"), quantidade, preço unitário, valor total
   - As despesas geralmente têm: categoria (ex: "Arbitragem", "Segurança"), valor
   - Extraia TODAS as linhas das tabelas, não apenas algumas

Retorne JSON EXATAMENTE neste formato:

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
      },
      {
        "source": "Camarotes",
        "quantity": 50,
        "price": 2000.0,
        "amount": 100000.0
      }
    ],
    "expense_details": [
      {
        "category": "Arbitragem",
        "amount": 15000.0
      },
      {
        "category": "Segurança",
        "amount": 32100.0
      }
    ]
  },
  "audience_statistics": {
    "paid_attendance": 10000,
    "non_paid_attendance": 500,
    "total_attendance": 10500
  }
}

**IMPORTANTE**:
- Se não conseguir extrair algum valor, use null
- Seja MUITO preciso com os números
- Extraia TODAS as linhas das tabelas de receitas e despesas
- Normalize todos os nomes conforme instruções acima
- Retorne APENAS o JSON, sem explicações adicionais
"""

        for attempt in range(1, retry_count + 1):
            try:
                self._rate_limit()

                logger.info(
                    "Calling Claude API",
                    attempt=attempt,
                    model=self.model,
                    pdf_size_kb=len(pdf_bytes) / 1024
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
                # Try to find JSON in response (handle markdown code blocks)
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())

                    logger.info(
                        "Successfully extracted data",
                        home_team=data.get('match_details', {}).get('home_team'),
                        away_team=data.get('match_details', {}).get('away_team'),
                        gross_revenue=data.get('financial_data', {}).get('gross_revenue')
                    )

                    return {
                        "success": True,
                        "data": data
                    }
                else:
                    raise ValueError("No JSON found in Claude response")

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
                        "error": f"Rate limit exceeded after {retry_count} attempts: {str(e)}"
                    }

            except anthropic.APIError as e:
                logger.error(
                    "Claude API error",
                    attempt=attempt,
                    error=str(e),
                    error_type=type(e).__name__
                )
                if attempt < retry_count:
                    backoff = 2 ** attempt
                    time.sleep(backoff)
                else:
                    return {
                        "success": False,
                        "error": f"API error: {str(e)}"
                    }

            except json.JSONDecodeError as e:
                logger.error(
                    "Failed to parse JSON from Claude response",
                    attempt=attempt,
                    error=str(e),
                    response_preview=response_text[:500] if 'response_text' in locals() else "N/A"
                )
                if attempt < retry_count:
                    time.sleep(2 ** attempt)
                else:
                    return {
                        "success": False,
                        "error": f"JSON parsing failed: {str(e)}"
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
        names: List[str],
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

        category_instructions = {
            "teams": """
**Regras para Times:**
- Use nome popular (ex: "Flamengo", "Santos", "São Paulo", "Corinthians")
- Remova "FC", "SAF", "S/A", "FUTEBOL CLUBE", "CLUB"
- Mantenha estado apenas se necessário para desambiguação:
  * "Botafogo-RJ" vs "Botafogo-PB"
  * "Nacional-AM" vs "Nacional-SP"
- Exemplos:
  * "CLUBE DE REGATAS DO FLAMENGO - RJ" → "Flamengo"
  * "SANTOS FUTEBOL CLUBE - SP" → "Santos"
  * "SPORT CLUB CORINTHIANS PAULISTA - SP" → "Corinthians"
  * "BOTAFOGO DE FUTEBOL E REGATAS - RJ" → "Botafogo-RJ"
""",
            "stadiums": """
**Regras para Estádios:**
- Use nome comum, sem cidade/estado
- Mantenha acentos e caracteres especiais
- Exemplos:
  * "MARACANÃ - RIO DE JANEIRO - RJ" → "Maracanã"
  * "ESTÁDIO MORUMBI - SÃO PAULO - SP" → "Morumbi"
  * "ARENA CORINTHIANS - SÃO PAULO - SP" → "Arena Corinthians"
  * "MINEIRÃO - BELO HORIZONTE - MG" → "Mineirão"
""",
            "competitions": """
**Regras para Competições:**
- Formato: "Competição - Divisão"
- Remova anos
- Exemplos:
  * "CAMPEONATO BRASILEIRO SÉRIE A 2025" → "Brasileiro - Série A"
  * "COPA DO BRASIL 2025" → "Copa do Brasil"
  * "CAMPEONATO BRASILEIRO SÉRIE B" → "Brasileiro - Série B"
  * "LIBERTADORES DA AMÉRICA" → "Libertadores"
"""
        }

        instructions = category_instructions.get(category, "")

        prompt = f"""
Você é um especialista em futebol brasileiro.

Normalize os seguintes nomes de **{category}** para formatos padronizados e curtos.

{instructions}

**Nomes existentes (mantenha consistência):**
{json.dumps(existing_mappings, ensure_ascii=False, indent=2)}

**Nomes para normalizar:**
{json.dumps(names, ensure_ascii=False, indent=2)}

Retorne APENAS JSON no formato:
{{
  "Nome Original 1": "Nome Normalizado 1",
  "Nome Original 2": "Nome Normalizado 2"
}}
"""

        try:
            self._rate_limit()

            logger.info(
                "Calling Claude for name normalization",
                category=category,
                count=len(names)
            )

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


def setup_client(api_key: Optional[str] = None) -> ClaudeClient:
    """
    Create and return a Claude client instance.

    Args:
        api_key: Optional API key. If not provided, loads from environment.

    Returns:
        Configured ClaudeClient instance
    """
    return ClaudeClient(api_key=api_key)


def analyze_pdf_with_claude(pdf_bytes: bytes, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to analyze a PDF using Claude.
    Maintains backward compatibility with gemini.py interface.

    Args:
        pdf_bytes: Raw PDF bytes
        api_key: Optional API key

    Returns:
        Dict with extraction results
    """
    client = ClaudeClient(api_key=api_key)
    return client.analyze_pdf(pdf_bytes)
