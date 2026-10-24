import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from conciliacao.api import app
from conciliacao.motor import conciliar
from conciliacao.regras import calcular_retencoes
from conciliacao.relatorio import gerar_excel
from scripts.gerar_dados_sinteticos import gerar


def test_retencoes_limpeza():
    r = calcular_retencoes(10_000, "limpeza", 0.05, optante_simples=False)
    assert r == {"iss": 500.0, "inss": 1100.0, "irrf": 100.0, "pis": 65.0, "cofins": 300.0, "csll": 100.0}


def test_dispensa_abaixo_de_10_reais():
    r = calcular_retencoes(200, "consultoria", 0.02, optante_simples=False)
    assert r["irrf"] == 0 and r["pis"] == 0  # 3,00 de IRRF e 9,30 de CSRF ficam dispensados


def test_optante_simples_sem_irrf_csrf():
    r = calcular_retencoes(10_000, "limpeza", 0.02, optante_simples=True)
    assert r["irrf"] == r["cofins"] == 0 and r["inss"] == 1100


def test_tipo_desconhecido():
    with pytest.raises(ValueError):
        calcular_retencoes(100, "padaria", 0.02, False)


def _base():
    nf = pd.DataFrame([{
        "cnpj_fornecedor": "12.345.678/0001-00", "numero_nf": "00123", "fornecedor": "Alfa Ficticia",
        "data_emissao": "2026-10-01", "valor_bruto": 10_000.0, "tipo_servico": "limpeza",
        "aliquota_iss": 0.05, "optante_simples": False,
    }])
    cp = pd.DataFrame([{
        "cnpj_fornecedor": "12345678000100", "numero_nf": "123", "id_titulo": "CP-1", "valor_bruto_cp": 10_000.0,
        "iss_lancado": 500.0, "inss_lancado": 1100.0, "irrf_lancado": 100.0,
        "pis_lancado": 65.0, "cofins_lancado": 300.0, "csll_lancado": 100.0,
    }])
    return nf, cp


def test_chave_normalizada_e_ok():
    nf, cp = _base()
    assert conciliar(nf, cp)["status"].tolist() == ["OK"]


def test_inss_esquecido():
    nf, cp = _base()
    cp.loc[0, "inss_lancado"] = 0
    linha = conciliar(nf, cp).iloc[0]
    assert linha["status"] == "Retenção divergente"
    assert linha["impostos_divergentes"] == "INSS" and linha["inss_diferenca"] == -1100


def test_nf_sem_titulo_e_titulo_sem_nf():
    nf, cp = _base()
    cp.loc[0, "numero_nf"] = "999"
    assert sorted(conciliar(nf, cp)["status"]) == ["NF sem lançamento no CP", "Título sem NF correspondente"]


def test_coluna_faltando():
    nf, cp = _base()
    with pytest.raises(ValueError, match="colunas"):
        conciliar(nf.drop(columns="tipo_servico"), cp)


def test_dados_sinteticos_geram_todos_os_status():
    nf, cp = gerar()
    status = set(conciliar(nf, cp)["status"])
    assert {"OK", "Retenção divergente", "NF sem lançamento no CP", "Título sem NF correspondente"} <= status
    assert gerar_excel(conciliar(nf, cp))[:2] == b"PK"  # xlsx é um zip


def test_api():
    nf, cp = gerar()
    cliente = TestClient(app)
    arquivos = {
        "notas_fiscais": ("nf.csv", nf.to_csv(index=False).encode(), "text/csv"),
        "contas_pagar": ("cp.csv", cp.to_csv(index=False).encode(), "text/csv"),
    }
    r = cliente.post("/conciliar", files=arquivos)
    assert r.status_code == 200 and r.content[:2] == b"PK"
    abas = pd.read_excel(io.BytesIO(r.content), sheet_name=None)
    assert set(abas) == {"Resumo", "Divergencias", "Detalhe"}

    r = cliente.post("/conciliar?formato=json", files=arquivos)
    assert r.status_code == 200 and r.json()["resumo"]
