"""Passo A: Censo 2022 por município x situação (urbana/rural) x sexo x idade.
Fonte principal: SIDRA 10089 (nível municipal, grupos quinquenais). Validação: SIDRA 9514 e agregados por setor.
Uso: python3 -I analise_situacao_2022.py  (depois de analise_idade.py e analise_idade_2.py)."""
import glob, json
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor

OUT = 'out/resultados_A.txt'
log = open(OUT, 'w')
def say(*a): print(*a, file=log)

# ---------- 1. SIDRA 10089 ----------
IDADE = {1140: '0 a 4 anos', 1141: '5 a 9 anos', 1142: '10 a 14 anos', 1143: '15 a 19 anos', 1144: '20 a 24 anos',
         1145: '25 a 29 anos', 1146: '30 a 34 anos', 1147: '35 a 39 anos', 1148: '40 a 44 anos', 1149: '45 a 49 anos',
         1150: '50 a 54 anos', 1151: '55 a 59 anos', 1152: '60 a 64 anos', 1153: '65 a 69 anos', 1154: '70 a 74 anos',
         1155: '75 a 79 anos', 6802: '80 a 84 anos', 6803: '85 a 89 anos', 92963: '90 a 94 anos', 92964: '95 a 99 anos',
         92965: '100 anos ou mais'}
rows = []
for f in sorted(glob.glob('data/ibge/sidra10089/uf*.json')):
    rows += json.load(open(f))
s = pd.DataFrame(rows)
s = pd.DataFrame({'cod': s.D1C.astype(int), 'sexo': s.D4C.map({'4': 'H', '5': 'M'}),
                  'idade': s.D5C.astype(int).map(IDADE), 'sit': s.D6C.map({'1': 'U', '2': 'R'}),
                  'pop': pd.to_numeric(s.V, errors='coerce').fillna(0)})   # '-' = zero no SIDRA
assert s.notna().all().all()
G = s.pivot_table(index='cod', columns=['sit', 'sexo', 'idade'], values='pop', aggfunc='sum').fillna(0)
say('SIDRA 10089: municipios', G.shape[0], '| populacao', int(G.to_numpy().sum()))

# ---------- 2. validação contra SIDRA 9514 ----------
def load9514(f):
    d = pd.read_excel(f, header=None)
    cols = ['cod', 'mun', 'forma'] + list(d.iloc[5, 3:])
    d = d.iloc[7:-1].copy(); d.columns = cols
    d['cod'] = pd.to_numeric(d['cod'], errors='coerce'); d = d.dropna(subset=['cod'])
    d['cod'] = d.cod.astype(int); d = d.set_index('cod')
    num = cols[3:]; d[num] = d[num].apply(pd.to_numeric, errors='coerce').fillna(0)
    d['55 a 59 anos'] = d['Total'] - d[num[1:]].sum(axis=1)
    return d
P = load9514('data/censo/b.xlsx'); Hm = load9514('data/censo/a.xlsx')
ages = list(IDADE.values())
tot = G.T.groupby(level='idade').sum().T[ages]
hom = G.xs('H', axis=1, level='sexo').T.groupby(level='idade').sum().T[ages]
idx = tot.index.intersection(P.index)
dif_t = (tot.loc[idx] - P.loc[idx, ages]).abs(); dif_h = (hom.loc[idx] - Hm.loc[idx, ages]).abs()
say('\n== Validacao contra SIDRA 9514 ==')
say('municipios em comum:', len(idx), '| so em 10089:', len(tot.index.difference(P.index)), '| so em 9514:', len(P.index.difference(tot.index)))
say('total por municipio: max |dif| =', dif_t.sum(axis=1).max(), '| total geral 10089 =', int(tot.to_numpy().sum()), '| 9514 =', int(P.Total.sum()))
say('total x idade: celulas com dif =', int((dif_t > 0).sum().sum()), 'de', dif_t.size, '| max', dif_t.to_numpy().max())
say('homens x idade: celulas com dif =', int((dif_h > 0).sum().sum()), 'de', dif_h.size, '| max', dif_h.to_numpy().max())
say('55-59 recuperado por residuo (9514) x 10089: max |dif| =', dif_t['55 a 59 anos'].max())

# ---------- 3. validação da situação contra os agregados por setor ----------
b = pd.read_csv('data/ibge/setores/Agregados_por_setores_basico_BR.csv', sep=';', encoding='latin1',
                usecols=['CD_SETOR', 'SITUACAO', 'CD_MUN', 'v0001'], dtype=str)
b = b[b.CD_MUN != '.']   # 2 'setores' de lagoas do RS (Patos e Mirim), sem município e sem moradores
say('setores por situacao:', b.SITUACAO.value_counts(dropna=False).to_dict())
b['sit'] = b.SITUACAO.map({'Urbana': 'U', 'Rural': 'R'})
b['pop'] = pd.to_numeric(b.v0001, errors='coerce')
st = b.pivot_table(index=b.CD_MUN.astype(int), columns='sit', values='pop', aggfunc='sum').fillna(0)
sid = G.T.groupby(level='sit').sum().T
j = sid.join(st, rsuffix='_set', how='inner')
say('\n== Validacao da situacao contra setores (v0001, pessoas) ==')
say('municipios:', len(j), '| setores sem v0001:', int(b['pop'].isna().sum()))
for k in ['U', 'R']:
    dd = (j[k] - j[k + '_set']).abs()
    say(f'{k}: municipios com dif = {(dd > 0).sum()}, max |dif| = {dd.max():.0f}, total 10089 = {j[k].sum():.0f}, setores = {j[k + "_set"].sum():.0f}')
say('(o arquivo de demografia por setor tem celulas suprimidas "X" em ~29% dos setores; por isso nao e usado para idade)')

# ---------- 4. Censo 2010 por situação x sexo (mesmo tratamento de analise_idade_2.py) ----------
def load1378(f):
    c = pd.read_excel(f, header=None).iloc[6:-1, [0, 2, 4]]
    c.columns = ['cod', 'idade', 'pop']
    c['cod'] = pd.to_numeric(c['cod'], errors='coerce').ffill()
    c['pop'] = pd.to_numeric(c['pop'], errors='coerce').fillna(0)
    p = c.pivot_table(index='cod', columns='idade', values='pop', aggfunc='sum')
    g = pd.DataFrame(index=p.index.astype(int))
    for a in [20, 25, 50, 55]:
        g[f'{a}_{a+4}'] = p[f'{a} a {a+4} anos'].values
    return g
T10 = load1378('data/censo/c.xlsx'); U10 = load1378('data/censo/u_t.xlsx')
W10 = load1378('data/censo/t_m.xlsx'); RW10 = load1378('data/censo/r_m.xlsx')
U10, W10, RW10 = [x.reindex(T10.index).fillna(0) for x in (U10, W10, RW10)]
R10 = T10 - U10
M10 = T10 - W10; RM10 = R10 - RW10; UW10 = W10 - RW10; UM10 = M10 - RM10
c10 = {('U', 'H'): UM10, ('U', 'M'): UW10, ('R', 'H'): RM10, ('R', 'M'): RW10}

# ---------- 5. migração por coorte por situação ----------
def coorte22(sit, sexo, ini):
    g = G[sit][sexo] if sexo else G[sit]['H'] + G[sit]['M']
    a = [f'{ini} a {ini+4} anos', f'{ini+5} a {ini+9} anos', f'{ini+10} a {ini+14} anos']
    return 0.6 * g[a[0]] + g[a[1]] + 0.4 * g[a[2]]
def coorte10(sit, sexo, ini):
    g = c10[(sit, sexo)] if sexo else c10[(sit, 'H')] + c10[(sit, 'M')]
    return g[f'{ini}_{ini+4}'] + g[f'{ini+5}_{ini+9}']
com = G.index.intersection(T10.index)
# fator nacional: todas as situações juntas (desconta mortalidade, não a reclassificação)
br = {ini: (coorte22('U', None, i22) + coorte22('R', None, i22)).loc[com].sum() /
           (coorte10('U', None, ini) + coorte10('R', None, ini)).loc[com].sum()
      for ini, i22 in [(20, 30), (50, 60)]}
z = pd.DataFrame(index=com)
for sit, nm in [('U', 'urb'), ('R', 'rur')]:
    for sexo, sx in [(None, ''), ('M', '_mulher'), ('H', '_homem')]:
        y22, y10 = coorte22(sit, sexo, 30).loc[com], coorte10(sit, sexo, 20).loc[com]
        z[f'mig_jovem_{nm}{sx}'] = np.log((y22 / y10) / br[20])
    o22, o10 = coorte22(sit, None, 60).loc[com], coorte10(sit, None, 50).loc[com]
    z[f'mig_idoso_{nm}'] = np.log((o22 / o10) / br[50])
    z[f'jov10_{nm}'] = coorte10(sit, None, 20).loc[com]; z[f'jov22_{nm}'] = coorte22(sit, None, 30).loc[com]
# saída líquida de jovens (pessoas) por situação: esperado (sobrevivência nacional) - observado
z['perda_jov_urb'] = z.jov10_urb * br[20] - z.jov22_urb
z['perda_jov_rur'] = z.jov10_rur * br[20] - z.jov22_rur
# a reclassificação urbano/rural atinge todas as coortes; a diferença jovem - idoso a desconta
z['mig_jovem_rur_liq'] = z.mig_jovem_rur - z.mig_idoso_rur
z['mig_jovem_urb_liq'] = z.mig_jovem_urb - z.mig_idoso_urb

# ---------- 6. ruralidade e elegibilidade 2022 ----------
o70 = ['70 a 74 anos', '75 a 79 anos', '80 a 84 anos', '85 a 89 anos', '90 a 94 anos', '95 a 99 anos', '100 anos ou mais']
w55 = ['55 a 59 anos', '60 a 64 anos', '65 a 69 anos'] + o70
m60 = ['60 a 64 anos', '65 a 69 anos'] + o70
pop22 = G.sum(axis=1)
e = pd.DataFrame(index=G.index)
e['rural_sh_22'] = G['R'].sum(axis=1) / pop22
e['eleg_rural_res_22_novo'] = G['R']['M'][w55].sum(axis=1) + G['R']['H'][m60].sum(axis=1)   # residentes rurais elegíveis
e['eleg_total_22'] = G['U']['M'][w55].sum(axis=1) + G['U']['H'][m60].sum(axis=1) + e.eleg_rural_res_22_novo
e['sh_eleg_rural_22'] = e.eleg_rural_res_22_novo / pop22
e['rural_sh_eleg_22'] = e.eleg_rural_res_22_novo / e.eleg_total_22

d = pd.read_csv('out/base_municipal_idade_v2.csv', index_col=0)
d.index = d.index.astype(int)
d = d.join(e).join(z)
d['cobertura_rural_22'] = d.benef_rurais / d.eleg_rural_res_22_novo      # benefícios / residentes rurais elegíveis
d['cobertura_ampla_22'] = d.benef_rurais / d.eleg_total_22               # benefícios / todos os residentes elegíveis
d['d_rural_sh'] = d.rural_sh_22 - d.rural_sh_10

say('\n== Ruralidade 2010 x 2022 (mudanca de delimitacao + migracao) ==')
say('populacao rural no Brasil: 2010', round((d.rural_sh_10 * d.pop10).sum() / d.pop10[d.rural_sh_10.notna()].sum(), 3),
    '| 2022', round(G['R'].to_numpy().sum() / G.to_numpy().sum(), 3))
say('rural_sh_22 - rural_sh_10 por municipio: quantis', d.d_rural_sh.quantile([.05, .25, .5, .75, .95]).round(3).to_dict())
say('correlacao rural_sh_10 x rural_sh_22:', round(d[['rural_sh_10', 'rural_sh_22']].corr().iloc[0, 1], 3))
say('municipios com rural_sh_22 > rural_sh_10 + 0,10:', int((d.d_rural_sh > .10).sum()), '| < -0,10:', int((d.d_rural_sh < -.10).sum()))

# ---------- 7. resultados ----------
cob = d.cobertura_rural_22.replace([np.inf, -np.inf], np.nan)
say('\n== (ii) Cobertura rural implicita com residentes rurais elegiveis de 2022 (mulheres 55+, homens 60+) ==')
say('beneficios rurais estimados (valor/SM) no Brasil:', int(d.benef_rurais.sum()), '| residentes rurais elegiveis:', int(d.eleg_rural_res_22_novo.sum()),
    '| razao agregada:', round(d.benef_rurais.sum() / d.eleg_rural_res_22_novo.sum(), 2))
say('mediana', round(cob.median(), 2), '| p25-p75', cob.quantile([.25, .75]).round(2).values, '| municipios sem residente rural elegivel:', int(np.isinf(d.cobertura_rural_22).sum()))
say('versao anterior (ruralidade 2010): mediana', round(d.cobertura_rural.replace([np.inf, -np.inf], np.nan).median(), 2))
say('cobertura ampla (beneficios rurais / todos os elegiveis, urb+rur): mediana', round(d.cobertura_ampla_22.median(), 2),
    '| p25-p75', d.cobertura_ampla_22.quantile([.25, .75]).round(2).values)
say('municipios com cobertura_rural_22 > 1:', int((cob > 1).sum()), 'de', int(cob.notna().sum()))
q = pd.qcut(d.rural_sh_22, 5, labels=['Q1 mais urbano', 'Q2', 'Q3', 'Q4', 'Q5 mais rural'])
quint = d.groupby(q, observed=True).agg(rural_sh_22=('rural_sh_22', 'median'), dep=('s', 'median'), dep_rural=('s_rural', 'median'),
                                        cobertura_rural_22=('cobertura_rural_22', 'median'), cobertura_ampla=('cobertura_ampla_22', 'median'),
                                        mig_jovem_rur=('mig_jovem_rur', 'median'), mig_jovem_urb=('mig_jovem_urb', 'median'))
say('\nQuintis de ruralidade 2022:\n', quint.round(3).to_string())

ok = d[np.isfinite(d[['mig_jovem_rur', 'mig_jovem_urb', 'mig_idoso_rur', 'mig_idoso_urb']]).all(axis=1)].copy()
say('\n== (i) Migracao por coorte por situacao (municipios com populacao rural e urbana nas coortes) ==  N =', len(ok))
cols = ['mig_jovem_urb', 'mig_jovem_rur', 'mig_idoso_urb', 'mig_idoso_rur', 'mig_jovem_rur_liq', 'mig_jovem_urb_liq',
        'mig_jovem_rur_mulher', 'mig_jovem_rur_homem', 'mig_jovem_urb_mulher', 'mig_jovem_urb_homem']
say(ok[cols].describe(percentiles=[.25, .5, .75]).round(3).T[['mean', '25%', '50%', '75%']].to_string())
say('\nPor regiao (medianas):')
reg = ok.groupby('reg')[cols[:6]].median(); reg.index = ['Norte', 'Nordeste', 'Sudeste', 'Sul', 'Centro-Oeste']
say(reg.round(3).to_string())

def ols(y, X, names):
    X = np.column_stack([np.ones(len(y))] + X); y = np.asarray(y, float)
    bb, *_ = np.linalg.lstsq(X, y, rcond=None); ee = y - X @ bb
    n, k = X.shape; XtXi = np.linalg.inv(X.T @ X)
    V = XtXi @ (X.T * ee ** 2) @ X @ XtXi * n / (n - k)
    return pd.DataFrame({'coef': bb, 'ep': np.sqrt(np.diag(V))}, index=['const'] + names), 1 - ee.var() / y.var()

env = ok[(ok.envelhecido == 1) & ok.resid_dem.notna()]
say('\n== (iii) Residuo demografico ~ migracao por situacao (envelhecidos, N =', len(env), ') ==')
for nm, xs in [('jovem urb + rur', ['mig_jovem_urb', 'mig_jovem_rur', 'mig_idoso', 'nordeste']),
               ('jovem urb + rur (liquido de reclassificacao)', ['mig_jovem_urb_liq', 'mig_jovem_rur_liq', 'mig_idoso', 'nordeste']),
               ('por sexo e situacao', ['mig_jovem_urb_mulher', 'mig_jovem_urb_homem', 'mig_jovem_rur_mulher', 'mig_jovem_rur_homem', 'mig_idoso', 'nordeste'])]:
    r, r2 = ols(env.resid_dem, [env[c].values for c in xs], xs)
    say(f'\n{nm}:\n', r.round(3).to_string(), f'\nR2 = {r2:.3f}')

# tipologia: dentro do atrito, de onde vem a saída de jovens
ok['tipo3'] = ok.tipo2
at = ok.tipo2 == 'atrito'
perda = ok.perda_jov_urb.clip(lower=0) + ok.perda_jov_rur.clip(lower=0)
ok['sh_perda_rural'] = (ok.perda_jov_rur.clip(lower=0) / perda).where(at)   # só faz sentido no atrito
ok.loc[at & (ok.sh_perda_rural >= .5), 'tipo3'] = 'atrito rural'
ok.loc[at & (ok.sh_perda_rural < .5), 'tipo3'] = 'atrito urbano'
tipo = ok.groupby('tipo3').agg(n=('s', 'size'), dep_mediana=('s', 'median'), dep_rural_mediana=('s_rural', 'median'),
                               resid_dem=('resid_dem', 'median'), rural_sh_22=('rural_sh_22', 'median'),
                               mig_jovem_urb=('mig_jovem_urb', 'median'), mig_jovem_rur=('mig_jovem_rur', 'median'),
                               mig_jovem_rur_liq=('mig_jovem_rur_liq', 'median'), sh_perda_rural=('sh_perda_rural', 'median'),
                               cobertura_rural_22=('cobertura_rural_22', 'median'), pct_nordeste=('nordeste', 'mean'))
say('\nTipologia com origem da saida de jovens (atrito dividido pela parcela rural da perda liquida de 20-29 anos):\n', tipo.round(3).to_string())

# poder explicativo: ruralidade 2010 x 2022
age = ['sh_0_14', 'sh_55_59', 'sh_60_64', 'sh_65_69', 'sh_70m']
rr = d.dropna(subset=age + ['rural_sh_10', 'rural_sh_22', 'eleg_rural_22', 'eleg_urb_22', 'eleg_rural_10', 's'])
def rf(cols, y='s'):
    m = RandomForestRegressor(n_estimators=500, min_samples_leaf=10, oob_score=True, random_state=1, n_jobs=-1)
    m.fit(rr[cols], rr[y]); return round(m.oob_score_, 3)
base = age + ['eleg_rural_22', 'eleg_urb_22']
say('\n== R2 fora da amostra (RF), N =', len(rr), '==')
say({'idade + elegib + ruralidade 2010': rf(base + ['rural_sh_10', 'eleg_rural_10']),
     'idade + elegib + ruralidade 2022': rf(base + ['rural_sh_22', 'sh_eleg_rural_22', 'rural_sh_eleg_22']),
     'ap. rural ~ ... ruralidade 2010': rf(base + ['rural_sh_10', 'eleg_rural_10'], 's_rural'),
     'ap. rural ~ ... ruralidade 2022': rf(base + ['rural_sh_22', 'sh_eleg_rural_22', 'rural_sh_eleg_22'], 's_rural')})

d = d.join(ok[['tipo3', 'sh_perda_rural']])
d.to_csv('out/base_municipal_situacao_2022.csv')
G.columns = ['_'.join(c) for c in G.columns]
G.to_csv('out/pop2022_municipio_situacao_sexo_idade.csv')
log.close()
print(open(OUT).read())
