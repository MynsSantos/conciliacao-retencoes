"""Exporta a conciliação para um Excel formatado (Resumo, Divergências, Detalhe)."""

from __future__ import annotations

import io

import pandas as pd

from .motor import resumo
from .regras import IMPOSTOS

CORES_STATUS = {
    "OK": "#C6EFCE",
    "Retenção divergente": "#FFEB9C",
    "Valor bruto divergente": "#FFEB9C",
    "NF sem lançamento no CP": "#FFC7CE",
    "Título sem NF correspondente": "#FFC7CE",
}

COLUNAS_DIVERGENCIAS = (
    ["status", "impostos_divergentes", "fornecedor", "cnpj_fornecedor", "numero_nf", "id_titulo", "valor_bruto"]
    + [f"{i}_diferenca" for i in IMPOSTOS]
)


def _escrever(writer, df: pd.DataFrame, aba: str) -> None:
    df.to_excel(writer, sheet_name=aba, index=False)
    ws = writer.sheets[aba]
    book = writer.book
    cabecalho = book.add_format({"bold": True, "bg_color": "#1F4E78", "font_color": "white", "border": 1})
    moeda = book.add_format({"num_format": "#,##0.00"})

    for col, nome in enumerate(df.columns):
        ws.write(0, col, nome, cabecalho)
        largura = max(len(str(nome)), *(len(str(v)) for v in df[nome].head(200))) + 2
        fmt = moeda if pd.api.types.is_float_dtype(df[nome]) else None
        ws.set_column(col, col, min(largura, 45), fmt)

    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, len(df), len(df.columns) - 1)

    if "status" in df.columns and len(df):
        col = df.columns.get_loc("status")
        for status, cor in CORES_STATUS.items():
            ws.conditional_format(1, col, len(df), col, {
                "type": "cell", "criteria": "==", "value": f'"{status}"',
                "format": book.add_format({"bg_color": cor}),
            })


def gerar_excel(conciliado: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        _escrever(writer, resumo(conciliado), "Resumo")
        _escrever(writer, conciliado.loc[conciliado["status"] != "OK", COLUNAS_DIVERGENCIAS], "Divergencias")
        _escrever(writer, conciliado, "Detalhe")
    return buffer.getvalue()
