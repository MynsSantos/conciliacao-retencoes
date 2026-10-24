"""Gera exemplos/notas_fiscais.csv e exemplos/contas_pagar.csv com dados SINTÉTICOS.

Os erros são inseridos de propósito (retenção esquecida, alíquota errada, título
duplicado, NF não lançada) para demonstrar a conciliação.
"""

import random
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conciliacao.regras import IMPOSTOS, TABELA_SERVICOS, calcular_retencoes  # noqa: E402

PASTA = Path(__file__).resolve().parents[1] / "exemplos"
PREFIXOS = ["Alfa", "Beta", "Gama", "Delta", "Epsilon", "Zeta", "Omega", "Sigma"]
SUFIXOS = ["Servicos", "Consultoria", "Facilities", "Solucoes", "Tecnica"]


def gerar(n_notas: int = 40, semente: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    rnd = random.Random(semente)
    fornecedores = [
        {
            "fornecedor": f"{p} {s} Ficticia LTDA",
            "cnpj_fornecedor": "".join(rnd.choices("0123456789", k=12)) + "00",
            "tipo_servico": rnd.choice(list(TABELA_SERVICOS)),
            "aliquota_iss": rnd.choice([0.02, 0.03, 0.05]),
            "optante_simples": rnd.random() < 0.2,
        }
        for p in PREFIXOS for s in rnd.sample(SUFIXOS, 1)
    ]

    notas, titulos = [], []
    for i in range(n_notas):
        f = rnd.choice(fornecedores)
        valor = round(rnd.uniform(300, 25000), 2)
        nota = {**f, "numero_nf": str(1000 + i), "valor_bruto": valor,
                "data_emissao": (date(2026, 10, 1) + timedelta(days=rnd.randint(0, 20))).isoformat()}
        notas.append(nota)

        ret = calcular_retencoes(valor, f["tipo_servico"], f["aliquota_iss"], f["optante_simples"])
        titulo = {"id_titulo": f"CP-{5000 + i}", "cnpj_fornecedor": f["cnpj_fornecedor"],
                  "numero_nf": nota["numero_nf"], "valor_bruto_cp": valor,
                  **{f"{k}_lancado": v for k, v in ret.items()}}

        # --- erros propositais ---
        sorteio = rnd.random()
        if sorteio < 0.08:
            continue                                   # NF não lançada
        if sorteio < 0.16:
            titulo["inss_lancado"] = 0.0               # INSS esquecido
        elif sorteio < 0.22:
            titulo["iss_lancado"] = round(valor * 0.05, 2)  # alíquota de ISS errada
        elif sorteio < 0.26:
            titulo["valor_bruto_cp"] = round(valor * 0.9, 2)  # digitação do bruto
        titulos.append(titulo)

    # título sem nota correspondente
    titulos.append({"id_titulo": "CP-9999", "cnpj_fornecedor": "".join(rnd.choices("0123456789", k=12)) + "00",
                    "numero_nf": "99999", "valor_bruto_cp": 1200.0, **{f"{k}_lancado": 0.0 for k in IMPOSTOS}})

    return pd.DataFrame(notas), pd.DataFrame(titulos)


if __name__ == "__main__":
    PASTA.mkdir(exist_ok=True)
    nf, cp = gerar()
    nf.to_csv(PASTA / "notas_fiscais.csv", index=False)
    cp.to_csv(PASTA / "contas_pagar.csv", index=False)
    print(f"{len(nf)} notas e {len(cp)} títulos gerados em {PASTA}")
