"""Regras de retenção na fonte sobre serviços tomados.

⚠️ Tabela SIMPLIFICADA, para demonstração. Alíquotas e enquadramentos reais
dependem do código de serviço, do regime do prestador, do município e da
legislação vigente. Ajuste ``TABELA_SERVICOS`` à realidade de cada empresa.
"""

from __future__ import annotations

from dataclasses import dataclass

LIMITE_DISPENSA = 10.00  # valores de IRRF/CSRF até R$ 10,00 não são retidos

ALIQ_PIS, ALIQ_COFINS, ALIQ_CSLL = 0.0065, 0.03, 0.01


@dataclass(frozen=True)
class RegraServico:
    inss: float   # alíquota de INSS (cessão de mão de obra/empreitada)
    irrf: float   # alíquota de IRRF
    csrf: bool    # sujeito a PIS/COFINS/CSLL retidos


TABELA_SERVICOS: dict[str, RegraServico] = {
    "consultoria": RegraServico(inss=0.00, irrf=0.015, csrf=True),
    "limpeza": RegraServico(inss=0.11, irrf=0.01, csrf=True),
    "vigilancia": RegraServico(inss=0.11, irrf=0.01, csrf=True),
    "manutencao": RegraServico(inss=0.11, irrf=0.015, csrf=True),
    "transporte": RegraServico(inss=0.00, irrf=0.00, csrf=False),
}

IMPOSTOS = ["iss", "inss", "irrf", "pis", "cofins", "csll"]


def _arred(v: float) -> float:
    return round(v + 1e-9, 2)


def calcular_retencoes(valor: float, tipo_servico: str, aliquota_iss: float, optante_simples: bool) -> dict[str, float]:
    """Retenções esperadas para uma nota fiscal."""
    try:
        regra = TABELA_SERVICOS[tipo_servico]
    except KeyError as exc:
        raise ValueError(f"Tipo de serviço sem regra cadastrada: {tipo_servico}") from exc

    ret = {imp: 0.0 for imp in IMPOSTOS}
    ret["iss"] = _arred(valor * aliquota_iss)
    ret["inss"] = _arred(valor * regra.inss)

    if not optante_simples:  # optantes do Simples não sofrem IRRF/CSRF sobre esses serviços
        irrf = _arred(valor * regra.irrf)
        ret["irrf"] = irrf if irrf > LIMITE_DISPENSA else 0.0

        if regra.csrf:
            pis, cofins, csll = (_arred(valor * a) for a in (ALIQ_PIS, ALIQ_COFINS, ALIQ_CSLL))
            if pis + cofins + csll > LIMITE_DISPENSA:
                ret.update(pis=pis, cofins=cofins, csll=csll)
    return ret
