from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field

class ClassificacaoRequest(BaseModel):
    dataset_path: str
    text_column: str
    id_column: Optional[str] = None

    canal_column: Optional[str] = Field(default=None, description="Nome da coluna com o canal (ex.: 'canal').")
    prioridade_column: Optional[str] = Field(default=None, description="Nome da coluna com a prioridade (ex.: 'prioridade').")

    categories: List[str]
    max_rows: Optional[int] = 100
    temperature: Optional[float] = 0.0
    resume_locale: Optional[str] = "pt-BR"
    output_csv_path: Optional[str] = None
    # CSV
    csv_sep: Optional[str] = Field(default=None, description="Separador (';', ',', '\\t' etc.). Autodetecta se omitido.")
    csv_encoding: Optional[str] = Field(default=None, description="Encoding (ex.: 'utf-8-sig', 'latin-1'). Autodetecta se omitido.")
    # OpenAI
    openai_model: str = Field(default="gpt-4o-mini", description="Modelo OpenAI a utilizar.")
