from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel

class ItemResult(BaseModel):
    id: Optional[str] = None
    summary: str
    category: str

class ClassificacaoResponse(BaseModel):
    provider: Literal["openai"] = "openai"
    model: str
    n_rows: int
    seconds_total: float
    results: List[ItemResult]
    output_csv_path: Optional[str] = None
