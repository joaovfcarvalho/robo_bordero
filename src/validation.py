import os
import datetime
from pydantic import BaseModel, ValidationError
from typing import List, Optional, Any
from .utils import DataValidationError, handle_error

# Ensure reports directory exists
REPORT_DIR = os.path.join(os.getcwd(), 'reports')
os.makedirs(REPORT_DIR, exist_ok=True)

def _write_quality_report(schema_name: str, errors: Any):
    report_file = os.path.join(
        REPORT_DIR,
        f'data_quality_{schema_name}_{datetime.date.today().isoformat()}.json'
    )
    with open(report_file, 'w', encoding='utf-8') as f:
        if hasattr(errors, 'json'):
            f.write(errors.json())
        else:
            f.write(str(errors))

class SummaryModel(BaseModel):
    id_jogo_cbf: str
    data_jogo: Optional[str]
    time_mandante: Optional[str]
    time_visitante: Optional[str]
    estadio: Optional[str]
    competicao: Optional[str]
    publico_pagante: Optional[int]
    publico_nao_pagante: Optional[int]
    publico_total: Optional[int]
    receita_bruta_total: Optional[float]
    despesa_total: Optional[float]
    resultado_liquido: Optional[float]
    caminho_pdf_local: str
    data_processamento: str
    status: str
    log_erro: Optional[str]

class RevenueDetailModel(BaseModel):
    id_jogo_cbf: str
    source: Any
    quantity: int
    price: float
    amount: float

class ExpenseDetailModel(BaseModel):
    id_jogo_cbf: str
    category: Any
    amount: float


def validate_summary(rows: List[dict]) -> List[dict]:
    try:
        validated = [SummaryModel(**row).dict() for row in rows]
        return validated
    except ValidationError as ve:
        _write_quality_report('summary', ve)
        raise DataValidationError('Summary data validation failed', {'errors': ve.errors()})


def validate_revenue(rows: List[dict]) -> List[dict]:
    try:
        validated = [RevenueDetailModel(**row).dict() for row in rows]
        return validated
    except ValidationError as ve:
        _write_quality_report('revenue', ve)
        raise DataValidationError('Revenue detail data validation failed', {'errors': ve.errors()})


def validate_expense(rows: List[dict]) -> List[dict]:
    try:
        validated = [ExpenseDetailModel(**row).dict() for row in rows]
        return validated
    except ValidationError as ve:
        _write_quality_report('expense', ve)
        raise DataValidationError('Expense detail data validation failed', {'errors': ve.errors()})
