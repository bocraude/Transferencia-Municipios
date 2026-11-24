// Projeta a malha municipal do IBGE (API de malhas v3, qualidade mínima) em caminhos SVG para o mapa do painel.
// Uso: node painel/gerar_malha.mjs <malha.json> <saida.json>   (precisa de d3@7.9 e topojson-client@3.1)
import fs from 'fs';
import * as d3 from 'd3';
import * as topojson from 'topojson-client';
const [, , entrada, saida] = process.argv;
const topo = JSON.parse(fs.readFileSync(entrada, 'utf8'));
const obj = topo.objects.BRMU;
const fc = topojson.feature(topo, obj);
const W = 1000, H = 1000;
const proj = d3.geoConicEqualArea().parallels([-2, -22]).rotate([54, 0]).fitSize([W, H], fc);
const path = d3.geoPath(proj).digits(1);
const uf = (g) => g.properties.codarea.slice(0, 2);
const rows = fc.features.map((f) => [+f.properties.codarea, path(f)]);
rows.push([0, path(topojson.mesh(topo, obj, (a, b) => a !== b && uf(a) !== uf(b)))]);   // divisas estaduais
rows.push([1, path(topojson.mesh(topo, obj, (a, b) => a === b))]);                      // contorno do país
const [[x0, y0], [x1, y1]] = path.bounds(fc);
fs.writeFileSync(saida, JSON.stringify({ columns: ['cod', 'd'], rows,
  meta: [{ label: 'gerar_malha.mjs', value: fs.readFileSync(new URL(import.meta.url), 'utf8'), type: 'code', lang: 'javascript' },
         { label: 'Entrada', value: 'IBGE, API de malhas v3: /malhas/paises/BR?qualidade=minima&intrarregiao=municipio' },
         { label: 'Caixa (viewBox)', value: `${x0.toFixed(0)} ${y0.toFixed(0)} ${(x1 - x0).toFixed(0)} ${(y1 - y0).toFixed(0)}` },
         { label: 'Linhas especiais', value: 'cod 0 = divisas estaduais; cod 1 = contorno do Brasil' }] }));
console.log(rows.length, 'caminhos;', (fs.statSync(saida).size / 1e6).toFixed(2), 'MB; bounds', x0, y0, x1, y1);
