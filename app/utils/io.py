from __future__ import annotations

from typing import Optional
import pandas as pd
from fastapi import HTTPException

def load_dataframe(path: str, sep: Optional[str] = None, encoding: Optional[str] = None) -> pd.DataFrame:
    """Leitura robusta de CSV com autodetecção de separador e encoding."""
    enc_try = [encoding] if encoding else ["utf-8-sig", "utf-8", "latin-1"]

    if sep is not None:
        last_err = None
        for enc in enc_try:
            try:
                return pd.read_csv(path, sep=sep, encoding=enc)
            except Exception as e:
                last_err = e
        raise HTTPException(status_code=400, detail=f"Falha ao ler CSV com sep='{sep}': {last_err}")

    for enc in enc_try:
        try:
            df = pd.read_csv(path, sep=None, engine='python', encoding=enc)
            if df.shape[1] == 1:
                only_col = str(df.columns[0])
                if ';' in only_col:
                    try:
                        return pd.read_csv(path, sep=';', encoding=enc)
                    except Exception:
                        pass
                if ',' in only_col:
                    try:
                        return pd.read_csv(path, sep=',', encoding=enc)
                    except Exception:
                        pass
            return df
        except Exception:
            continue

    raise HTTPException(status_code=400, detail="Não foi possível ler o CSV: verifique csv_sep/csv_encoding.")
