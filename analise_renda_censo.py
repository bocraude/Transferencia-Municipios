"""Passo C: renda municipal por fonte no Censo 2022 (SIDRA 10297, amostra) x registros administrativos.
- Os microdados da amostra de 2022 têm só dois blocos de renda: trabalho (P1080) e um único bloco
  "Aposentadoria/Pensão/Bolsa Família/BPC/Aluguel" (P1100); o município (P0080) só existe no acesso restrito.
- A SIDRA 10297 publica, por município, a massa de rendimento domiciliar de todas as fontes, dos trabalhos e
  de outras fontes. Com ela: (i) renda sem transferências na mesma fonte; (ii) declarado x administrativo.
Uso: python3 -I analise_renda_censo.py  (depois de analise_semiarido.py)."""
import json
import numpy as np, pandas as pd

log = open('out/resultados_C.txt', 'w')
def say(*a): print(*a, file=log)

s = pd.DataFrame(json.load(open('data/ibge/sidra10297/t10297.json')))
s = s[s.D2C == '13506']   # massa de rendimento (R$/mês)
s = s.pivot_table(index=s.D1C.astype(int), columns='D4C', values='V', aggfunc=lambda x: pd.to_numeric(x).sum())
s.columns = s.columns.map({'79450': 'c_todas', '79451': 'c_trab', '79452': 'c_outras'})
say('SIDRA 10297: municipios', len(s), '| todas = trabalho + outras? max |dif| =', (s.c_todas - s.c_trab - s.c_outras).abs().max())

d = pd.read_csv('out/base_municipal_situacao_2022.csv', index_col=0)
d.index = d.index.astype(int)
tf = pd.read_excel('data/transf.xlsx'); tf = tf[tf.nivel == 'Municípios'].set_index(tf[tf.nivel == 'Municípios'].COD_MUN.astype(int))
d = d.join(s).join(tf[['bpc', 'bolsa', 'seguro', 'apos_Rural', 'apos_Urbano', 'pib', 'massa_salarial']])
d = d[d.c_todas > 0]
pop = d.populacao

# ---------- 1. de onde vem renda_pc da planilha ----------
r = d.renda_total / d.c_todas
say('\n== renda_total da planilha / massa de todas as fontes (Censo 2022, SIDRA 10297) ==')
say('quantis:', r.quantile([.01, .05, .25, .5, .75, .95, .99]).round(4).to_dict())
say('=> renda_pc da planilha e o rendimento domiciliar per capita do Censo 2022 (mesmo conceito, ~mesma massa).')

# ---------- 2. declarado x administrativo ----------
d['razao_outras_T'] = d.c_outras / d['T']            # outras fontes declaradas / 5 benefícios administrativos
d['T_menos_seguro'] = d['T'] - d.seguro
say('\n== Declarado (Censo: outras fontes) x administrativo (5 beneficios) ==')
say('Brasil: outras fontes (Censo) R$ bi/mes', round(d.c_outras.sum() / 1e9, 2), '| beneficios administrativos', round(d['T'].sum() / 1e9, 2),
    '| razao', round(d.c_outras.sum() / d['T'].sum(), 3))
say('razao municipal outras/T: quantis', d.razao_outras_T.quantile([.05, .25, .5, .75, .95]).round(3).to_dict())
say('municipios com outras fontes declaradas < beneficios administrativos:', int((d.c_outras < d['T']).sum()), 'de', len(d),
    f'({(d.c_outras < d["T"]).mean():.1%})')
say('  idem excluindo seguro-desemprego:', int((d.c_outras < d.T_menos_seguro).sum()))
say('(outras fontes inclui tambem RPPS, previdencia privada, aluguel, pensao alimenticia etc.: deveria ser >= T)')
q = pd.qcut(d.s, 5, labels=['Q1 menor dep.', 'Q2', 'Q3', 'Q4', 'Q5 maior dep.'])
t = d.groupby(q, observed=True).apply(lambda g: pd.Series({
    'n': len(g), 'dep_admin_mediana': g.s.median(), 'dep_censo_mediana': (g.c_outras / g.c_todas).median(),
    'razao_outras_T_agregada': g.c_outras.sum() / g['T'].sum(), 'pct_outras_menor_T': (g.c_outras < g['T']).mean() * 100,
    'sh_rural_em_T': g.apos_Rural.sum() / g['T'].sum()}))
say('\nPor quintil da dependencia original (T/renda_total):\n', t.round(3).to_string())
reg = d.groupby('reg').apply(lambda g: pd.Series({'razao_outras_T': g.c_outras.sum() / g['T'].sum(),
                                                  'pct_outras_menor_T': (g.c_outras < g['T']).mean() * 100}))
reg.index = ['Norte', 'Nordeste', 'Sudeste', 'Sul', 'Centro-Oeste']
say('\nPor regiao:\n', reg.round(3).to_string())
# regressão simples: o sub-registro (log razão) cresce com o peso da aposentadoria rural?
x = d[(d.razao_outras_T > 0)]
X = np.column_stack([np.ones(len(x)), x.apos_Rural / x['T'], (x.bolsa + x.bpc) / x['T'], np.log(x.renda_pc)])
b, *_ = np.linalg.lstsq(X, np.log(x.razao_outras_T), rcond=None)
say('\nlog(outras/T) ~ parcela ap. rural em T + parcela BF+BPC em T + log renda_pc:', dict(zip(['const', 'sh_ap_rural', 'sh_bf_bpc', 'log_renda_pc'], b.round(3))))

# ---------- 3. medidas alternativas de dependência ----------
d['s_censo'] = d.c_outras / d.c_todas                                  # tudo no Censo (inclui RPPS, aluguel)
d['s_hibrido'] = d['T'] / (d.c_trab + d['T'])                           # trabalho (Censo) + benefícios (registros)
d['s_hibrido2'] = d['T'] / (d.c_trab + np.maximum(d.c_outras, d['T']))  # denominador inclui as outras fontes se maiores que T
d['s_massa_sal'] = d['T'] / (d.massa_salarial + d['T'])
d['s_pib'] = d['T'] * 12 / d.pib
say('\n== Dependencia sob denominadores alternativos ==')
cols = ['s', 's_censo', 's_hibrido', 's_hibrido2', 's_massa_sal', 's_pib']
num = {'s': d['T'], 's_censo': d.c_outras, 's_hibrido': d['T'], 's_hibrido2': d['T'], 's_massa_sal': d['T'], 's_pib': d['T'] * 12}
den = {'s': d.renda_total, 's_censo': d.c_todas, 's_hibrido': d.c_trab + d['T'], 's_hibrido2': d.c_trab + np.maximum(d.c_outras, d['T']),
       's_massa_sal': d.massa_salarial + d['T'], 's_pib': d.pib}
desc = pd.DataFrame({c: {'razao_agregada': num[c].sum() / den[c].sum(), 'ponderada_pop': np.average(d[c], weights=pop), 'mediana': d[c].median(), 'p95': d[c].quantile(.95),
                         'max': d[c].max(), 'pct_munic>25%': (d[c] > .25).mean() * 100, 'pct_munic>50%': (d[c] > .5).mean() * 100}
                     for c in cols}).T
desc.index = ['T/renda_total (original)', 'outras/todas (so Censo)', 'T/(trabalho Censo + T)', 'T/(trabalho + max(outras,T))',
              'T/(massa salarial RAIS + T)', 'T*12/PIB']
say(desc.round(3).to_string())
say('correlacoes de Spearman:\n', d[cols].corr('spearman').round(3).to_string())

# ---------- 4. desigualdade entre municípios ----------
def gini(y, w):
    o = np.argsort(y); y, w = np.asarray(y)[o], np.asarray(w)[o]
    cw = np.cumsum(w) / w.sum(); cy = np.cumsum(y * w) / (y * w).sum()
    return 1 - np.sum((cw - np.r_[0, cw[:-1]]) * (cy + np.r_[0, cy[:-1]]))
def atk(y, w, e):
    y, w = np.asarray(y, float), np.asarray(w, float) / np.sum(w); m = np.sum(w * y)
    if e == 1: return 1 - np.exp(np.sum(w * np.log(y))) / m
    return 1 - np.sum(w * y ** (1 - e)) ** (1 / (1 - e)) / m
def theil(y, w):
    w = np.asarray(w, float) / np.sum(w); m = np.sum(w * y); return np.sum(w * (y / m) * np.log(y / m))
med = {
    'PIB pc': d.pib / 12 / pop,
    'massa salarial RAIS pc': d.massa_salarial / pop,
    'renda - T admin (original)': (d.renda_total - d['T']) / pop,
    'renda total (original)': d.renda_total / pop,
    'Censo: trabalho pc': d.c_trab / pop,
    'Censo: trabalho + T admin': (d.c_trab + d['T']) / pop,
    'Censo: todas as fontes': d.c_todas / pop,
}
rows = []
for k, y in med.items():
    ok = (y > 0).values
    rows.append({'medida': k, 'n': ok.sum(), 'media_pc': np.average(y[ok], weights=pop[ok]), 'gini': gini(y[ok], pop[ok]),
                 'atk_0.5': atk(y[ok], pop[ok], .5), 'atk_1': atk(y[ok], pop[ok], 1), 'atk_2': atk(y[ok], pop[ok], 2), 'theil': theil(y[ok], pop[ok])})
say('\n== Desigualdade entre municipios (ponderada pela populacao, R$/mes per capita) ==')
say(pd.DataFrame(rows).set_index('medida').round(3).to_string())
say('(conferencia com o LEIAME: Gini 0,293 -> 0,242; Atkinson e=2 0,322 -> 0,187; PIB pc 0,376; massa salarial 0,435)')
g0, g1 = gini(med['Censo: trabalho pc'], pop), gini(med['Censo: trabalho + T admin'], pop)
say(f'\nReducao do Gini pelas transferencias: original {rows[2]["gini"] - rows[3]["gini"]:.3f} '
    f'({(rows[2]["gini"] - rows[3]["gini"]) / rows[2]["gini"]:.1%}) | trabalho Censo -> + T admin {g0 - g1:.3f} ({(g0 - g1) / g0:.1%})')

d.to_csv('out/base_municipal_renda_censo.csv')
log.close()
print(open('out/resultados_C.txt').read())
