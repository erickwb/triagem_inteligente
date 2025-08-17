# app/services/pipeline.py
from __future__ import annotations

import asyncio
import os
from typing import List, Optional, Tuple

import pandas as pd

from app.core.prompt import SYSTEM_TEMPLATE, USER_TEMPLATE
from app.schemas.responses import ItemResult
from app.services.openai_client import OpenAIClient
from fastapi import HTTPException

def _safe_json_parse(s: str) -> dict:
    import json
    s = (s or "").strip()
    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        s = s[start : end + 1]
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return {"summary": s[:512], "category": "UNPARSEABLE"}

def _build_extra_context(canal: Optional[str], prioridade: Optional[str]) -> str:
    """
    Monta um bloco textual com canal e prioridade quando disponíveis.
    Retorna string terminada por dupla quebra de linha se houver conteúdo; caso contrário, string vazia.
    """
    parts = []
    if canal not in (None, "", "nan"):
        parts.append(f"CANAL: {canal}")
    if prioridade not in (None, "", "nan"):
        parts.append(f"PRIORIDADE: {prioridade}")
    return ("DADOS CONTEXTUAIS:\n" + "\n".join(parts) + "\n\n") if parts else ""

async def _inference_row(
    client: OpenAIClient,
    text: str,
    locale: str,
    categories: List[str],
    canal: Optional[str],
    prioridade: Optional[str],
) -> Tuple[str, str]:
    extra_context = _build_extra_context(canal, prioridade)
    user = USER_TEMPLATE.format(
        text=text,
        locale=locale,
        categories=categories,
        extra_context=extra_context
    )
    reply = await client.complete(SYSTEM_TEMPLATE, user)
    parsed = _safe_json_parse(reply.text)
    summary = str(parsed.get("summary") or "").strip()
    category = str(parsed.get("category") or "").strip()
    norm = {c.lower(): c for c in categories}
    if category.lower() in norm:
        category = norm[category.lower()]
    return summary, category

async def run_pipeline(
    df: pd.DataFrame,
    text_column: str,
    id_column: Optional[str],
    categories: List[str],
    locale: str,
    temperature: float,
    openai_model: str,
    output_csv_path: Optional[str],
    canal_column: Optional[str],           
    prioridade_column: Optional[str]      
) -> Tuple[List[ItemResult], str]:

    client = OpenAIClient(model=openai_model, temperature=temperature)
    max_conc = int(os.environ.get("MAX_CONCURRENCY", "4"))
    sem = asyncio.Semaphore(max_conc)

    def _get(row, colname: Optional[str]) -> Optional[str]:
        if not colname:
            return None
        val = row.get(colname)
        return None if pd.isna(val) else str(val)

    async def task_row(row) -> ItemResult:
        text = str(row[text_column])
        item_id = str(row[id_column]) if id_column else None
        canal = _get(row, canal_column)
        prioridade = _get(row, prioridade_column)
        async with sem:
            summary, category = await _inference_row(
                client, text, locale, categories, canal, prioridade
            )
        return ItemResult(id=item_id, summary=summary, category=category)

    tasks = [task_row(row) for _, row in df.iterrows()]
    results: List[ItemResult] = await asyncio.gather(*tasks)

    if output_csv_path:
        out = df.copy()
        out["summary"] = [it.summary for it in results]
        out["predicted_category"] = [it.category for it in results]
        try:
            out.to_csv(output_csv_path, index=False)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Falha ao escrever CSV de saída: {e}")

    return results, openai_model
 