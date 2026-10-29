/* The 24 ready-made answer plots, three per question category. The server
   picks the category and the plot (/api/plot-answer); these builders take
   its real figures and draw it. Kept in one closure so its short names do
   not clash with the dashboard's. Palette and rules as the dashboard. */
window.PlotTemplates = (function () {
  const AX = '#9FB7C9', GRID = 'rgba(117, 214, 255, 0.10)', TXT = '#E6F0F6';
  const CYAN = '#75D6FF', MINT = '#2EF2B0', CORAL = '#FF4F7B', AMBER = '#FFC547', VIOLET = '#7C6CFF';
  const CATS = ['#75D6FF', '#3A8FD9', '#7C6CFF', '#4FB3C9', '#5B7C93', '#A9C6D8', '#2E4F66'];
  const STATUS = {new: CYAN, revised: AMBER, superseded: '#5B7C93'};
  const tip = {backgroundColor: '#0E2C3D', borderColor: '#14384C', textStyle: {color: TXT, fontSize: 11}};
  const axisCat = d => ({type: 'category', data: d, axisTick: {show: false},
    axisLabel: {color: AX, fontSize: 10}, axisLine: {lineStyle: {color: GRID}}});
  const axisVal = x => Object.assign({type: 'value', axisLabel: {color: AX, fontSize: 10},
    splitLine: {lineStyle: {color: GRID}}}, x || {});
  const glow = c => ({color: c, shadowColor: c, shadowBlur: 6});
  const fade = (r, g, b) => ({color: new echarts.graphic.LinearGradient(0, 0, 0, 1,
    [{offset: 0, color: `rgba(${r},${g},${b},.30)`}, {offset: 1, color: `rgba(${r},${g},${b},0)`}])});
  /* The label sat on the right edge and was clipped to "tr". It rides
     the line on the inside now, where the panel always has room. */
  const refY = (v, t) => ({symbol: 'none', silent: true,
    label: {color: AX, fontSize: 10, formatter: t, position: 'insideEndTop'},
    lineStyle: {color: 'rgba(230,240,246,.8)', type: 'dashed', width: 1}, data: [{yAxis: v}]});
  const grid = rows => {
    const out = [];
    rows.forEach((row, r) => row.forEach((v, c) => out.push([c, r, v])));
    return out;
  };
  const arrow = (v, unit) => v === null ? 'no earlier figure'
    : `<span class="up-${v >= 0 ? 'good' : 'bad'}">${v >= 0 ? '▲' : '▼'}</span> ${Math.abs(v)}${unit}`;

  /* Each plot draws inside its own shadow root with this style alone. The
     dashboard's own classes (.step, .when, .card, .item...) leaked into
     the plots and broke them. */
  const CSS = `
:host { display: block; height: 100%; }
* { box-sizing: border-box; }
.tpl { position: relative; font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.35; height: 100%; color: #E6F0F6; font-size: 12.5px; }
.tpl .chart { position: absolute; inset: 0; }
.tpl .big { font-size: 30px; font-weight: 700; color: #75D6FF; text-shadow: 0 0 14px rgba(117,214,255,.45); line-height: 1; }
.tpl .chg { font-size: 11.5px; color: #9FB7C9; }
.tpl .up-good { color: #2EF2B0; } .tpl .up-bad { color: #FF4F7B; }
.tpl .met { color: #2EF2B0; font-weight: 700; } .tpl .missed { color: #FF4F7B; font-weight: 700; }
.tpl .bullet { margin: 8px 0 16px; }
.tpl .bullet .lab { display: flex; justify-content: space-between; margin-bottom: 5px; }
.tpl .bullet .track { position: relative; height: 6px; border-radius: 3px; background: rgba(117,214,255,.1); }
.tpl .bullet .fill { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 3px; }
.tpl .bullet .mark { position: absolute; top: -4px; bottom: -4px; border-left: 1.5px dashed rgba(230,240,246,.8); }
.tpl table { width: 100%; border-collapse: collapse; table-layout: fixed; }
.tpl th { text-align: left; color: #9FB7C9; font-size: 10.5px; text-transform: uppercase; padding: 4px;
  border-bottom: 1px solid rgba(117,214,255,.24); }
.tpl td { padding: 5px 4px; border-bottom: 1px solid rgba(117,214,255,.1); white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; }
.tpl td.id { color: #3FD0FF; text-shadow: 0 0 8px rgba(63,208,255,.4); }
.tpl .chip { display: inline-block; padding: 0 6px; border-radius: 4px; font-size: 11px; font-weight: 700; }
.tpl .chip.new { color: #75D6FF; background: rgba(117,214,255,.12); }
.tpl .chip.revised { color: #FFC547; background: rgba(255,197,71,.14); }
.tpl .chip.superseded { color: #8FA9BC; background: rgba(159,183,201,.12); }
.tpl .item { display: flex; gap: 8px; padding: 6px 0; border-bottom: 1px solid rgba(117,214,255,.1); }
.tpl .dot { width: 8px; height: 8px; border-radius: 50%; margin-top: 5px; flex: none; }
.tpl .tl { position: relative; padding-left: 18px; }
.tpl .tl::before { content: ''; position: absolute; left: 4px; top: 4px; bottom: 4px; width: 1px; background: rgba(117,214,255,.35); }
.tpl .tl .step { position: relative; padding: 2px 0 8px; }
.tpl .tl .step::before { content: ''; position: absolute; left: -17px; top: 6px; width: 8px; height: 8px;
  border-radius: 50%; background: #75D6FF; box-shadow: 0 0 6px #75D6FF; }
.tpl .tl .step.warn::before { background: #FFC547; box-shadow: 0 0 6px #FFC547; }
.tpl .tl .when { color: #9FB7C9; font-size: 11px; }
.tpl .card { display: grid; grid-template-columns: auto 1fr; gap: 6px 14px; }
.tpl .card .k { color: #9FB7C9; } .tpl .card .v { text-align: right; }
.tpl .tiles { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; height: 100%; }
.tpl .tile { border: 1px solid rgba(117,214,255,.16); border-radius: 7px; padding: 5px 8px;
  display: flex; flex-direction: column; min-height: 0; background: rgba(14,44,61,.45); }
.tpl .tile .n { font-size: 11px; color: #9FB7C9; } .tpl .tile .v { font-size: 18px; font-weight: 700; }
.tpl .tile .spark { flex: 1; min-height: 0; }`;

  /* For each category, three builders that take the server's figures and
     return a title and either HTML or a chart option. */
  const PLOTS = {
    volume: [
      f => ({kind: 'Columns', title: 'Invoices per week',
        html: `<div style="display:flex;gap:12px;align-items:flex-end;height:36px"><div class="big">${f.total}</div>` +
              `<div class="chg">${arrow(f.vs_week, '% last week')}<br>${arrow(f.vs_month, '% last month')}</div></div>` +
              '<div style="position:absolute;left:0;right:0;top:42px;bottom:0"><div class="chart"></div></div>',
        option: {grid: {left: 28, right: 4, top: 8, bottom: 20}, xAxis: axisCat(f.weeks), yAxis: axisVal(),
          series: [{type: 'bar', barWidth: '50%', data: f.counts.map((v, i) =>
            ({value: v, itemStyle: glow(i === f.counts.length - 1 ? CYAN : 'rgba(117,214,255,.45)')}))}]}}),
      f => ({kind: 'Heatmap', title: 'Invoices by weekday and week',
        option: {grid: {left: 34, right: 4, top: 4, bottom: 20}, xAxis: axisCat(f.weeks),
          yAxis: Object.assign(axisCat(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']), {inverse: true}),
          visualMap: {show: false, min: 0, max: Math.max(1, ...f.weekday.flat()),
                      inRange: {color: ['rgba(117,214,255,0.05)', CYAN]}},
          series: [{type: 'heatmap', data: grid(f.weekday), label: {show: true, color: '#061C28', fontSize: 10,
            formatter: p => p.value[2] || ''}, itemStyle: {borderColor: '#061C28', borderWidth: 2, borderRadius: 3}}]}}),
      f => ({kind: 'Cumulative area', title: 'Invoices so far in the period',
        option: {grid: {left: 30, right: 30, top: 10, bottom: 20},
          xAxis: Object.assign(axisCat(f.weeks), {boundaryGap: false}), yAxis: axisVal(),
          series: [{type: 'line', smooth: true, symbol: 'none',
            data: f.counts.reduce((a, v) => a.concat([(a[a.length - 1] || 0) + v]), []),
            lineStyle: {width: 2, color: CYAN, shadowColor: CYAN, shadowBlur: 8}, areaStyle: fade(117, 214, 255),
            endLabel: {show: true, color: CYAN, fontSize: 12, fontWeight: 700}}]}}),
    ],
    target: [
      f => ({kind: 'Bullets', title: 'Are we on target this week?',
        html: f.bullets.map(([name, value, target, met]) => {
          const fill = name.startsWith('Automation') ? Math.min(100, value * 20) : value;
          const mark = name.startsWith('Automation') ? 20 : 100;
          return `<div class="bullet"><div class="lab"><span>${name}</span><span class="${met ? 'met' : 'missed'}">${value}%</span></div>` +
            `<div class="track"><div class="fill" style="width:${Math.max(fill, 1)}%;background:${met ? MINT : CORAL}"></div>` +
            `<div class="mark" style="left:${mark}%"></div></div></div>`;
        }).join('')}),
      f => ({kind: 'Gauge', title: 'Processed this week',
        option: {series: [{type: 'gauge', startAngle: 210, endAngle: -30, min: 0, max: 100, radius: '90%',
          center: ['50%', '58%'], progress: {show: true, width: 10,
            itemStyle: glow(f.completed[f.completed.length - 1] >= 100 ? MINT : CORAL)},
          axisLine: {lineStyle: {width: 10, color: [[1, 'rgba(117,214,255,0.1)']]}},
          axisTick: {show: false}, splitLine: {show: false}, axisLabel: {show: false}, pointer: {show: false},
          title: {offsetCenter: [0, '40%'], color: AX, fontSize: 11},
          detail: {offsetCenter: [0, '0%'], fontSize: 30, fontWeight: 700, formatter: '{value}%',
                   color: f.completed[f.completed.length - 1] >= 100 ? MINT : CORAL},
          data: [{value: f.completed[f.completed.length - 1], name: 'target 100%'}]}]}}),
      /* As in the preview: completed per week, a white line whose points
         are mint on target and coral below it, under the dashed target. */
      f => ({kind: 'Line with target', title: 'Completed per week',
        option: {grid: {left: 40, right: 10, top: 12, bottom: 20},
          xAxis: Object.assign(axisCat(f.weeks), {boundaryGap: false}),
          yAxis: axisVal({min: v => Math.max(0, Math.floor((v.min - 5) / 5) * 5), max: 100,
                          axisLabel: {color: AX, fontSize: 10, formatter: '{value}%'}}),
          series: [{type: 'line', data: f.completed, symbolSize: 7,
            lineStyle: {width: 1.5, color: TXT},
            itemStyle: {color: p => p.value >= 100 ? MINT : CORAL},
            markLine: refY(100, 'target 100%')}]}}),
    ],
    errors: [
      f => ({kind: 'Horizontal bars', title: 'Errors by type in the period',
        option: {grid: {left: 12, right: 30, top: 6, bottom: 6, containLabel: true},
          xAxis: {type: 'value', show: false},
          yAxis: {type: 'category', inverse: true, axisTick: {show: false}, axisLine: {show: false},
            axisLabel: {color: TXT, fontSize: 11}, data: f.error_types.map(e => e[0])},
          series: [{type: 'bar', barWidth: 9, label: {show: true, position: 'right', color: TXT, fontSize: 11},
            data: f.error_types.map(([n, v]) => ({value: v,
              itemStyle: glow(v === 0 ? MINT : n.startsWith('Supplier') ? CORAL : AMBER)}))}]}}),
      f => ({kind: 'Scatter', title: 'Days to confirm each supplier error',
        option: {grid: {left: 46, right: 14, top: 22, bottom: 22},
          xAxis: axisCat(f.weeks),
          /* The axis says what the numbers are. Without it a reader
             had to guess whether 120 meant days, errors or reais. */
          yAxis: axisVal({name: 'days', nameTextStyle: {color: AX, fontSize: 10},
                          nameGap: 8}),
          series: [{type: 'scatter', symbolSize: 10,
            data: f.decide.map(([w, d]) => ({value: [w, d], itemStyle: glow(d <= 7 ? MINT : CORAL)})),
            markLine: refY(7, 'target 7 days')}]}}),
      f => ({kind: 'Matrix', title: 'Errors by type and week',
        option: {grid: {left: 74, right: 4, top: 4, bottom: 20}, xAxis: axisCat(f.weeks),
          yAxis: Object.assign(axisCat(['Supplier', 'Automation', 'Revised', 'Superseded']), {inverse: true}),
          visualMap: {show: false, min: 0, max: Math.max(1, ...f.error_matrix.flat()),
                      inRange: {color: ['rgba(255,79,123,0.05)', CORAL]}},
          series: [{type: 'heatmap', data: grid(f.error_matrix), label: {show: true, color: TXT, fontSize: 10,
            formatter: p => p.value[2] || ''}, itemStyle: {borderColor: '#061C28', borderWidth: 2, borderRadius: 3}}]}}),
    ],
    ranking: [
      f => ({kind: 'Horizontal bars', title: 'Top issuers by invoices',
        option: {grid: {left: 12, right: 30, top: 4, bottom: 4, containLabel: true},
          xAxis: {type: 'value', show: false},
          yAxis: {type: 'category', inverse: true, axisTick: {show: false}, axisLine: {show: false},
            axisLabel: {color: TXT, fontSize: 11}, data: f.issuers.slice(0, 6).map(i => i[0])},
          series: [{type: 'bar', barWidth: 8, data: f.issuers.slice(0, 6).map(i => i[1]),
            itemStyle: Object.assign(glow(CYAN), {borderRadius: 3}),
            label: {show: true, position: 'right', color: TXT, fontSize: 11}}]}}),
      f => ({kind: 'Treemap', title: 'Share of invoices by issuer',
        option: {series: [{type: 'treemap', roam: false, nodeClick: false, breadcrumb: {show: false},
          left: 0, right: 0, top: 0, bottom: 0, label: {fontSize: 11, color: '#061C28', fontWeight: 700},
          itemStyle: {borderColor: '#061C28', borderWidth: 2, gapWidth: 2},
          data: f.issuers.map(([n, v], i) => ({name: n, value: v, itemStyle: {color: CATS[i % 6]}}))}]}}),
      f => ({kind: 'Catplot (split violin)', title: 'Lines per invoice, by issuer',
        option: violin(f.catplot)}),
    ],
    trend: [
      f => ({kind: 'Two lines', title: 'This month against the last',
        option: {grid: {left: 30, right: 12, top: 26, bottom: 20},
          legend: {top: 0, right: 0, textStyle: {color: AX, fontSize: 10}, itemWidth: 12, itemHeight: 2},
          xAxis: Object.assign(axisCat(f.this_month.map((_, i) => 'Week ' + (i + 1))), {boundaryGap: false}),
          yAxis: axisVal(),
          series: [{name: 'This month', type: 'line', smooth: true, data: f.this_month, symbolSize: 5,
                    lineStyle: {width: 2, color: CYAN, shadowColor: CYAN, shadowBlur: 8},
                    itemStyle: {color: CYAN}, areaStyle: fade(117, 214, 255)},
                   {name: 'Last month', type: 'line', smooth: true, data: f.last_month, symbol: 'none',
                    lineStyle: {width: 1.2, color: 'rgba(230,240,246,.75)', type: 'dashed'},
                    itemStyle: {color: 'rgba(230,240,246,.75)'}}]}}),
      f => ({kind: 'Waterfall', title: 'Change from week to week',
        option: (() => {
          const base = [], rise = [], fall = [];
          let level = f.counts[0];
          f.counts.slice(1).forEach((v, i) => {
            const d = v - f.counts[i];
            base.push(d >= 0 ? level : level + d); rise.push(d >= 0 ? d : '-'); fall.push(d < 0 ? -d : '-');
            level += d;
          });
          return {grid: {left: 30, right: 6, top: 10, bottom: 20}, xAxis: axisCat(f.weeks.slice(1)), yAxis: axisVal(),
            series: [{type: 'bar', stack: 'w', data: base, itemStyle: {color: 'transparent'}, silent: true},
                     {type: 'bar', stack: 'w', data: rise, barWidth: '50%', itemStyle: glow(MINT)},
                     {type: 'bar', stack: 'w', data: fall, itemStyle: glow(CORAL)}]};
        })()}),
      f => ({kind: 'Stacked area', title: 'Invoice types over time',
        option: {grid: {left: 34, right: 6, top: 24, bottom: 20},
          legend: {top: 0, right: 0, textStyle: {color: AX, fontSize: 10}, itemWidth: 8, itemHeight: 8},
          xAxis: Object.assign(axisCat(f.weeks), {boundaryGap: false}), yAxis: axisVal(),
          series: Object.entries(f.kind_weeks).map(([n, d], i) => ({name: n, type: 'line', stack: 't',
            smooth: true, symbol: 'none', data: d, lineStyle: {width: 1, color: CATS[i]},
            itemStyle: {color: CATS[i]}, areaStyle: {color: CATS[i], opacity: 0.35}}))}}),
    ],
    mix: [
      f => ({kind: 'Donut', title: 'Invoices by type',
        option: {legend: {orient: 'vertical', right: 0, top: 'middle', icon: 'circle', itemWidth: 8, itemHeight: 8,
          textStyle: {color: TXT, fontSize: 11}},
          series: [{type: 'pie', radius: ['40%', '66%'], center: ['34%', '50%'], label: {show: false},
            itemStyle: {borderColor: 'rgba(6,28,40,.9)', borderWidth: 0.5}, color: CATS,
            data: f.kinds.map(([n, v]) => ({name: n, value: v}))}]}}),
      f => ({kind: '100% stacked columns', title: 'Status share per week',
        option: {grid: {left: 38, right: 6, top: 22, bottom: 20},
          legend: {top: 0, right: 0, textStyle: {color: AX, fontSize: 10}, itemWidth: 8, itemHeight: 8},
          xAxis: axisCat(f.weeks), yAxis: axisVal({max: 100, axisLabel: {color: AX, fontSize: 10, formatter: '{value}%'}}),
          series: Object.entries(f.status_share).map(([n, d]) => ({name: n, type: 'bar', stack: 's',
            barWidth: '55%', data: d, itemStyle: {color: STATUS[n]}}))}}),
      f => ({kind: 'Nested treemap', title: 'Type, then status',
        option: {series: [{type: 'treemap', roam: false, nodeClick: false, breadcrumb: {show: false},
          left: 0, right: 0, top: 0, bottom: 0, label: {color: '#061C28', fontSize: 10, fontWeight: 700},
          levels: [{itemStyle: {borderWidth: 0, gapWidth: 4, color: 'transparent', borderColor: 'transparent'},
                    upperLabel: {show: false}},
                   {itemStyle: {borderWidth: 2, gapWidth: 2},
                    upperLabel: {show: true, height: 18, color: '#061C28', fontSize: 11, fontWeight: 700}},
                   {itemStyle: {borderWidth: 0}}],
          data: Object.entries(f.kind_status).map(([k, st], i) => ({name: k,
            itemStyle: {color: CATS[i], borderColor: CATS[i]},
            children: Object.entries(st).map(([s, v]) => ({name: s, value: v,
              itemStyle: {color: s === 'new' ? CATS[i] : STATUS[s]}}))}))}]}}),
    ],
    lookup: [
      (f, x) => ({kind: 'Table', title: 'Invoices that match',
        html: '<table><thead><tr><th style="width:44%">Invoice</th><th style="width:32%">Issuer</th><th>Status</th></tr></thead><tbody>' +
          f.table.map(([id, a, s]) => `<tr><td class="id">${id}</td><td>${a}</td><td><span class="chip ${s}">${s}</span></td></tr>`).join('') +
          '</tbody></table>'}),
      (f, x) => ({kind: 'Timeline', title: 'History of ' + x.number,
        html: '<div class="tl">' + x.steps.map(([w, d, t]) =>
          `<div class="step ${t}">${w}<div class="when">${d}</div></div>`).join('') + '</div>'}),
      (f, x) => ({kind: 'Detail card', title: x.number,
        html: '<div class="card">' + x.card.map(([k, v]) => `<span class="k">${k}</span><span class="v">${
          k === 'Status' ? `<span class="chip ${v}">${v}</span>` : v}</span>`).join('') + '</div>'}),
    ],
    overview: [
      (f, x) => ({kind: 'Attention list', title: 'What needs attention',
        html: x.attention.map(([tone, text]) => {
          const c = {met: MINT, missed: CORAL, warn: AMBER, volume: CYAN}[tone];
          return `<div class="item"><span class="dot" style="background:${c};box-shadow:0 0 6px ${c}"></span><span>${text}</span></div>`;
        }).join('')}),
      f => ({kind: 'Sparkline tiles', title: 'The period at a glance',
        html: '<div class="tiles">' + [['Invoices', f.total, CYAN, f.counts], ['Processed', f.completed[f.completed.length - 1] + '%', MINT, f.completed],
          ['Supplier errors', f.supplier[f.supplier.length - 1], f.supplier[f.supplier.length - 1] ? CORAL : MINT, f.supplier],
          ['Revised', f.revised[f.revised.length - 1], f.revised[f.revised.length - 1] ? AMBER : MINT, f.revised]]
          .map(([n, v, c, s]) => `<div class="tile"><span class="n">${n}</span><span class="v" style="color:${c}">${v}</span>` +
            `<div class="spark" data-colour="${c}" data-values="${s.join(',')}"></div></div>`).join('') + '</div>'}),
      f => ({kind: 'Target matrix', title: 'Targets, week by week',
        option: {grid: {left: 74, right: 4, top: 4, bottom: 20}, xAxis: axisCat(f.weeks),
          yAxis: Object.assign(axisCat(f.matrix_kpis), {inverse: true}),
          visualMap: {show: false, type: 'piecewise', pieces: [{value: 0, color: CORAL}, {value: 1, color: MINT}]},
          series: [{type: 'heatmap', data: grid(f.matrix),
            itemStyle: {borderColor: '#061C28', borderWidth: 3, borderRadius: 4, opacity: 0.85}}]}}),
    ],
  };

  /* The catplot: a split violin per issuer, the latest weeks on top and
     the earlier weeks below, with the mean and ±1 and ±2 standard
     deviations. */
  function violin(c) {
    const MAX = Math.max(6, ...c.now.flat(), ...c.before.flat()) + 1, STEPS = 48;
    const xs = Array.from({length: STEPS + 1}, (_, i) => i * MAX / STEPS);
    const dens = l => { const ys = xs.map(x => l.reduce((s, d) => s + Math.exp(-0.5 * ((x - d) / 0.6) ** 2), 0));
      const t = Math.max(...ys, 1e-9); return ys.map(y => y / t); };
    const stats = l => { if (!l.length) return [0, 0]; const m = l.reduce((s, d) => s + d, 0) / l.length;
      return [m, l.length > 1 ? Math.sqrt(l.reduce((s, d) => s + (d - m) ** 2, 0) / (l.length - 1)) : 0]; };
    const half = (name, colour, lists, side) => ({name: name, type: 'custom', itemStyle: {color: colour},
      data: lists.map((_, r) => [r]),
      renderItem: (p, api) => {
        const l = lists[p.dataIndex]; if (!l.length) return null;
        const row = p.dataIndex, d = dens(l), [m, sd] = stats(l);
        const centre = api.coord([0, row])[1], room = api.size([0, 1])[1] * 0.47;
        const lo = Math.max(0, Math.min(...l) - 0.5), hi = Math.min(MAX, Math.max(...l) + 0.5);
        const pts = xs.map((x, i) => [x, i]).filter(([x]) => x >= lo && x <= hi)
          .map(([x, i]) => [api.coord([x, row])[0], centre - side * d[i] * room]);
        pts.push([api.coord([hi, row])[0], centre], [api.coord([lo, row])[0], centre]);
        const y = centre - side * room * 0.28, at = x => api.coord([Math.max(0, Math.min(MAX, x)), row])[0];
        return {type: 'group', children: [
          {type: 'polygon', shape: {points: pts, smooth: 0.3},
           style: {fill: colour, opacity: 0.45, stroke: colour, lineWidth: 1, shadowColor: colour, shadowBlur: 6}},
          {type: 'line', shape: {x1: at(m - 2 * sd), y1: y, x2: at(m + 2 * sd), y2: y},
           style: {stroke: TXT, lineWidth: 0.5, opacity: 0.35, lineDash: [2, 2]}},
          {type: 'line', shape: {x1: at(m - sd), y1: y, x2: at(m + sd), y2: y},
           style: {stroke: TXT, lineWidth: 0.7, opacity: 0.85}},
          ...[-2, -1, 1, 2].map(k => ({type: 'line',
            shape: {x1: at(m + k * sd), y1: y - 2, x2: at(m + k * sd), y2: y + 2},
            style: {stroke: TXT, lineWidth: 0.5, opacity: Math.abs(k) === 1 ? 0.85 : 0.35}})),
          {type: 'circle', shape: {cx: at(m), cy: y, r: 2.4},
           style: {fill: TXT, shadowColor: TXT, shadowBlur: 4}}]};
      }});
    const shift = c.actors.map((_, i) => stats(c.now[i])[0] - stats(c.before[i])[0]);
    const moved = d => Math.abs(d) < 0.05 ? '{f|avg = 0.0 lines}'
      : d > 0 ? `{a|avg ▲ ${d.toFixed(1)} lines}` : `{a|avg ▼ ${(-d).toFixed(1)} lines}`;
    return {grid: {left: 104, right: 10, top: 32, bottom: 20},
      title: {text: 'avg: lines per invoice, latest four weeks vs the four before', left: 0, top: 0,
              textStyle: {color: AX, fontSize: 10, fontWeight: 400}},
      legend: {top: 14, right: 0, textStyle: {color: AX, fontSize: 10}, itemWidth: 10, itemHeight: 6,
               data: ['Latest 4 weeks', 'Earlier 4 weeks']},
      xAxis: axisVal({min: 0, max: MAX, interval: 1}),
      yAxis: Object.assign(axisCat(c.actors), {inverse: true, axisLabel: {
        formatter: (n, i) => `{n|${n}}\n${moved(shift[i])}`,
        rich: {n: {color: TXT, fontSize: 11, lineHeight: 14}, a: {color: CYAN, fontSize: 10}, f: {color: AX, fontSize: 10}}}}),
      series: [half('Latest 4 weeks', CYAN, c.now, 1), half('Earlier 4 weeks', VIOLET, c.before, -1)]};
  }

  /* The picked plot for one /api/plot-answer reply: its title and kind,
     ready to draw. */
  function spec(answer) {
    return PLOTS[answer.category][answer.plot](answer.figures, answer.extra || {});
  }

  /* Draw a spec into a node. Returns the node that holds the main chart,
     carrying it as ._chart, so a resize can redraw it. */
  function draw(node, s) {
    const host = document.createElement('div');
    host.style.height = '100%';
    node.appendChild(host);
    const root = host.attachShadow({mode: 'open'});
    const style = document.createElement('style');
    style.textContent = CSS;
    root.appendChild(style);
    const box = document.createElement('div');
    box.className = 'tpl';
    box.innerHTML = s.html || '<div class="chart"></div>';
    root.appendChild(box);
    const holder = box.querySelector('.chart');
    if (s.option && holder) {
      holder._chart = echarts.init(holder, null, {renderer: 'canvas'});
      /* ECharts sets the box to relative when it cannot read its style,
         which a box not yet on the page never has. Pinned back here, or
         the chart has no height. */
      holder.style.position = 'absolute';
      holder.style.inset = '0';
      holder._chart.setOption(Object.assign({backgroundColor: 'transparent', tooltip: tip,
                                             animationDuration: 400}, s.option));
    }
    box.querySelectorAll('.spark').forEach(spark => {
      const c = echarts.init(spark, null, {renderer: 'canvas'}), colour = spark.dataset.colour;
      c.setOption({backgroundColor: 'transparent', grid: {left: 0, right: 0, top: 2, bottom: 2},
        xAxis: {type: 'category', show: false, boundaryGap: false}, yAxis: {type: 'value', show: false, scale: true},
        series: [{type: 'line', smooth: true, symbol: 'none', data: spark.dataset.values.split(',').map(Number),
          lineStyle: {width: 1.5, color: colour, shadowColor: colour, shadowBlur: 6}}]});
      /* Drawn before the panel is on the page, at no size: redrawn once
         it has one. */
      setTimeout(() => c.resize(), 60);
    });
    return holder;
  }

  /* How many plots a category holds, so an answer can show the picked
     one and the rest of its family instead of the old hand-built
     panels. */
  function count(category) {
    return (PLOTS[category] || []).length;
  }

  return {spec: spec, draw: draw, count: count};
})();
