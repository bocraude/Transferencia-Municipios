"""Gera os arquivos de dados do painel interativo (painel/dados/*.json).
Entradas: out/base_municipal_renda_censo.csv (passos 1-C), SIDRA 10089 (2022), SIDRA 1378 (2010),
setores censitários (regiões imediatas e intermediárias), IBGE bioma predominante por município (2024).
Uso: python3 -I painel/gerar_dados_painel.py  (depois de analise_renda_censo.py)."""
import glob, json, os
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor

OUT = 'painel/dados'; os.makedirs(OUT, exist_ok=True)
CODE = open(__file__, encoding='utf-8').read()
def dump(name, df, inputs):
    df = df.replace([np.inf, -np.inf], np.nan)
    rows = [[None if pd.isna(v) else (v.item() if hasattr(v, 'item') else v) for v in r] for r in df.itertuples(index=False, name=None)]
    meta = [{'label': 'gerar_dados_painel.py', 'value': CODE, 'type': 'code', 'lang': 'python'},
            {'label': 'Entradas', 'value': inputs}]
    with open(f'{OUT}/{name}.json', 'w', encoding='utf-8') as f:
        json.dump({'columns': list(df.columns), 'rows': rows, 'meta': meta}, f, ensure_ascii=False, separators=(',', ':'))
    print(name, df.shape, round(os.path.getsize(f'{OUT}/{name}.json') / 1e6, 2), 'MB')

# ---------- base municipal ----------
d = pd.read_csv('out/base_municipal_renda_censo.csv', index_col=0); d.index = d.index.astype(int)
b = pd.read_csv('data/ibge/setores/Agregados_por_setores_basico_BR.csv', sep=';', encoding='latin1', dtype=str,
                usecols=['CD_MUN', 'CD_RGI', 'NM_RGI', 'CD_RGINT', 'NM_RGINT', 'NM_UF'])
b = b[b.CD_MUN != '.'].drop_duplicates('CD_MUN').set_index(b[b.CD_MUN != '.'].drop_duplicates('CD_MUN').CD_MUN.astype(int))
bio = pd.read_csv('data/ibge/biomas/Bioma_Predominante_por_Municipio_2024.csv', sep=';', encoding='utf-8-sig')
bio = bio[pd.to_numeric(bio.iloc[:, 0], errors='coerce').notna()]   # rodapé com notas
bio = bio.set_index(bio.iloc[:, 0].astype(int))[bio.columns[3]]
REG = {1: 'Norte', 2: 'Nordeste', 3: 'Sudeste', 4: 'Sul', 5: 'Centro-Oeste'}
m = pd.DataFrame({
    'cod': d.index, 'nome': d.NM_MUN, 'uf': d.SIGLA_UF, 'regiao': d.reg.map(REG),
    'rgi': b.NM_RGI.reindex(d.index).values, 'rgint': b.NM_RGINT.reindex(d.index).values,
    'bioma': bio.reindex(d.index).values, 'semiarido': np.where(d.semiarido == 1, 'Semiárido', 'Fora do semiárido'),
    'pop': d.populacao, 'renda': d.renda_total.round(0), 'trab_censo': d.c_trab.round(0),
    'bpc': d.bpc.round(0), 'bolsa': d.bolsa.round(0), 'seguro': d.seguro.round(0),
    'apos_rural': d.apos_Rural.round(0), 'apos_urbana': d.apos_Urbano.round(0),
    'dep': d.s.round(4), 'dep_prev_idade': d.s_prev_idade.round(4), 'resid_idade': d.resid_idade.round(4),
    'tipo': d.tipo2, 'tipo_situacao': d.tipo3,
    'mig_jovem': d.mig_jovem.round(4), 'mig_idoso': d.mig_idoso.round(4),
    'mig_jovem_mulher': d.mig_jovem_mulher.round(4), 'mig_jovem_homem': d.mig_jovem_homem.round(4),
    'mig_jovem_urb': d.mig_jovem_urb.round(4), 'mig_jovem_rur': d.mig_jovem_rur.round(4),
    'sh_60m': d.sh_60m.round(4), 'rural_10': d.rural_sh_10.round(4), 'rural_22': d.rural_sh_22.round(4),
    'cobertura_rural': d.cobertura_rural_22.round(3)})
assert m.rgi.notna().all() and m.bioma.notna().all()
m['tipo'] = m.tipo.fillna('sem dados de migração'); m['tipo_situacao'] = m.tipo_situacao.fillna('sem dados de migração')
m = m.astype({c: 'float' for c in m.columns[8:] if pd.api.types.is_numeric_dtype(m[c])})
for c in ['cod', 'pop']: m[c] = m[c].astype(int)
dump('municipios', m, 'out/base_municipal_renda_censo.csv; setores (CD_RGI, CD_RGINT); Bioma_Predominante_por_Municipio_2024.csv')

# ---------- pirâmides 2010 x 2022 (sexo x 15 grupos) ----------
GR = ['0_9', '10_14', '15_19', '20_24', '25_29', '30_34', '35_39', '40_44', '45_49', '50_54', '55_59', '60_64', '65_69', '70_74', '75m']
IDADE = {1140: '0_9', 1141: '0_9', 1142: '10_14', 1143: '15_19', 1144: '20_24', 1145: '25_29', 1146: '30_34', 1147: '35_39',
         1148: '40_44', 1149: '45_49', 1150: '50_54', 1151: '55_59', 1152: '60_64', 1153: '65_69', 1154: '70_74'}
rows = []
for f in sorted(glob.glob('data/ibge/sidra10089/uf*.json')): rows += json.load(open(f))
s = pd.DataFrame(rows)
s = pd.DataFrame({'cod': s.D1C.astype(int), 'sx': s.D4C.map({'4': 'h', '5': 'm'}),
                  'g': s.D5C.astype(int).map(IDADE).fillna('75m'), 'pop': pd.to_numeric(s.V, errors='coerce').fillna(0)})
p22 = s.pivot_table(index='cod', columns=['sx', 'g'], values='pop', aggfunc='sum')
def load1378(f):
    c = pd.read_excel(f, header=None).iloc[6:-1, [0, 2, 4]]; c.columns = ['cod', 'idade', 'pop']
    c['cod'] = pd.to_numeric(c['cod'], errors='coerce').ffill(); c['pop'] = pd.to_numeric(c['pop'], errors='coerce').fillna(0)
    p = c.pivot_table(index='cod', columns='idade', values='pop', aggfunc='sum'); g = pd.DataFrame(index=p.index.astype(int))
    g['15_19'] = p['15 a 17 anos'].values + p['18 ou 19 anos'].values
    for a in [10, 20, 25, 30, 35, 40, 45, 50, 55]: g[f'{a}_{a+4}'] = p[f'{a} a {a+4} anos'].values
    g['60_64'] = (p['60 a 64 anos'] if '60 a 64 anos' in p else p['60 a 69 anos'] - p['65 a 69 anos']).values
    g['65_69'] = (p['65 a 69 anos'] if '65 a 69 anos' in p else p['60 a 69 anos'] - p['60 a 64 anos']).values
    g['75m'] = (p['75 a 79 anos'] + p['80 a 89 anos'] + p['90 a 99 anos'] + p['100 anos ou mais']).values
    g['70_74'] = (p['70 a 74 anos'] if '70 a 74 anos' in p else p['70 anos ou mais'] - p['75 a 79 anos'] - p['80 a 89 anos'] - p['90 a 99 anos'] - p['100 anos ou mais']).values
    tot = (p['Total'] if 'Total' in p else p.drop(columns=[]).sum(axis=1) * np.nan).values
    g['0_9'] = (p['0 a 4 anos'] + p['5 a 9 anos']).values if '0 a 4 anos' in p else tot - g.sum(axis=1).values
    return g[GR]
T10 = load1378('data/censo/c.xlsx'); W10 = load1378('data/censo/t_m.xlsx').reindex(T10.index).fillna(0); H10 = T10 - W10
assert (H10.to_numpy() >= 0).all()
pir = pd.DataFrame({'cod': p22.index})
for sx in ['h', 'm']:
    for g in GR: pir[f'{sx}22_{g}'] = p22[sx][g].reindex(p22.index).values.astype(int)
for sx, src in [('h', H10), ('m', W10)]:
    for g in GR: pir[f'{sx}10_{g}'] = src[g].reindex(p22.index).values
pir = pir[pir.cod.isin(m.cod)]
dump('piramides', pir, 'SIDRA 10089 (Censo 2022) e SIDRA 1378 (Censo 2010), homens 2010 = total - mulheres')

# ---------- regressões ----------
def ols(y, X, names):
    X = np.column_stack([np.ones(len(y))] + X); y = np.asarray(y, float)
    bb, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ bb
    n, k = X.shape; XtXi = np.linalg.inv(X.T @ X); V = XtXi @ (X.T * e ** 2) @ X @ XtXi * n / (n - k)
    return bb, np.sqrt(np.diag(V)), 1 - e.var() / y.var(), n
out = []
def add(modelo, tema, y, cols, df, rotulos):
    bb, ep, r2, n = ols(df[y], [df[c].values for c in cols], cols)
    for v, c, e in zip(['const'] + cols, bb, ep):
        if v == 'const': continue
        out.append({'modelo': modelo, 'tema': tema, 'variavel': rotulos.get(v, v), 'coef': round(c, 4), 'ep': round(e, 4),
                    'ic_baixo': round(c - 1.96 * e, 4), 'ic_alto': round(c + 1.96 * e, 4), 'n': n, 'r2': round(r2, 3)})
    return r2
age = ['sh_0_14', 'sh_55_59', 'sh_60_64', 'sh_65_69', 'sh_70m']
ROT = {'sh_0_14': 'Parcela 0–14 anos', 'sh_55_59': 'Parcela 55–59', 'sh_60_64': 'Parcela 60–64', 'sh_65_69': 'Parcela 65–69',
       'sh_70m': 'Parcela 70+', 'mig_jovem': 'Migração jovem (20–29→32–41)', 'mig_idoso': 'Migração idosa (50–59→62–71)',
       'nordeste': 'Nordeste', 'semiarido': 'Semiárido', 'mig_jovem_mulher': 'Migração jovem – mulheres',
       'mig_jovem_homem': 'Migração jovem – homens', 'mig_jovem_urb': 'Migração jovem urbana', 'mig_jovem_rur': 'Migração jovem rural',
       'nordeste_fora_sa': 'Nordeste fora do semiárido'}
r2_idade = add('A1. Dependência ~ estrutura etária (MQO)', 'Estrutura etária', 's', age, d, ROT)
uf = pd.get_dummies(d.SIGLA_UF, drop_first=True).astype(float)
dd = d.join(uf.add_prefix('uf_')); ufc = list(uf.add_prefix('uf_').columns)
_, _, r2_uf, _ = ols(dd.s, [dd[c].values for c in age + ufc], age + ufc)
dd['log_ocup'] = np.log(dd.ocup_formal); dd['ifdm'] = dd.firjan.fillna(dd.firjan.median())
_, _, r2_eco, _ = ols(dd.s, [dd[c].values for c in age + ufc + ['log_ocup', 'ifdm']], age + ufc + ['log_ocup', 'ifdm'])
ok = d.dropna(subset=age + ['rural_sh_10', 'eleg_rural_22', 'eleg_urb_22', 'eleg_rural_10', 'rural_sh_22'])
def rf(cols):
    r = RandomForestRegressor(n_estimators=500, min_samples_leaf=10, oob_score=True, random_state=1, n_jobs=-1)
    r.fit(ok[cols], ok.s); return r.oob_score_
aj = [('Idade (MQO)', r2_idade, 'MQO'), ('Idade + UF (MQO)', r2_uf, 'MQO'), ('Idade + UF + economia (MQO)', r2_eco, 'MQO'),
      ('Idade (random forest, fora da amostra)', rf(age + ['sh_60m']), 'RF'),
      ('Idade + elegibilidade por sexo (RF)', rf(age + ['eleg_rural_22', 'eleg_urb_22']), 'RF'),
      ('+ ruralidade 2010 (RF)', rf(age + ['eleg_rural_22', 'eleg_urb_22', 'rural_sh_10', 'eleg_rural_10']), 'RF'),
      ('+ ruralidade 2022 (RF)', rf(age + ['eleg_rural_22', 'eleg_urb_22', 'rural_sh_22', 'sh_eleg_rural_22', 'rural_sh_eleg_22']), 'RF')]
dump('ajuste_idade', pd.DataFrame([{'ordem': i + 1, 'especificacao': a, 'r2': round(b_, 3), 'metodo': c} for i, (a, b_, c) in enumerate(aj)]),
     'out/base_municipal_renda_censo.csv (R² do MQO e R² fora da amostra do random forest)')
env = d[d.envelhecido == 1].dropna(subset=['resid_idade', 'resid_dem', 'mig_jovem', 'mig_idoso', 'mig_jovem_mulher', 'mig_jovem_homem'])
env = env[np.isfinite(env[['mig_jovem', 'mig_idoso', 'mig_jovem_mulher', 'mig_jovem_homem']]).all(axis=1)]
add('B1. Resíduo da idade ~ migração + Nordeste', 'Atrito × atração', 'resid_idade', ['mig_jovem', 'mig_idoso', 'nordeste'], env, ROT)
add('B2. Resíduo da idade ~ migração + semiárido', 'Atrito × atração', 'resid_idade', ['mig_jovem', 'mig_idoso', 'semiarido'], env, ROT)
add('B3. Resíduo demográfico ~ migração + semiárido + Nordeste fora do SA', 'Atrito × atração', 'resid_dem',
    ['mig_jovem', 'mig_idoso', 'semiarido', 'nordeste_fora_sa'], env, ROT)
add('B4. Resíduo demográfico ~ migração por sexo + Nordeste', 'Atrito × atração', 'resid_dem',
    ['mig_jovem_mulher', 'mig_jovem_homem', 'mig_idoso', 'nordeste'], env, ROT)
e2 = env[np.isfinite(env[['mig_jovem_urb', 'mig_jovem_rur']]).all(axis=1)]
add('B5. Resíduo demográfico ~ migração por situação + Nordeste', 'Atrito × atração', 'resid_dem',
    ['mig_jovem_urb', 'mig_jovem_rur', 'mig_idoso', 'nordeste'], e2, ROT)
dump('regressoes', pd.DataFrame(out), 'out/base_municipal_renda_censo.csv; erros-padrão robustos (HC1); IC de 95%')
