"""Concilia as retenções esperadas (notas fiscais) com o que foi lançado no contas a pagar."""

from __future__ import annotations

import pandas as pd

from .regras import IMPOSTOS, calcular_retencoes

CHAVE = ["cnpj_fornecedor", "numero_nf"]
TOLERANCIA = 0.01

COLUNAS_NF = CHAVE + ["fornecedor", "data_emissao", "valor_bruto", "tipo_servico", "aliquota_iss", "optante_simples"]
COLUNAS_CP = CHAVE + ["id_titulo", "valor_bruto_cp"] + [f"{i}_lancado" for i in IMPOSTOS]


def _validar_colunas(df: pd.DataFrame, esperadas: list[str], nome: str) -> None:
    faltando = set(esperadas) - set(df.columns)
    if faltando:
        raise ValueError(f"Arquivo de {nome} sem as colunas: {sorted(faltando)}")


def _normalizar_chave(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["cnpj_fornecedor"] = df["cnpj_fornecedor"].astype(str).str.replace(r"\D", "", regex=True).str.zfill(14)
    df["numero_nf"] = df["numero_nf"].astype(str).str.strip().str.lstrip("0")
    return df


def calcular_esperado(notas: pd.DataFrame) -> pd.DataFrame:
    esperado = notas.apply(
        lambda r: calcular_retencoes(r.valor_bruto, r.tipo_servico, r.aliquota_iss, bool(r.optante_simples)),
        axis=1,
        result_type="expand",
    )
    esperado.columns = [f"{c}_esperado" for c in esperado.columns]
    return pd.concat([notas, esperado], axis=1)


def conciliar(notas: pd.DataFrame, contas_pagar: pd.DataFrame) -> pd.DataFrame:
    """Retorna uma linha por nota/título com o status da conciliação e as diferenças por imposto."""
    _validar_colunas(notas, COLUNAS_NF, "notas fiscais")
    _validar_colunas(contas_pagar, COLUNAS_CP, "contas a pagar")

    notas = calcular_esperado(_normalizar_chave(notas))
    cp = _normalizar_chave(contas_pagar)

    df = notas.merge(cp, on=CHAVE, how="outer", indicator=True)

    for imp in IMPOSTOS:
        df[f"{imp}_diferenca"] = (df[f"{imp}_lancado"].fillna(0) - df[f"{imp}_esperado"].fillna(0)).round(2)

    def classificar(linha) -> str:
        if linha["_merge"] == "left_only":
            return "NF sem lançamento no CP"
        if linha["_merge"] == "right_only":
            return "Título sem NF correspondente"
        if abs(linha["valor_bruto"] - linha["valor_bruto_cp"]) > TOLERANCIA:
            return "Valor bruto divergente"
        if any(abs(linha[f"{i}_diferenca"]) > TOLERANCIA for i in IMPOSTOS):
            return "Retenção divergente"
        return "OK"

    df["status"] = df.apply(classificar, axis=1)
    df["impostos_divergentes"] = df.apply(
        lambda l: ", ".join(i.upper() for i in IMPOSTOS if abs(l[f"{i}_diferenca"]) > TOLERANCIA)
        if l["status"] == "Retenção divergente" else "",
        axis=1,
    )
    return df.drop(columns="_merge").sort_values(["status", "fornecedor"], na_position="last").reset_index(drop=True)


def resumo(conciliado: pd.DataFrame) -> pd.DataFrame:
    conciliado = conciliado.assign(valor_ref=conciliado["valor_bruto"].fillna(conciliado["valor_bruto_cp"]))
    tabela = conciliado.groupby("status").agg(
        quantidade=("status", "size"),
        valor_bruto=("valor_ref", "sum"),
        diferenca_total=("status", lambda s: conciliado.loc[s.index, [f"{i}_diferenca" for i in IMPOSTOS]].sum().sum()),
    )
    return tabela.reset_index().round(2)
