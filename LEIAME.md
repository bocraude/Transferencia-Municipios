# Transferências de renda, desigualdade e estabilização regional no Brasil — pacote de trabalho

Este arquivo resume o projeto para continuar no Claude Code. Leia tudo antes de executar qualquer passo.

## 1. Objetivo do artigo

Analisar, no nível municipal, cinco transferências federais — BPC, Bolsa Família, seguro-desemprego, aposentadoria urbana e aposentadoria rural — e medir:

1. **Equalização:** quanto reduzem a desigualdade de renda entre municípios (Atkinson ε = 0,5/1/2, Gini, Theil; contrafactual contábil "sem transferências"; decomposição de Shapley por benefício).
2. **Estabilização:** quanto amortecem choques na renda municipal (decomposição à Asdrubali-Sørensen-Yosha por benefício; elasticidade ao emprego formal com instrumento de Bartik; choques de seca 2012–2017, recessão 2015–16, pandemia).
3. **Dependência:** peso das transferências na renda e seus determinantes (idade, ruralidade, envelhecimento por atrito × atração).

Os resultados são contábeis (contribuição direta), não causais. A revisão de literatura, o texto da seção 2 e a análise da seção 3 estão num doc no claude.ai (Projeto "Análise das transferencias em nível municipio no brasil").

## 2. Estrutura da pasta

```
LEIAME.md
analise_idade.py          # passo 1: idade, migração por coorte, atrito × atração
analise_idade_2.py        # passo 2: sexo e urbano/rural (2010), elegibilidade, cobertura rural
data/
  transf.xlsx             # transferências municipais 2022 (planilha do projeto)
  censo/
    b.xlsx                # SIDRA 9514 (Censo 2022) – total, grupos quinquenais, com código
    a.xlsx                # SIDRA 9514 (Censo 2022) – homens
    c.xlsx                # SIDRA 1378 (Censo 2010) – total
    u_t.xlsx              # SIDRA 1378 (2010) – urbano total
    t_m.xlsx              # SIDRA 1378 (2010) – mulheres total
    r_m.xlsx              # SIDRA 1378 (2010) – rural mulheres
    u_m.xlsx              # SIDRA 1378 (2010) – urbano mulheres
out/
  base_municipal_idade.csv     # saída do passo 1
  base_municipal_idade_v2.csv  # saída do passo 2
  resultados.txt, resultados_2.txt
```

Rodar: `python3 analise_idade.py` e depois `python3 analise_idade_2.py` (pandas, numpy, scikit-learn, openpyxl).

## 3. Dados e ajustes já feitos

**Planilha de transferências (`data/transf.xlsx`)**
- 2022, valores **mensais** de renda e transferências. Linhas `nivel == "Municípios"` (5.570); há também linhas de UF e região.
- `renda_total = renda_pc × populacao`; `part_X = X / renda_total`.
- Local do benefício: município do registro do ministério.
- 5 municípios sem dados de aposentadoria; 22 sem IFDM (`firjan`).
- `renda_pc` vem de fonte declarada, diferente dos registros administrativos dos benefícios. A dependência chega a 96% em alguns municípios. Testar denominadores alternativos (PIB, massa salarial).

**Censo 2022 (SIDRA 9514)**
- O grupo **55 a 59 anos não veio** no download; foi recuperado como `Total − soma dos demais grupos` (vale tanto para o total quanto para homens). Mulheres = total − homens.

**Censo 2010 (SIDRA 1378)**
- Os grupos de idade são irregulares: 65–69 = (60–69) − (60–64); 70–74 = (70 ou mais) − (75–79) − (80–89) − (90–99) − (100+); 0–9 = Total − demais grupos, nos arquivos que não trazem 0–4 e 5–9.
- Derivados: rural = total − urbano; homens = total − mulheres; rural homens = rural − rural mulheres. Checagem: rural mulheres + urbano mulheres = mulheres (diferença zero).
- 4 municípios criados depois de 2010 (Mojuí dos Campos, Pescaria Brava, Balneário Rincão, Pinto Bandeira) ficam fora da migração por coorte.

**Migração líquida por coorte (12 anos):** 20–29 em 2010 → 32–41 em 2022 (jovens) e 50–59 → 62–71 (idosos), com interpolação uniforme nos grupos de 5 anos (0,6 × 30–34 + 35–39 + 0,4 × 40–44). A razão municipal é dividida pela razão nacional (desconta a mortalidade média). Índice > 0 = ganho líquido.

## 4. Resultados já obtidos (preliminares)

- Transferências = 21,7% da renda municipal (ponderado pela população); em 69% dos municípios passam de 25%.
- Gini entre municípios: 0,293 sem transferências → 0,242 com elas; Atkinson (ε = 2): 0,322 → 0,187.
- Shapley (Gini, ponderado): aposentadoria rural 50%, Bolsa Família 28%, BPC 14%, aposentadoria urbana 8%, seguro-desemprego ~0%.
- "Escada" do Gini: PIB pc 0,376 → massa salarial formal 0,435 → renda sem transferências 0,293 → renda 0,242.
- A idade explica 42% (MQO) a 57% (random forest, fora da amostra) da dependência; com ruralidade de 2010, 62%.
- Municípios envelhecidos por **atrito** (918): dependência mediana de 41% contra 28% nos de **atração** (1.239), com estrutura etária parecida. Cada −0,1 na migração jovem → +1,7 a 1,9 p.p. de excesso de dependência; a saída de mulheres jovens pesa mais que a de homens.
- Cobertura rural implícita (benefícios rurais / residentes rurais em idade de elegibilidade): mediana de 1,5, maior nos municípios mais urbanos. Indica muitos aposentados rurais morando em sedes urbanas. A estimativa é aproximada (usa a ruralidade de 2010).

## 5. Próximos passos (para executar no Claude Code)

### Passo A — Censo 2022 por município × situação urbano/rural × sexo × idade
Baixar de `https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/`:
- `Agregados_por_Setor_csv/Agregados_por_setores_demografia_BR.zip` (população por sexo e idade por setor)
- `Agregados_por_Setor_csv/Agregados_por_setores_basico_BR_20260520.zip` (atributos do setor, incluindo situação e código do município)
- `dicionario_de_dados_agregados_por_setores_censitarios_20261113.xlsx`

Os nomes de arquivo podem ter mudado; se não existirem, listar a pasta. Usar o dicionário para identificar as variáveis (não adivinhar códigos). Juntar pelo código do setor e agregar por município × situação × sexo × grupo de idade. Validar: a soma por município deve bater com a SIDRA 9514. Atenção: a delimitação urbano/rural mudou entre 2010 e 2022.

Com isso: (i) migração por coorte separada para rural e urbano; (ii) cobertura rural com residentes rurais elegíveis em 2022 (mulheres 55+, homens 60+); (iii) refazer a tipologia atrito × atração por situação.

### Passo B — Semiárido
Obter a lista oficial de municípios do semiárido (Sudene, delimitação vigente) e substituir a variável Nordeste no teste de atrito.

### Passo C — Microdados da amostra do Censo 2022
Conferir `https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Microdados_e_Areas_de_Ponderacao/`. Ver na documentação se há renda por fonte (trabalho, aposentadoria, BPC/Bolsa Família etc.). Se houver: (i) construir a renda municipal sem transferências na mesma fonte (resolve o problema do denominador); (ii) comparar benefícios declarados × administrativos por município.

### Passo D — Painel para a estabilização
- Transferências por município e ano (os dados de outros anos já estão disponíveis).
- Renda imputada nos anos sem Censo (método SPREE): W = massa salarial formal (RAIS), T = transferências (registros), O = outras rendas. O é ancorada nos Censos 2010 e 2022, os totais anuais vêm da PNAD Contínua por estrato geográfico (UF × capital/RM/interior), e a distribuição dentro do estrato é ajustada pelo valor adicionado agropecuário e de serviços do PIB municipal. Depois, calibrar aos totais da PNAD.
- Validação: imputar 2010 usando só a âncora de 2022 e comparar com o Censo 2010 (nível, variação e desigualdade).
- Cuidados: a RAIS registra o local de trabalho (corrigir com a matriz casa-trabalho ou usar regiões imediatas); tratar 2020–2021 à parte.
- Estimar a estabilização com três medidas de renda própria: imputada, massa salarial RAIS e PIB municipal.

### Passo E — Robustez da equalização
Ponderado × não ponderado; regiões geográficas imediatas; deflator espacial (aluguel do Censo 2022); Theil entre e dentro de UFs; efeitos marginais de Lerman-Yitzhaki; bootstrap dos índices.

## 6. Convenções
- Escrever em português; resultados em tabelas com unidades.
- Não sobrescrever arquivos originais; gravar saídas em `out/`.
- Registrar no fim deste arquivo o que foi feito e as decisões tomadas.

## 7. Registro de execução (Claude Code, 24/11/2026)

### Ordem de execução
```
./baixar_dados.sh                      # dados brutos do IBGE (não versionados; ~250 MB)
python3 analise_idade.py               # passo 1
python3 analise_idade_2.py             # passo 2
python3 analise_situacao_2022.py       # passo A  -> out/resultados_A.txt
python3 analise_semiarido.py           # passo B  -> out/resultados_B.txt
python3 analise_renda_censo.py         # passo C  -> out/resultados_C.txt
python3 analise_equalizacao_robustez.py  # passo E -> out/resultados_E.txt
```
Dependências: pandas, numpy, scikit-learn, openpyxl.

### Correções nos scripts originais
- `analise_idade_2.py` não rodava: usava `tipo2`, que nenhum script criava. A regra foi reconstruída a partir da saída original: entre os envelhecidos, **atrito** = `mig_jovem < −0,10`; **atração** = `mig_idoso > 0,05` (sem atrito); o resto é **intermediário**.
- O fator nacional da migração por sexo somava, em 2022, os 4 municípios criados após 2010. Agora usa só os presentes nos dois Censos. Com as duas correções, `resultados_2.txt` é reproduzido byte a byte.

### Passo A — decisões
- Fonte: **SIDRA 10089** (município × situação × sexo × idade quinquenal, inclusive 55–59), e não os agregados por setor. Motivos: os setores têm idade em faixas de 10 anos acima de 30 e células suprimidas ("X") em ~29% dos setores, concentradas nos pequenos (rurais).
- Validação: a 10089 bate **célula a célula** com a SIDRA 9514 (116.970 células; o 55–59 recuperado por resíduo também confere). Os totais urbano/rural por município batem exatamente com `v0001` dos setores.
- Mudança de delimitação: população rural de 15,6% (2010) para 12,6% (2022); 943 municípios perderam mais de 10 p.p. de ruralidade. A reclassificação atinge todas as coortes, por isso também se reporta `mig_jovem_rur_liq = mig_jovem_rur − mig_idoso_rur`.
- Resultados: (i) a migração jovem rural é negativa em quase todo o país (mediana −0,17), e a urbana é positiva (+0,04). (ii) **Cobertura rural com residentes rurais elegíveis de 2022: 1,74 benefício por residente rural elegível no agregado (mediana municipal 1,71; antes 1,5)**. Isso reforça que muitos aposentados rurais moram em áreas urbanas. (iii) O atrito se divide em **atrito rural** (549; dependência mediana 47,7%) e **atrito urbano** (361; 31,8%), contra 27,8% na atração. Na regressão do resíduo demográfico, a saída de jovens **urbanos**, sobretudo mulheres, pesa mais que a rural.
- A ruralidade de 2022 quase não melhora o R² do RF (0,619 → 0,621).

### Passo B — semiárido
- Lista: IBGE `lista_municipios_Semiarido_2022.xlsx` (geoftp) = 1.477 municípios. Conferido: = anexo da Res. Condel/Sudene 150/2021 (1.427) + os 50 da lista de 2017 excluídos em 2021 e mantidos por resoluções posteriores (155/2022, 163/2022, 176/2024). Na base: 1.474 (3 sem dados de aposentadoria).
- Resultado: o coeficiente da migração jovem é robusto (−0,19 → −0,20 com semiárido). O semiárido explica **menos** que o Nordeste (R² 0,154 contra 0,175). O "Nordeste fora do semiárido" tem prêmio de resíduo **maior** (+0,07) que o semiárido (+0,045), e a interação migração × semiárido é nula. O efeito regional não é climático.

### Passo C — microdados e renda por fonte
- Microdados da amostra 2022: só **trabalho (P1080)** e **um bloco único "Aposentadoria/Pensão/Bolsa Família/BPC/Aluguel" (P1100)**. Não dá para separar os benefícios. O município (P0080) e a área de ponderação existem só no **acesso restrito** (sala de sigilo do IBGE).
- Alternativa usada: **SIDRA 10297** (massa de rendimento domiciliar por município: todas as fontes / trabalhos / outras fontes).
- `renda_pc` da planilha **é** o rendimento domiciliar per capita do Censo 2022 (razão `renda_total`/massa 10297: mediana 1,002).
- Declarado × administrativo: outras fontes declaradas = 1,12 × benefícios administrativos no Brasil. Mas em **49% dos municípios** o Censo declara menos "outras fontes" (que incluem RPPS, previdência privada e aluguel) do que os 5 benefícios administrativos, chegando a **84% no quintil de maior dependência** (71,6% no Nordeste). Há sub-registro de benefícios no Censo onde eles mais pesam. Por isso `renda_total − T` fica subestimada e a dependência é inflada no topo (máximo de 95,9% → 78,5% com o denominador híbrido).
- Dependência agregada: 21,7% (original), 22,4% (T/(trabalho Censo + T)), 24,5% (só Censo).

### Passo E — robustez da equalização
- A redução do Gini pelas transferências é **17,4%** tanto na medida original quanto na híbrida (trabalho do Censo + T). No não ponderado chega a 27–28%; nas 510 regiões imediatas, 17,8–18,0%. No Atkinson ε=2, a redução fica entre 40% e 53%.
- Bootstrap (1.000): redução do Gini 0,051 [0,044; 0,058] (original); 0,048 [0,041; 0,054] (híbrida).
- Theil: cerca de 60% da queda ocorre **dentro** das UFs.
- Shapley reproduz o LEIAME (rural 50%, BF 28%, BPC 14%, urbana 8%, seguro 0%). Com a renda híbrida, a aposentadoria urbana cai para 1,6%. Nas RGIs, para ~0.
- Lerman-Yitzhaki (efeito de +1% na fonte sobre o Gini): aposentadoria rural −0,09%, BF −0,05%, BPC −0,02%, aposentadoria urbana ≈ 0 (levemente desequalizadora), seguro ≈ 0.
- **Pendente:** deflator espacial (o aluguel do Censo 2022 não está no SIDRA por município). Usar a tabela de aluguel quando for publicada, ou o acesso restrito.

### Passo D — não executado
Faltam dados que não estão no pacote: transferências por município de outros anos, RAIS (massa salarial anual), PNAD Contínua por estrato e a série do PIB municipal. Com esses arquivos em `data/`, o passo pode ser montado.
