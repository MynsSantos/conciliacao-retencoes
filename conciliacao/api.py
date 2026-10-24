"""API HTTP: um robô RPA (ou qualquer sistema) envia os dois arquivos e recebe o Excel conciliado.

Rodar:  uvicorn conciliacao.api:app --reload
Docs:   http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import io

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response

from .motor import conciliar, resumo
from .relatorio import gerar_excel

app = FastAPI(title="Conciliação de Retenções", version="1.0.0")


async def _ler_tabela(arquivo: UploadFile) -> pd.DataFrame:
    conteudo = await arquivo.read()
    nome = (arquivo.filename or "").lower()
    if nome.endswith(".csv"):
        return pd.read_csv(io.BytesIO(conteudo), sep=None, engine="python")
    if nome.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(conteudo))
    raise HTTPException(415, f"Formato não suportado: {arquivo.filename} (use .csv ou .xlsx)")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/conciliar")
async def conciliar_endpoint(
    notas_fiscais: UploadFile = File(...),
    contas_pagar: UploadFile = File(...),
    formato: str = "xlsx",
):
    try:
        resultado = conciliar(await _ler_tabela(notas_fiscais), await _ler_tabela(contas_pagar))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    if formato == "json":
        return {
            "resumo": resumo(resultado).to_dict(orient="records"),
            "divergencias": resultado[resultado["status"] != "OK"].fillna("").to_dict(orient="records"),
        }
    return Response(
        gerar_excel(resultado),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="conciliacao_retencoes.xlsx"'},
    )
