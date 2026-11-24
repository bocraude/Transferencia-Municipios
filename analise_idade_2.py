"""Extensão: sexo e situação urbana/rural (Censo 2010) e idades de elegibilidade (Censo 2022).
Uso: python3 -I analise_idade_2.py  (depois de analise_idade.py)."""
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor

def load1378(f):
    c = pd.read_excel(f, header=None).iloc[6:-1, [0, 2, 4]]
    c.columns = ['cod', 'idade', 'pop']
    c['cod'] = pd.to_numeric(c['cod'], errors='coerce').ffill()
    c['pop'] = pd.to_numeric(c['pop'], errors='coerce').fillna(0)
    p = c.pivot_table(index='cod', columns='idade', values='pop', aggfunc='sum')
    g = pd.DataFrame(index=p.index)
    g['15_19'] = p['15 a 17 anos'] + p['18 ou 19 anos']
    for a in [10, 20, 25, 30, 35, 40, 45, 50, 55]:
        g[f'{a}_{a+4}'] = p[f'{a} a {a+4} anos']
    g['60_64'] = p['60 a 64 anos'] if '60 a 64 anos' in p else p['60 a 69 anos'] - p['65 a 69 anos']
    g['65_69'] = p['65 a 69 anos'] if '65 a 69 anos' in p else p['60 a 69 anos'] - p['60 a 64 anos']
    g['75m'] = p['75 a 79 anos'] + p['80 a 89 anos'] + p['90 a 99 anos'] + p['100 anos ou mais']
    g['70_74'] = p['70 a 74 anos'] if '70 a 74 anos' in p else p['70 anos ou mais'] - g['75m']
    if 'Total' in p:
        g['Total'] = p['Total']
        g['0_9'] = g['Total'] - g.drop(columns='Total').sum(axis=1)
    else:
        g['0_9'] = p['0 a 4 anos'] + p['5 a 9 anos']
        g['Total'] = g.sum(axis=1)
    return g

T = load1378('data/censo/c.xlsx')          # total
U = load1378('data/censo/u_t.xlsx')        # urbano total
W = load1378('data/censo/t_m.xlsx')        # mulheres total
RW = load1378('data/censo/r_m.xlsx')       # rural mulheres
UW = load1378('data/censo/u_m.xlsx')       # urbano mulheres
idx = T.index
U, W, RW, UW = [x.reindex(idx).fillna(0) for x in (U, W, RW, UW)]
R = T - U; M = T - W; RM = R - RW
chk = (RW + UW - W).abs().to_numpy().max()

old_w = ['55_59', '60_64', '65_69', '70_74', '75m']        # mulheres 55+
old_m = ['60_64', '65_69', '70_74', '75m']                 # homens 60+
z = pd.DataFrame(index=idx)
z['rural_sh_10'] = R.Total / T.Total
z['eleg_rural_10'] = (RW[old_w].sum(axis=1) + RM[old_m].sum(axis=1)) / T.Total   # residentes rurais em idade de aposentadoria rural
z['rural_sh_45m_10'] = (R[['45_49', '50_54'] + old_w].sum(axis=1)) / T[['45_49', '50_54'] + old_w].sum(axis=1)
# migração jovem por sexo (20-29 em 2010)
z['jov_w_10'] = W['20_24'] + W['25_29']; z['jov_m_10'] = M['20_24'] + M['25_29']

# ---------- 2022 por sexo ----------
def load9514(f):
    d = pd.read_excel(f, header=None)
    cols = ['cod', 'mun', 'forma'] + list(d.iloc[5, 3:])
    d = d.iloc[7:-1].copy(); d.columns = cols
    d['cod'] = pd.to_numeric(d['cod'], errors='coerce'); d = d.dropna(subset=['cod']).set_index('cod')
    num = cols[3:]; d[num] = d[num].apply(pd.to_numeric, errors='coerce').fillna(0)
    d['55 a 59 anos'] = d['Total'] - d[num[1:]].sum(axis=1)
    return d
P = load9514('data/censo/b.xlsx'); H = load9514('data/censo/a.xlsx'); F = P.drop(columns=['mun', 'forma']) - H.drop(columns=['mun', 'forma'])
o70 = ['70 a 74 anos', '75 a 79 anos', '80 a 84 anos', '85 a 89 anos', '90 a 94 anos', '95 a 99 anos', '100 anos ou mais']
z22 = pd.DataFrame(index=P.index)
z22['eleg_rural_22'] = (F[['55 a 59 anos', '60 a 64 anos', '65 a 69 anos'] + o70].sum(axis=1)
                        + H[['60 a 64 anos', '65 a 69 anos'] + o70].sum(axis=1)) / P.Total
z22['eleg_urb_22'] = (F[['60 a 64 anos', '65 a 69 anos'] + o70].sum(axis=1)
                      + H[['65 a 69 anos'] + o70].sum(axis=1)) / P.Total
jw22 = 0.6 * F['30 a 34 anos'] + F['35 a 39 anos'] + 0.4 * F['40 a 44 anos']
jm22 = 0.6 * H['30 a 34 anos'] + H['35 a 39 anos'] + 0.4 * H['40 a 44 anos']
z22['jw22'] = jw22; z22['jm22'] = jm22

d = pd.read_csv('out/base_municipal_idade.csv', index_col=0)
d = d.join(z).join(z22)
ambos = d.jov_w_10.notna()   # só municípios presentes nos dois Censos
br_w = d.jw22[ambos].sum() / d.jov_w_10[ambos].sum(); br_m = d.jm22[ambos].sum() / d.jov_m_10[ambos].sum()
d['mig_jovem_mulher'] = np.log((d.jw22 / d.jov_w_10) / br_w)
d['mig_jovem_homem'] = np.log((d.jm22 / d.jov_m_10) / br_m)
d['gap_sexo'] = d.mig_jovem_mulher - d.mig_jovem_homem   # <0: mulheres jovens saem mais

# cobertura implícita da aposentadoria rural (benefícios / residentes rurais em idade de elegibilidade)
SM = 1212.0
d['benef_rurais'] = d.s_rural * d.renda_total / SM
d['eleg_rural_res_22'] = d.eleg_rural_22 * d.populacao * d.rural_sh_45m_10
d['cobertura_rural'] = d.benef_rurais / d.eleg_rural_res_22

def ols(y, X, names):
    X = np.column_stack([np.ones(len(y))] + X); y = np.asarray(y, float)
    b, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ b
    n, k = X.shape; XtXi = np.linalg.inv(X.T @ X)
    V = XtXi @ (X.T * e ** 2) @ X @ XtXi * n / (n - k)
    return pd.DataFrame({'coef': b, 'ep': np.sqrt(np.diag(V))}, index=['const'] + names), 1 - e.var() / y.var()

ok = d.dropna(subset=['rural_sh_10', 'eleg_rural_22', 'mig_jovem', 'mig_jovem_mulher', 'mig_jovem_homem'])
ok = ok[np.isfinite(ok.mig_jovem_mulher) & np.isfinite(ok.mig_jovem_homem)]
# tipologia com limiares (envelhecidos): atrito = saída líquida de jovens > 10%;
# atração = ganho líquido de idosos > 5% (sem atrito); demais = intermediário
ok['tipo2'] = 'não envelhecido'
ev = ok.envelhecido == 1
ok.loc[ev, 'tipo2'] = 'intermediário'
ok.loc[ev & (ok.mig_idoso > 0.05), 'tipo2'] = 'atração'
ok.loc[ev & (ok.mig_jovem < -0.10), 'tipo2'] = 'atrito'
age = ['sh_0_14', 'sh_55_59', 'sh_60_64', 'sh_65_69', 'sh_70m']
res = {}
def rf_r2(cols, y='s'):
    rf = RandomForestRegressor(n_estimators=500, min_samples_leaf=10, oob_score=True, random_state=1, n_jobs=-1)
    rf.fit(ok[cols], ok[y]); return rf.oob_score_, rf.oob_prediction_
res['idade (grupos)'] = rf_r2(age)[0]
res['idade + elegibilidade por sexo'] = rf_r2(age + ['eleg_rural_22', 'eleg_urb_22'])[0]
r2, pred = rf_r2(age + ['eleg_rural_22', 'eleg_urb_22', 'rural_sh_10', 'eleg_rural_10'])
res['+ ruralidade 2010'] = r2
ok = ok.assign(s_prev_dem=pred, resid_dem=ok.s - pred)
res_rural = {'aposentadoria rural ~ idade': rf_r2(age, 's_rural')[0],
             'aposentadoria rural ~ idade + elegibilidade + ruralidade': rf_r2(age + ['eleg_rural_22', 'eleg_urb_22', 'rural_sh_10', 'eleg_rural_10'], 's_rural')[0]}

env = ok[ok.envelhecido == 1]
r_a, r2_a = ols(env.resid_idade, [env.mig_jovem.values, env.mig_idoso.values, env.nordeste.values], ['mig_jovem', 'mig_idoso', 'nordeste'])
r_b, r2_b = ols(env.resid_dem, [env.mig_jovem.values, env.mig_idoso.values, env.nordeste.values], ['mig_jovem', 'mig_idoso', 'nordeste'])
r_c, r2_c = ols(env.resid_dem, [env.mig_jovem_mulher.values, env.mig_jovem_homem.values, env.mig_idoso.values, env.nordeste.values],
                ['mig_jovem_mulher', 'mig_jovem_homem', 'mig_idoso', 'nordeste'])

tipo = ok.groupby('tipo2').agg(n=('s', 'size'), rural_sh_10=('rural_sh_10', 'median'), eleg_rural_22=('eleg_rural_22', 'median'),
                              resid_idade=('resid_idade', 'median'), resid_dem=('resid_dem', 'median'),
                              mig_mulher=('mig_jovem_mulher', 'median'), mig_homem=('mig_jovem_homem', 'median'),
                              cobertura_rural=('cobertura_rural', 'median'))
cob = ok.cobertura_rural.replace([np.inf, -np.inf], np.nan)
q = pd.qcut(ok.rural_sh_10, 5, labels=['Q1 mais urbano', 'Q2', 'Q3', 'Q4', 'Q5 mais rural'])
quint = ok.groupby(q, observed=True).agg(rural_sh=('rural_sh_10', 'median'), dep=('s', 'median'), dep_rural=('s_rural', 'median'),
                                          cobertura=('cobertura_rural', 'median'), mig_mulher=('mig_jovem_mulher', 'median'),
                                          mig_homem=('mig_jovem_homem', 'median'), resid_idade=('resid_idade', 'median'))
with open('out/resultados_2.txt', 'w') as f:
    print('checagem rural+urbano mulheres = total mulheres (max dif):', chk, file=f)
    print('N', len(ok), file=f)
    print('\nR2 fora da amostra (RF), dependencia total:', {k: round(v, 3) for k, v in res.items()}, file=f)
    print('R2 RF, aposentadoria rural:', {k: round(v, 3) for k, v in res_rural.items()}, file=f)
    print('\nResiduo (so idade) ~ migracao:\n', r_a.round(3), round(r2_a, 3), file=f)
    print('\nResiduo (idade+elegib+ruralidade) ~ migracao:\n', r_b.round(3), round(r2_b, 3), file=f)
    print('\nResiduo demografico ~ migracao por sexo:\n', r_c.round(3), round(r2_c, 3), file=f)
    print('\nTipologia:\n', tipo.round(3).to_string(), file=f)
    print('\nQuintis de ruralidade 2010:\n', quint.round(3).to_string(), file=f)
    print('\nCobertura rural implicita: mediana', round(cob.median(), 2), 'p25-p75', cob.quantile([.25, .75]).round(2).values, file=f)
ok.to_csv('out/base_municipal_idade_v2.csv')
print(open('out/resultados_2.txt').read())
