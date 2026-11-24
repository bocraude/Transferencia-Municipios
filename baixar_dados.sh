#!/usr/bin/env bash
# Baixa os dados brutos do IBGE usados pelos scripts (não versionados: ver .gitignore).
set -euo pipefail
cd "$(dirname "$0")"
FTP=https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios
mkdir -p data/ibge/setores data/ibge/sidra10089
( cd data/ibge/setores
  for f in Agregados_por_Setor_csv/Agregados_por_setores_demografia_BR.zip \
           Agregados_por_Setor_csv/Agregados_por_setores_basico_BR_20260520.zip \
           dicionario_de_dados_agregados_por_setores_censitarios_20261113.xlsx; do
    [ -s "$(basename $f)" ] || curl -sS --retry 4 -O "$FTP/$f"
  done
  unzip -o -q '*.zip' )
# SIDRA 10089: população por sexo, grupo de idade e situação, por município (uma consulta por UF)
for uf in 11 12 13 14 15 16 17 21 22 23 24 25 26 27 28 29 31 32 33 35 41 42 43 50 51 52 53; do
  f=data/ibge/sidra10089/uf$uf.json
  [ -s $f ] || curl -sS --retry 4 --max-time 300 -o $f \
    "https://apisidra.ibge.gov.br/values/t/10089/n6/in%20n3%20$uf/v/93/p/all/c2/4,5/c58/allxt/c1/1,2/c2661/32776/f/c/h/n"
done
# SIDRA 10297: massa de rendimento domiciliar por tipo (todas as fontes, trabalhos, outras fontes), municípios
mkdir -p data/ibge/sidra10297
[ -s data/ibge/sidra10297/t10297.json ] || curl -sS --retry 4 --max-time 300 -o data/ibge/sidra10297/t10297.json \
  "https://apisidra.ibge.gov.br/values/t/10297/n6/all/v/13506,13504/p/all/c11308/allxt/f/c/h/n"
