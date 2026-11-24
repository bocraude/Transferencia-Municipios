"""Passo B: semiárido (delimitação Sudene vigente) no lugar da variável Nordeste no teste de atrito.
Fontes: IBGE, lista_municipios_Semiarido_2022.xlsx (1.477 = Res. Condel 150/2021 + 50 excluídos mantidos pelas
Res. 155/2022, 163/2022 e 176/2024); conferida contra o anexo da Res. 150/2021 (data/sudene/r150.txt).
Uso: python3 -I analise_semiarido.py  (depois de analise_situacao_2022.py)."""
import re
import numpy as np, pandas as pd

log = open('out/resultados_B.txt', 'w')
def say(*a): print(*a, file=log)

sa = set(pd.read_excel('data/sudene/lista_municipios_Semiarido_2022.xlsx').CD_MUN.astype(int))
r150 = set(int(x) for x in re.findall(r'\b(\d{7})\b', open('data/sudene/r150.txt').read()))
assert len(sa) == 1477 and len(r150) == 1427 and r150 <= sa

d = pd.read_csv('out/base_municipal_situacao_2022.csv', index_col=0)
d.index = d.index.astype(int)
d['semiarido'] = d.index.isin(sa).astype(int)                 # 1.477 (vigente)
d['semiarido_150'] = d.index.isin(r150).astype(int)           # 1.427 (critério climático de 2021)
d['nordeste_fora_sa'] = ((d.nordeste == 1) & (d.semiarido == 0)).astype(int)
pd.DataFrame({'cod': sorted(sa), 'res150_2021': [c in r150 for c in sorted(sa)]}).to_csv('out/semiarido_municipios.csv', index=False)

say('Semiarido: municipios', d.semiarido.sum(), '| no Nordeste', int(((d.semiarido == 1) & (d.nordeste == 1)).sum()),
    '| fora (MG/ES)', int(((d.semiarido == 1) & (d.nordeste == 0)).sum()), '| Nordeste fora do semiarido', d.nordeste_fora_sa.sum())
g = d.groupby(['nordeste', 'semiarido']).apply(lambda x: pd.Series({
    'n': len(x), 'pop_mil': x.populacao.sum() / 1e3, 'dependencia': x['T'].sum() / x.renda_total.sum(),
    'dep_mediana': x.s.median(), 'resid_idade_med': x.resid_idade.median(), 'mig_jovem_med': x.mig_jovem.median()}))
say('\nPerfil por Nordeste x semiarido:\n', g.round(3).to_string())

def ols(y, X, names):
    X = np.column_stack([np.ones(len(y))] + X); y = np.asarray(y, float)
    b, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ b
    n, k = X.shape; XtXi = np.linalg.inv(X.T @ X)
    V = XtXi @ (X.T * e ** 2) @ X @ XtXi * n / (n - k)
    return pd.DataFrame({'coef': b, 'ep': np.sqrt(np.diag(V))}, index=['const'] + names), 1 - e.var() / y.var()

env = d[(d.envelhecido == 1)].dropna(subset=['resid_idade', 'resid_dem', 'mig_jovem', 'mig_idoso', 'mig_jovem_mulher', 'mig_jovem_homem'])
env = env[np.isfinite(env[['mig_jovem', 'mig_idoso', 'mig_jovem_mulher', 'mig_jovem_homem']]).all(axis=1)]
say('\nMunicipios envelhecidos: N =', len(env))
specs = {'nordeste (original)': ['nordeste'], 'semiarido': ['semiarido'], 'semiarido 1.427 (Res. 150)': ['semiarido_150'],
         'semiarido + Nordeste fora do SA': ['semiarido', 'nordeste_fora_sa']}
tab = []
for yv, ylab in [('resid_idade', 'residuo idade'), ('resid_dem', 'residuo idade+elegib+ruralidade')]:
    for nm, ctrl in specs.items():
        xs = ['mig_jovem', 'mig_idoso'] + ctrl
        r, r2 = ols(env[yv], [env[c].values for c in xs], xs)
        say(f'\n{ylab} ~ migracao + {nm}:\n', r.round(3).to_string(), f'\nR2 = {r2:.3f}')
        tab.append({'y': ylab, 'controle': nm, 'b_mig_jovem': r.loc['mig_jovem', 'coef'], 'ep': r.loc['mig_jovem', 'ep'],
                    'b_regiao': r.loc[ctrl[0], 'coef'], 'R2': r2})
    for nm, ctrl in [('nordeste', ['nordeste']), ('semiarido', ['semiarido'])]:
        xs = ['mig_jovem_mulher', 'mig_jovem_homem', 'mig_idoso'] + ctrl
        r, r2 = ols(env[yv], [env[c].values for c in xs], xs)
        say(f'\n{ylab} ~ migracao por sexo + {nm}:\n', r.round(3).to_string(), f'\nR2 = {r2:.3f}')
# por situação (passo A), com semiárido
e2 = env[np.isfinite(env[['mig_jovem_urb', 'mig_jovem_rur']]).all(axis=1)]
for nm in ['nordeste', 'semiarido']:
    xs = ['mig_jovem_urb', 'mig_jovem_rur', 'mig_idoso', nm]
    r, r2 = ols(e2.resid_dem, [e2[c].values for c in xs], xs)
    say(f'\nresiduo demografico ~ migracao por situacao + {nm} (N={len(e2)}):\n', r.round(3).to_string(), f'\nR2 = {r2:.3f}')
# interação: o efeito da saída de jovens é diferente no semiárido?
env = env.assign(mj_x_sa=env.mig_jovem * env.semiarido)
xs = ['mig_jovem', 'mj_x_sa', 'mig_idoso', 'semiarido']
r, r2 = ols(env.resid_dem, [env[c].values for c in xs], xs)
say('\nresiduo demografico ~ mig_jovem x semiarido:\n', r.round(3).to_string(), f'\nR2 = {r2:.3f}')

say('\nResumo (coeficiente de mig_jovem e da dummy regional):\n', pd.DataFrame(tab).round(3).to_string(index=False))
t = pd.crosstab(d.tipo3.fillna('sem tipo'), d.semiarido, margins=True)
t.columns = ['fora SA', 'semiarido', 'total']
say('\nTipologia x semiarido (n municipios):\n', t.to_string())
d.to_csv('out/base_municipal_situacao_2022.csv')
log.close()
print(open('out/resultados_B.txt').read())
