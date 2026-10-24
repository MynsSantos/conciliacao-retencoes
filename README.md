# Conciliação de Retenções Tributárias × Contas a Pagar

Confere automaticamente se as **retenções na fonte** (ISS, INSS, IRRF, PIS, COFINS e CSLL) das notas fiscais de serviço foram **lançadas corretamente no contas a pagar** e entrega um **Excel pronto para o analista** com as divergências destacadas. Disponível como **CLI** e como **API FastAPI**, para ser chamada por um robô RPA.

> Projeto de portfólio inspirado em automações contábeis que desenvolvi profissionalmente. Código escrito do zero, com dados **sintéticos**. As regras tributárias são simplificadas e servem só para demonstração.

## O problema

Todo fechamento mensal, a contabilidade precisa conferir nota por nota se o INSS de 11% sobre cessão de mão de obra foi retido, se a alíquota de ISS do município está certa, se a CSRF respeitou a dispensa de até R$ 10,00... Feito à mão, em planilhas, isso leva dias e erros viram multa.

## O que o projeto faz

1. **Calcula a retenção esperada** de cada NF a partir de uma tabela de regras configurável (`regras.py`): tipo de serviço, alíquota de ISS, optante do Simples e limite de dispensa
2. **Normaliza as chaves** (CNPJ com ou sem máscara, número da NF com zeros à esquerda) e cruza com o contas a pagar via `pandas.merge` (outer join)
3. **Classifica cada linha**: `OK`, `Retenção divergente` (e quais impostos), `Valor bruto divergente`, `NF sem lançamento no CP` e `Título sem NF correspondente`
4. **Gera o Excel** com as abas *Resumo*, *Divergências* e *Detalhe*: cabeçalho formatado, filtros, painel congelado e cores por status

## Executando

```bash
pip install -r requirements.txt
python scripts/gerar_dados_sinteticos.py   # cria exemplos/*.csv com erros propositais

python -m conciliacao exemplos/notas_fiscais.csv exemplos/contas_pagar.csv
```

```
                      status  quantidade  valor_bruto  diferenca_total
     NF sem lançamento no CP           5     61977.62        -12933.97
                          OK          28    348147.96             0.00
         Retenção divergente           5     71213.05         -2951.61
Título sem NF correspondente           1      1200.00             0.00
      Valor bruto divergente           2     32277.69             0.00
```

### Como API

```bash
uvicorn conciliacao.api:app --reload
# Swagger em http://127.0.0.1:8000/docs

curl -F notas_fiscais=@exemplos/notas_fiscais.csv \
     -F contas_pagar=@exemplos/contas_pagar.csv \
     http://127.0.0.1:8000/conciliar -o conciliacao.xlsx

# ou ?formato=json para integrar com outro sistema
```

Aceita `.csv` (separador detectado automaticamente) ou `.xlsx`. Se faltar alguma coluna, a API responde `422` dizendo qual.

## Estrutura

```
conciliacao/
├── regras.py      # alíquotas e regras de dispensa (configurável)
├── motor.py       # cálculo esperado, merge, classificação e resumo
├── relatorio.py   # Excel formatado com xlsxwriter
├── api.py         # FastAPI (POST /conciliar, GET /health)
└── __main__.py    # CLI
scripts/gerar_dados_sinteticos.py
```

## Testes

```bash
pytest
```

Cobrem as regras (dispensa abaixo de R$ 10, Simples Nacional), a normalização de chaves, cada status da conciliação e a API de ponta a ponta.

## Tecnologias

Python 3.10+ · pandas · FastAPI · xlsxwriter · pytest

---
Desenvolvido por **Yasmim Santos** · Licença MIT
