from __future__ import annotations

from fastapi import APIRouter, HTTPException
from app.schemas.requests import ClassificacaoRequest
from app.schemas.responses import ClassificacaoResponse
from app.services.pipeline import run_pipeline
from app.utils.io import load_dataframe

import os
import time

router = APIRouter(tags=["classificacao"])

@router.post("/classificacao", response_model=ClassificacaoResponse, summary="Classificar tickets com OpenAI")
async def classificacao(req: ClassificacaoRequest):
    if not os.path.exists(req.dataset_path):
        raise HTTPException(status_code=400, detail=f"Arquivo não encontrado: {req.dataset_path}")

    try:
        df = load_dataframe(req.dataset_path, sep=req.csv_sep, encoding=req.csv_encoding)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Falha ao ler CSV: {e}")

    cols = list(df.columns)
    # obrigatória
    if req.text_column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Coluna de texto '{req.text_column}' não existe. Colunas disponíveis: {cols}")
    # opcionais
    if req.id_column and req.id_column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Coluna id '{req.id_column}' não existe. Colunas disponíveis: {cols}")
    if req.canal_column and req.canal_column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Coluna canal '{req.canal_column}' não existe. Colunas disponíveis: {cols}")
    if req.prioridade_column and req.prioridade_column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Coluna prioridade '{req.prioridade_column}' não existe. Colunas disponíveis: {cols}")

    # selecionar apenas o necessário
    keep = [req.text_column]
    if req.id_column: keep.append(req.id_column)
    if req.canal_column: keep.append(req.canal_column)
    if req.prioridade_column: keep.append(req.prioridade_column)
    work_df = df[keep].copy()

    if req.max_rows is not None:
        work_df = work_df.head(int(req.max_rows))

    t0 = time.perf_counter()
    items, model_used = await run_pipeline(
        df=work_df,
        text_column=req.text_column,
        id_column=req.id_column,
        categories=req.categories,
        locale=req.resume_locale or "pt-BR",
        temperature=req.temperature or 0.0,
        openai_model=req.openai_model,
        output_csv_path=req.output_csv_path,
        canal_column=req.canal_column,                
        prioridade_column=req.prioridade_column       
    )
    t1 = time.perf_counter()

    return ClassificacaoResponse(
        provider="openai",
        model=model_used,
        n_rows=len(items),
        seconds_total=(t1 - t0),
        results=items,
        output_csv_path=req.output_csv_path
    )
