"""Gera uma versão autônoma do painel (um único .html, sem servidor e sem login) para compartilhar.
Embute os dados de painel/dados/*.json, o d3 v7 e um pequeno motor que reproduz a API `dash` usada por painel/index.html.
Uso: python3 -I painel/gerar_html_standalone.py <caminho/do/d3.min.js> [saida.html]"""
import json, re, sys, datetime

D3 = sys.argv[1]
SAIDA = sys.argv[2] if len(sys.argv) > 2 else 'out/painel_transferencias_municipios.html'
pagina = open('painel/index.html', encoding='utf-8').read()
pagina = re.sub(r'<meta name="dash-[^"]+"[^>]*>\n?', '', pagina)
dados = {k: json.load(open(f'painel/dados/{k}.json', encoding='utf-8')) for k in ['municipios', 'piramides', 'regressoes', 'ajuste_idade', 'malha']}
for v in dados.values(): v.pop('meta', None)
PARAMS = {'nivel': 'uf', 'medida': 'orig', 'pond': '1', 'unidade': 'mun', 'mapvar': 'dep'}
hoje = datetime.date.today().strftime('%d/%m/%Y')

TOKENS = """
:root { --color-bg:#fbfbf9; --color-panel:#ffffff; --color-fg:#1d2321; --color-fg-muted:#5d6763; --color-border-line:#dfe3e0;
  --color-ok:#2f7d4f; --color-warn:#a86b00; --color-bad:#b8432f;
  --font-anthropic-sans: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-anthropic-serif: Georgia, "Times New Roman", serif;
  --cds-font-size-caption:12px; --cds-font-size-body:14px; --cds-font-size-heading:17px; --cds-font-size-title:28px; --cds-font-weight-medium:600;
  --cds-gap-xs:4px; --cds-gap-sm:8px; --cds-gap-md:12px; --cds-gap-lg:18px; --cds-gap-xl:28px;
  --cds-pad-xs:4px; --cds-pad-sm:8px; --cds-pad-md:12px; --cds-pad-lg:16px; --cds-pad-xl:24px; --cds-radius:8px;
  --cds-chart-muted:#b9c2be; --cds-chart-grid:#e9ecea; --cds-chart-axis:#c9cfcc; --cds-chart-reference:#7c8682; --cds-chart-status-critical:#b8432f;
  --cds-text-secondary:#5d6763; --cds-surface-popover:#ffffff; --cds-border:#dfe3e0; --cds-shadow-popover:0 4px 16px rgba(0,0,0,.12);
  --s0:#2b6cb0; --s1:#d97a2b; --s2:#7a5cc4; --s3:#2a9d8f; --s4:#c2417a; color-scheme: light; }
@media (prefers-color-scheme: dark) { :root { --color-bg:#151918; --color-panel:#1d2221; --color-fg:#e8ecea; --color-fg-muted:#a3ada9; --color-border-line:#333b38;
  --color-ok:#6cc08b; --color-warn:#e0a83a; --color-bad:#ec7b66; --cds-chart-muted:#56605c; --cds-chart-grid:#2a312e; --cds-chart-axis:#3c4541;
  --cds-chart-reference:#8f9a96; --cds-text-secondary:#a3ada9; --cds-surface-popover:#242a29; --cds-border:#3a4340; --cds-shadow-popover:0 4px 16px rgba(0,0,0,.5);
  --s0:#6ea8e8; --s1:#f0a35e; --s2:#a993e6; --s3:#5cc3b6; --s4:#e57aa8; color-scheme: dark; } }
html, body { margin:0; background:var(--color-bg); color:var(--color-fg); font-family:var(--font-anthropic-sans); font-size:14px; }
#dash-root { max-width:1200px; margin:0 auto; padding-block:24px 40px; padding-left:max(16px, env(safe-area-inset-left, 0px)); padding-right:max(16px, env(safe-area-inset-right, 0px)); }
.dash-select { font:inherit; font-size:var(--cds-font-size-body); color:var(--color-fg); background-color:var(--color-bg); border:1px solid var(--color-border-line); border-radius:var(--cds-radius); padding:6px 8px; }
.dash-skeleton { position:relative; color:transparent !important; }
.dash-skeleton::after { content:""; position:absolute; inset:0; border-radius:4px; background:var(--cds-chart-grid); }
.tm-rodape { margin-top:32px; font-size:12px; color:var(--color-fg-muted); line-height:1.5; max-width:80ch; }
"""

MOTOR = r"""
(function () {
  const RAW = JSON.parse(document.getElementById('dados-painel').textContent);
  const PADRAO = JSON.parse(document.getElementById('params-painel').textContent);
  const loaders = {}, calcs = {}, draws = new Map(), onDatas = [], cache = new Map(), raw = new Map(), feitos = new WeakMap();
  let params = Object.assign({}, PADRAO), agendado = false;
  const ler = (id) => {
    if (calcs[id]) { const c = calcs[id]; return c.fn(...c.inputs.map((i) => dash.data(i).data)); }
    if (!raw.has(id)) { const a = RAW[id]; if (!a) throw new Error('Base ausente: ' + id); raw.set(id, loaders[id] ? loaders[id]({ answer: a }).data : a); }
    return raw.get(id);
  };
  const rodar = (nome) => {
    const f = draws.get(nome); if (!f) return;
    document.querySelectorAll(`[data-draw="${nome}"]`).forEach((el) => {
      if (el.closest('[hidden]')) return;
      try {
        if (typeof f === 'function') f(el);
        else { if (!feitos.has(el)) feitos.set(el, f.mount ? f.mount(el) : undefined); if (f.update) f.update(el, feitos.get(el)); }
      } catch (e) { console.error('desenho ' + nome, e); }
    });
  };
  const tudo = () => { agendado = false; onDatas.forEach((f) => { try { f(); } catch (e) { console.error(e); } }); draws.forEach((_, n) => rodar(n)); };
  const agendar = () => { if (!agendado) { agendado = true; requestAnimationFrame(tudo); } };
  window.dash = {
    colors: ['var(--s0)', 'var(--s1)', 'var(--s2)', 'var(--s3)', 'var(--s4)'],
    loader: (id, o) => { loaders[id] = o.fn; },
    calc: (id, o) => { calcs[id] = o; },
    params: () => Object.assign({}, params),
    setParams: (p) => { Object.entries(p).forEach(([k, v]) => { if (v == null || v === '') delete params[k]; else params[k] = v; }); cache.clear(); agendar(); },
    resetParams: () => { params = Object.assign({}, PADRAO); cache.clear(); agendar(); },
    setLink: (n) => { try { history.replaceState(null, '', '#' + n); } catch (e) { /* arquivo local */ } },
    refresh: () => {},
    data: (id) => {
      if (cache.has(id)) return cache.get(id);
      let r; try { r = { status: 'ok', data: ler(id) }; } catch (e) { console.error(e); r = { status: 'error', data: [], message: String(e) }; }
      cache.set(id, r); return r;
    },
    onData: (fn) => { onDatas.push(fn); },
    draw: (nome, fn) => { if (fn === undefined) rodar(nome); else draws.set(nome, fn); },
    _iniciar: () => {
      tudo();
      let t; window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(agendar, 150); });
      new MutationObserver((ms) => { if (ms.some((m) => m.target.classList && m.target.classList.contains('tm-sec'))) agendar(); })
        .observe(document.body, { attributes: true, attributeFilter: ['hidden'], subtree: true });
    }
  };
})();
"""

html = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Transferências e Municípios</title>
<style>{TOKENS}</style>
<script>{open(D3, encoding='utf-8').read()}</script>
<script type="application/json" id="dados-painel">{json.dumps(dados, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')}</script>
<script type="application/json" id="params-painel">{json.dumps(PARAMS)}</script>
</head>
<body>
<script>{MOTOR}</script>
<div id="dash-root">
{pagina}
<p class="tm-rodape">Versão para compartilhar gerada em {hoje}. Fontes: IBGE (Censos 2010 e 2022, SIDRA 1378, 9514, 10089 e 10297; malha municipal; regiões geográficas; bioma predominante 2024), Sudene (semiárido) e registros administrativos de 2022 dos benefícios. Valores mensais de 2022. Resultados contábeis, sem interpretação causal.</p>
</div>
<script>dash._iniciar();</script>
</body>
</html>
"""
open(SAIDA, 'w', encoding='utf-8').write(html)
print(SAIDA, round(len(html.encode('utf-8')) / 1e6, 2), 'MB')
