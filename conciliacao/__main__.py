"""CLI: python -m conciliacao <notas.csv> <contas_pagar.csv> [--saida output/conciliacao.xlsx]"""

import argparse
from pathlib import Path

import pandas as pd

from .motor import conciliar, resumo
from .relatorio import gerar_excel


def _ler(caminho: Path) -> pd.DataFrame:
    return pd.read_excel(caminho) if caminho.suffix.lower() in (".xlsx", ".xls") else pd.read_csv(caminho, sep=None, engine="python")


def main() -> None:
    parser = argparse.ArgumentParser(description="Concilia retenções das NFs com o contas a pagar.")
    parser.add_argument("notas", type=Path)
    parser.add_argument("contas_pagar", type=Path)
    parser.add_argument("--saida", type=Path, default=Path("output/conciliacao.xlsx"))
    args = parser.parse_args()

    resultado = conciliar(_ler(args.notas), _ler(args.contas_pagar))
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_bytes(gerar_excel(resultado))

    print(resumo(resultado).to_string(index=False))
    print(f"\nRelatório: {args.saida}")


if __name__ == "__main__":
    main()
