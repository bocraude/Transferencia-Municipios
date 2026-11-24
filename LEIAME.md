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
