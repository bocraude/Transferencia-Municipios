"""Dependência de transferências e estrutura etária: Censos 2010 e 2022.
Uso: python3 -I analise_idade.py  (lê data/, grava out/)."""
import numpy as np, pandas as pd, os
from sklearn.ensemble import RandomForestRegressor

os.makedirs('out', exist_ok=True)

# ---------- 2022 (tabela 9514, total) ----------
def load9514(f):
    d = pd.read_excel(f, header=None)
    cols = ['cod', 'mun', 'forma'] + list(d.iloc[5, 3:])
    d = d.iloc[7:-1].copy(); d.columns = cols
    d['cod'] = pd.to_numeric(d['cod'], errors='coerce')
    num = cols[3:]
    d[num] = d[num].apply(pd.to_numeric, errors='coerce').fillna(0)
    # 55 a 59 anos não veio no download: recuperado como resíduo do total
    d['55 a 59 anos'] = d['Total'] - d[num[1:]].sum(axis=1)
    return d.dropna(subset=['cod'])

p22 = load9514('data/censo/b.xlsx')
h22 = load9514('data/censo/a.xlsx')
assert (p22['55 a 59 anos'] >= 0).all()

# ---------- 2010 (tabela 1378) ----------
c = pd.read_excel('data/censo/c.xlsx', header=None).iloc[6:-1, [0, 2, 4]]
c.columns = ['cod', 'idade', 'pop']
c['cod'] = pd.to_numeric(c['cod'], errors='coerce').ffill()
c['pop'] = pd.to_numeric(c['pop'], errors='coerce').fillna(0)
p10 = c.pivot_table(index='cod', columns='idade', values='pop', aggfunc='sum')
p10['15 a 19 anos'] = p10['15 a 17 anos'] + p10['18 ou 19 anos']
p10['65 a 69 anos'] = p10['60 a 69 anos'] - p10['60 a 64 anos']
p10['70 a 74 anos'] = (p10['70 anos ou mais'] - p10['75 a 79 anos'] - p10['80 a 89 anos']
                       - p10['90 a 99 anos'] - p10['100 anos ou mais'])
grp = ['0 a 4 anos', '5 a 9 anos', '10 a 14 anos', '15 a 19 anos', '20 a 24 anos', '25 a 29 anos',
       '30 a 34 anos', '35 a 39 anos', '40 a 44 anos', '45 a 49 anos', '50 a 54 anos', '55 a 59 anos',
       '60 a 64 anos', '65 a 69 anos', '70 a 74 anos']
p10['Total'] = p10[grp].sum(axis=1) + p10['75 a 79 anos'] + p10['80 a 89 anos'] + p10['90 a 99 anos'] + p10['100 anos ou mais']
p10 = p10.reset_index()

# ---------- transferências ----------
tf = pd.read_excel('data/transf.xlsx')
tf = tf[tf.nivel == 'Municípios'].copy()
tf['cod'] = tf.COD_MUN.astype(int)
tr = ['bpc', 'bolsa', 'seguro', 'apos_Rural', 'apos_Urbano']
tf = tf.dropna(subset=['apos_Rural'])
tf['T'] = tf[tr].sum(axis=1)
tf['s'] = tf['T'] / tf.renda_total
tf['s_rural'] = tf.apos_Rural / tf.renda_total

# ---------- base municipal ----------
P = p22.set_index('cod')
d = pd.DataFrame(index=P.index)
d['pop22'] = P.Total
d['sh_0_14'] = P[['0 a 4 anos', '5 a 9 anos', '10 a 14 anos']].sum(axis=1) / P.Total
d['sh_55_59'] = P['55 a 59 anos'] / P.Total
d['sh_60_64'] = P['60 a 64 anos'] / P.Total
d['sh_65_69'] = P['65 a 69 anos'] / P.Total
d['sh_70m'] = P[['70 a 74 anos', '75 a 79 anos', '80 a 84 anos', '85 a 89 anos', '90 a 94 anos',
                 '95 a 99 anos', '100 anos ou mais']].sum(axis=1) / P.Total
d['sh_60m'] = d.sh_60_64 + d.sh_65_69 + d.sh_70m
d['sh_65m'] = d.sh_65_69 + d.sh_70m
H = h22.set_index('cod')
d['razao_sexo_60m'] = (H[['60 a 64 anos', '65 a 69 anos']].sum(axis=1)) / (P[['60 a 64 anos', '65 a 69 anos']].sum(axis=1) - H[['60 a 64 anos', '65 a 69 anos']].sum(axis=1))

Q = p10.set_index('cod')
d = d.join(Q[['Total']].rename(columns={'Total': 'pop10'}))
d['cresc_pop'] = np.log(d.pop22 / d.pop10)

# migração líquida por coorte (12 anos), interpolação uniforme dentro dos grupos de 5 anos
young22 = 0.6 * P['30 a 34 anos'] + P['35 a 39 anos'] + 0.4 * P['40 a 44 anos']   # 32-41 em 2022
young10 = Q['20 a 24 anos'] + Q['25 a 29 anos']                                      # 20-29 em 2010
old22 = 0.6 * P['60 a 64 anos'] + P['65 a 69 anos'] + 0.4 * P['70 a 74 anos']       # 62-71 em 2022
old10 = Q['50 a 54 anos'] + Q['55 a 59 anos']                                        # 50-59 em 2010
br_y = young22.sum() / young10.reindex(young22.index).sum()
br_o = old22.sum() / old10.reindex(old22.index).sum()
d['mig_jovem'] = np.log((young22 / young10) / br_y)   # >0: ganho líquido relativo ao Brasil
d['mig_idoso'] = np.log((old22 / old10) / br_o)

d = d.join(tf.set_index('cod')[['SIGLA_UF', 'NM_MUN', 'renda_pc', 'populacao', 'T', 'renda_total', 's', 's_rural',
                                'vinculos', 'firjan']], how='inner')
d['reg'] = (d.index // 1000000).astype(int)
d['nordeste'] = (d.reg == 2).astype(int)
d['Tpc'] = d['T'] / d.populacao
d['Ypc'] = (d.renda_total - d['T']) / d.populacao
d['ocup_formal'] = d.vinculos / d.populacao
d.to_csv('out/base_municipal_idade.csv')

# ---------- 1. decomposição numerador x denominador ----------
ls, lt, ly = np.log(d.s), np.log(d.Tpc), np.log(d.renda_pc)
w = d.populacao / d.populacao.sum()
def wvar(x): m = np.average(x, weights=w); return np.average((x - m) ** 2, weights=w)
def wcov(x, y): return np.average((x - np.average(x, weights=w)) * (y - np.average(y, weights=w)), weights=w)
dec = pd.Series({'var_log_s': wvar(ls), 'var_log_Tpc': wvar(lt), 'var_log_Ypc': wvar(ly), 'menos_2cov': -2 * wcov(lt, ly)})

# ---------- 2. OLS com HC1 ----------
def ols(y, X, names):
    X = np.column_stack([np.ones(len(y))] + X); y = np.asarray(y, float)
    b, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ b
    n, k = X.shape; XtXi = np.linalg.inv(X.T @ X)
    V = XtXi @ (X.T * e ** 2) @ X @ XtXi * n / (n - k)
    r2 = 1 - e.var() / y.var()
    return pd.DataFrame({'coef': b, 'ep': np.sqrt(np.diag(V))}, index=['const'] + names), r2, e

age = ['sh_0_14', 'sh_55_59', 'sh_60_64', 'sh_65_69', 'sh_70m']
uf = pd.get_dummies(d.SIGLA_UF, drop_first=True).astype(float)
X1 = [d[c].values for c in age]
r_age, r2_age, _ = ols(d.s, X1, age)
X2 = X1 + [uf[c].values for c in uf.columns]
_, r2_uf, _ = ols(d.s, X2, age + list(uf.columns))
X3 = X2 + [np.log(d.ocup_formal.values), d.firjan.fillna(d.firjan.median()).values]
_, r2_eco, _ = ols(d.s, X3, age + list(uf.columns) + ['log_ocup_formal', 'ifdm'])

# random forest só com idade (resíduos fora da amostra: out-of-bag)
rf = RandomForestRegressor(n_estimators=500, min_samples_leaf=10, oob_score=True, random_state=1, n_jobs=-1)
rf.fit(d[age + ['sh_60m']], d.s)
d['s_prev_idade'] = rf.oob_prediction_
d['resid_idade'] = d.s - d.s_prev_idade
r2_rf = rf.oob_score_

# ---------- 3. atrito x atração ----------
env = d.sh_60m > np.average(d.sh_60m, weights=d.populacao)   # mais envelhecidos que o Brasil
d['envelhecido'] = env.astype(int)
d['tipo'] = 'não envelhecido'
d.loc[env & (d.mig_jovem < 0) & (d.mig_idoso <= 0), 'tipo'] = 'atrito'
d.loc[env & (d.mig_idoso > 0), 'tipo'] = 'atração'
d.loc[env & (d.tipo == 'não envelhecido'), 'tipo'] = 'misto'

tab = d.groupby('tipo').apply(lambda g: pd.Series({
    'n_munic': len(g), 'pop_mil': g.populacao.sum() / 1e3,
    'sh_60m': np.average(g.sh_60m, weights=g.populacao),
    'dependencia': g['T'].sum() / g.renda_total.sum(),
    'resid_idade_mediano': g.resid_idade.median(),
    'renda_pc_sem_transf': (g.renda_total - g['T']).sum() / g.populacao.sum(),
    'cresc_pop_mediano': g.cresc_pop.median(),
    'pct_nordeste': g.nordeste.mean() * 100}))

# resíduo da idade explicado pela migração (municípios envelhecidos)
e = d[env].dropna(subset=['mig_jovem', 'mig_idoso', 'resid_idade'])
e = e[np.isfinite(e.mig_jovem) & np.isfinite(e.mig_idoso)]
r_mig, r2_mig, _ = ols(e.resid_idade, [e.mig_jovem.values, e.mig_idoso.values, e.nordeste.values],
                       ['mig_jovem', 'mig_idoso', 'nordeste'])

reg_tab = d.groupby('reg').apply(lambda g: pd.Series({'dependencia': g['T'].sum() / g.renda_total.sum(),
                                                      'dep_prevista_idade': np.average(g.s_prev_idade, weights=g.populacao),
                                                      'resid_med': np.average(g.resid_idade, weights=g.populacao),
                                                      'mig_jovem_med': np.average(g.mig_jovem, weights=g.populacao)}))
reg_tab.index = ['Norte', 'Nordeste', 'Sudeste', 'Sul', 'Centro-Oeste']

with open('out/resultados.txt', 'w') as f:
    print('N municipios:', len(d), file=f)
    print('\n1. Decomposicao var log(dependencia) (pond. pop):\n', dec.round(4), file=f)
    print('\n2. OLS dependencia ~ idade:\n', r_age.round(3), file=f)
    print(f'R2 idade={r2_age:.3f}  +UF={r2_uf:.3f}  +economia={r2_eco:.3f}  RF idade OOB={r2_rf:.3f}', file=f)
    print('\nPor regiao:\n', reg_tab.round(3), file=f)
    print('\n3. Tipologia:\n', tab.round(3).to_string(), file=f)
    print('\nResiduo idade ~ migracao (envelhecidos):\n', r_mig.round(3), f'R2={r2_mig:.3f}', file=f)
    print('\nMig BR ratios', round(br_y, 3), round(br_o, 3), file=f)
    top = d.sort_values('resid_idade', ascending=False)
    print('\nMaiores residuos:\n', top[['NM_MUN', 'SIGLA_UF', 's', 's_prev_idade', 'mig_jovem', 'tipo']].head(15).round(3).to_string(), file=f)
    print('\nMenores residuos:\n', top[['NM_MUN', 'SIGLA_UF', 's', 's_prev_idade', 'mig_jovem', 'tipo']].tail(10).round(3).to_string(), file=f)
d.to_csv('out/base_municipal_idade.csv')
print(open('out/resultados.txt').read())
