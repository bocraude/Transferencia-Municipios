"""Passo E: robustez da equalização entre municípios.
Ponderado x não ponderado; regiões geográficas imediatas (RGI); Theil entre e dentro de UFs; Shapley por benefício;
efeitos marginais de Lerman-Yitzhaki; bootstrap. Tudo com duas medidas de renda própria:
  original = renda_total (Censo) - T (registros);  híbrida = trabalho (Censo, SIDRA 10297).
Uso: python3 -I analise_equalizacao_robustez.py  (depois de analise_renda_censo.py)."""
from itertools import combinations
from math import factorial
import numpy as np, pandas as pd

log = open('out/resultados_E.txt', 'w')
def say(*a): print(*a, file=log)

def gini(y, w):
    o = np.argsort(y); y, w = np.asarray(y, float)[o], np.asarray(w, float)[o]
    cw = np.cumsum(w) / w.sum(); cy = np.cumsum(y * w) / (y * w).sum()
    return 1 - np.sum((cw - np.r_[0, cw[:-1]]) * (cy + np.r_[0, cy[:-1]]))
def atk(y, w, e):
    y, w = np.asarray(y, float), np.asarray(w, float) / np.sum(w); m = np.sum(w * y)
    if e == 1: return 1 - np.exp(np.sum(w * np.log(y))) / m
    return 1 - np.sum(w * y ** (1 - e)) ** (1 / (1 - e)) / m
def theil(y, w):
    y, w = np.asarray(y, float), np.asarray(w, float) / np.sum(w); m = np.sum(w * y); return np.sum(w * (y / m) * np.log(y / m))
IND = {'gini': gini, 'atk_0.5': lambda y, w: atk(y, w, .5), 'atk_1': lambda y, w: atk(y, w, 1),
       'atk_2': lambda y, w: atk(y, w, 2), 'theil': theil}

d = pd.read_csv('out/base_municipal_renda_censo.csv', index_col=0)
d.index = d.index.astype(int)
BEN = ['apos_Rural', 'bolsa', 'bpc', 'apos_Urbano', 'seguro']
d['own_orig'] = d.renda_total - d['T']
d['own_hib'] = d.c_trab
d = d[(d.own_orig > 0) & (d.own_hib > 0)]
say('Municipios:', len(d))

def tabela(df, w, own):
    out = {}
    for nm, y in [('sem transf.', df[own] / df.populacao), ('com transf.', (df[own] + df['T']) / df.populacao)]:
        out[nm] = {k: f(y.values, w.values) for k, f in IND.items()}
    t = pd.DataFrame(out).T
    t.loc['reducao %'] = (1 - t.loc['com transf.'] / t.loc['sem transf.']) * 100
    return t

# ---------- 1. ponderado x não ponderado; município x RGI ----------
b = pd.read_csv('data/ibge/setores/Agregados_por_setores_basico_BR.csv', sep=';', encoding='latin1', usecols=['CD_MUN', 'CD_RGI', 'CD_UF'], dtype=str)
b = b[b.CD_MUN != '.'].drop_duplicates('CD_MUN')
rgi = b.set_index(b.CD_MUN.astype(int)).CD_RGI.astype(int)
d['rgi'] = rgi.reindex(d.index).values
d['uf'] = d.index // 100000
R = d.groupby('rgi')[['own_orig', 'own_hib', 'T', 'populacao'] + BEN].sum()
say('Regioes geograficas imediatas:', len(R))
for own, lab in [('own_orig', 'renda propria original (renda - T)'), ('own_hib', 'renda propria hibrida (trabalho Censo)')]:
    say(f'\n===== {lab} =====')
    say('\nMunicipios, ponderado pela populacao:\n', tabela(d, d.populacao, own).round(3).to_string())
    say('\nMunicipios, nao ponderado:\n', tabela(d, pd.Series(1.0, index=d.index), own).round(3).to_string())
    say('\nRegioes imediatas, ponderado:\n', tabela(R, R.populacao, own).round(3).to_string())

# ---------- 2. Theil entre e dentro de UFs ----------
def theil_dec(df, own, comp):
    y = (df[own] + (df['T'] if comp else 0)) / df.populacao; w = df.populacao / df.populacao.sum()
    m = np.sum(w * y); tot = theil(y, w)
    g = pd.DataFrame({'y': y * w, 'w': w, 'uf': df.uf}).groupby('uf').sum()
    yu = g.y / g.w
    entre = np.sum(g.w * (yu / m) * np.log(yu / m))
    return tot, entre, tot - entre
say('\n===== Theil-T entre e dentro de UFs (ponderado) =====')
rows = []
for own in ['own_orig', 'own_hib']:
    for comp in [False, True]:
        t, e, w_ = theil_dec(d, own, comp)
        rows.append({'renda propria': own, 'transferencias': 'com' if comp else 'sem', 'total': t, 'entre UFs': e, 'dentro UFs': w_, '% entre': e / t * 100})
tt = pd.DataFrame(rows)
say(tt.round(3).to_string(index=False))
for own in ['own_orig', 'own_hib']:
    a, c = tt[(tt['renda propria'] == own) & (tt.transferencias == 'sem')].iloc[0], tt[(tt['renda propria'] == own) & (tt.transferencias == 'com')].iloc[0]
    say(f'{own}: queda do Theil entre UFs {a["entre UFs"] - c["entre UFs"]:.3f}, dentro {a["dentro UFs"] - c["dentro UFs"]:.3f} '
        f'-> {(a["dentro UFs"] - c["dentro UFs"]) / (a.total - c.total):.1%} da queda vem de dentro das UFs')

# ---------- 3. Shapley por benefício (Gini, ponderado) ----------
def shapley(df, own, w, f=gini):
    base = df[own] / df.populacao
    def v(S): return f((df[own] + df[list(S)].sum(axis=1)) / df.populacao if S else base, w)
    n = len(BEN); val = {}
    for k in range(n + 1):
        for S in combinations(BEN, k): val[frozenset(S)] = v(S)
    phi = {}
    for i in BEN:
        oth = [x for x in BEN if x != i]; s = 0
        for k in range(n):
            for S in combinations(oth, k):
                wt = factorial(k) * factorial(n - k - 1) / factorial(n)
                s += wt * (val[frozenset(S)] - val[frozenset(S) | {i}])   # redução do índice
        phi[i] = s
    tot = val[frozenset()] - val[frozenset(BEN)]
    return pd.Series(phi), tot
say('\n===== Shapley: contribuicao de cada beneficio para a reducao do Gini (%) =====')
sh = {}
for own in ['own_orig', 'own_hib']:
    for wl, w in [('pond', d.populacao), ('nao pond', pd.Series(1.0, index=d.index))]:
        phi, tot = shapley(d, own, w.values)
        sh[f'{own} {wl}'] = (phi / tot * 100).round(1).to_dict() | {'reducao total': round(tot, 3)}
    phi, tot = shapley(R, own, R.populacao.values)
    sh[f'{own} RGI'] = (phi / tot * 100).round(1).to_dict() | {'reducao total': round(tot, 3)}
say(pd.DataFrame(sh).to_string())

# ---------- 4. Lerman-Yitzhaki ----------
def ly(df, own, w):
    w = np.asarray(w, float) / np.sum(w)
    comps = {'renda propria': df[own] / df.populacao} | {k: df[k] / df.populacao for k in BEN}
    Y = sum(comps.values())
    o = np.argsort(Y.values); cw = np.cumsum(w[o]); F = np.empty(len(Y)); F[o] = cw - w[o] / 2   # posto ponderado
    G = gini(Y.values, w); mY = np.sum(w * Y)
    rows = []
    for k, x in comps.items():
        x = x.values; mk = np.sum(w * x)
        Fk = np.empty(len(x)); ok = np.argsort(x); Fk[ok] = np.cumsum(w[ok]) - w[ok] / 2
        cov_y = np.sum(w * (x - mk) * (F - np.sum(w * F))); cov_k = np.sum(w * (x - mk) * (Fk - np.sum(w * Fk)))
        Gk = 2 * cov_k / mk; Rk = cov_y / cov_k; Sk = mk / mY
        rows.append({'fonte': k, 'S_k (parcela)': Sk, 'G_k': Gk, 'R_k': Rk, 'contrib. ao Gini %': Sk * Rk * Gk / G * 100,
                     'efeito marginal (dG/G por 1% de aumento)': Sk * (Rk * Gk / G - 1)})
    return pd.DataFrame(rows).set_index('fonte'), G
say('\n===== Lerman-Yitzhaki (renda total = renda propria + 5 beneficios) =====')
for own in ['own_orig', 'own_hib']:
    t, G = ly(d, own, d.populacao)
    say(f'\n{own}, ponderado (Gini = {G:.3f}; soma das contribuicoes = {t["contrib. ao Gini %"].sum():.1f}%):\n', t.round(3).to_string())

# ---------- 5. bootstrap ----------
rng = np.random.default_rng(2022); B = 1000
say(f'\n===== Bootstrap ({B} reamostragens de municipios, ponderado) =====')
for own in ['own_orig', 'own_hib']:
    y0 = (d[own] / d.populacao).values; y1 = ((d[own] + d['T']) / d.populacao).values; w = d.populacao.values
    res = []
    for _ in range(B):
        i = rng.integers(0, len(d), len(d))
        g0, g1 = gini(y0[i], w[i]), gini(y1[i], w[i]); a0, a1 = atk(y0[i], w[i], 2), atk(y1[i], w[i], 2)
        res.append([g0, g1, g0 - g1, a0, a1, a0 - a1])
    res = pd.DataFrame(res, columns=['gini sem', 'gini com', 'reducao gini', 'atk2 sem', 'atk2 com', 'reducao atk2'])
    q = res.quantile([.025, .5, .975]).T; q.columns = ['IC 2,5%', 'mediana', 'IC 97,5%']
    say(f'\n{own}:\n', q.round(3).to_string())
log.close()
print(open('out/resultados_E.txt').read())
