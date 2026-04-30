import json

with open('results.json', 'r') as f:
    results = json.load(f)

# Inject obj_labels so JS can read them
OBJ_LABELS = ["Sec CO time (hrs)", "Sec CO cost (Rs)", "Thk CO cost (Rs)",
               "Late (MT\u00b7days)", "Storage (MT\u00b7days)", "Storage (days)"]
results['obj_labels'] = OBJ_LABELS

results_js = json.dumps(results)

html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SteelOpt — NSGA-III Rolling Schedule Optimizer</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=IBM+Plex+Sans:ital,wght@0,300;0,400;0,600;0,700;1,300&display=swap');
:root{
  --bg:#0a0c10;--bg2:#111318;--bg3:#181c24;--border:#252a35;--border2:#2e3545;
  --text:#e2e8f0;--text2:#8892a4;--text3:#5a6478;
  --accent:#00d4ff;--accent2:#0096ff;--green:#00e5a0;--red:#ff4466;
  --yellow:#ffd166;--orange:#ff8c42;--purple:#b06aff;
  --mono:'IBM Plex Mono',monospace;--sans:'IBM Plex Sans',sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0;}
html{font-size:14px;}
body{background:var(--bg);color:var(--text);font-family:var(--sans);min-height:100vh;overflow-x:hidden;}
body::before{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(0,212,255,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(0,212,255,0.03) 1px,transparent 1px);background-size:40px 40px;pointer-events:none;z-index:0;}
header{position:relative;z-index:10;padding:20px 32px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;background:rgba(10,12,16,0.95);backdrop-filter:blur(10px);}
.logo{display:flex;align-items:center;gap:12px;}
.logo-icon{width:36px;height:36px;background:linear-gradient(135deg,var(--accent),var(--accent2));border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:18px;}
.logo-text{font-family:var(--mono);font-size:1.3rem;font-weight:700;letter-spacing:-0.5px;}
.logo-text span{color:var(--accent);}
.header-badge{font-family:var(--mono);font-size:0.7rem;color:var(--text3);background:var(--bg3);border:1px solid var(--border);padding:4px 10px;border-radius:4px;letter-spacing:1px;text-transform:uppercase;}
main{position:relative;z-index:1;max-width:1400px;margin:0 auto;padding:32px 24px;}

/* Nav tabs */
.nav-tabs{display:flex;gap:0;margin-bottom:36px;background:var(--bg2);border:1px solid var(--border);border-radius:10px;overflow:hidden;}
.nav-tab{flex:1;padding:13px 20px;border:none;background:transparent;color:var(--text3);font-family:var(--mono);font-size:0.8rem;font-weight:600;cursor:pointer;transition:all 0.2s;letter-spacing:0.5px;text-transform:uppercase;border-right:1px solid var(--border);}
.nav-tab:last-child{border-right:none;}
.nav-tab:hover{color:var(--text2);background:rgba(255,255,255,0.02);}
.nav-tab.active{background:rgba(0,212,255,0.1);color:var(--accent);border-bottom:2px solid var(--accent);}
.nav-tab.done{color:var(--green);}

.panel{display:none;animation:fadeIn 0.3s ease;}
.panel.active{display:block;}
@keyframes fadeIn{from{opacity:0;transform:translateY(6px);}to{opacity:1;transform:translateY(0);}}

.section-title{font-family:var(--mono);font-size:0.7rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--accent);margin-bottom:16px;display:flex;align-items:center;gap:8px;}
.section-title::after{content:'';flex:1;height:1px;background:linear-gradient(to right,var(--border2),transparent);}

/* Solution cards */
.sol-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px;margin-bottom:28px;}
.sol-card{background:var(--bg2);border:2px solid var(--border);border-radius:12px;padding:18px;cursor:pointer;transition:all 0.2s;position:relative;user-select:none;}
.sol-card:hover{border-color:var(--accent);background:rgba(0,212,255,0.05);transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,212,255,0.1);}
.sol-card.selected{border-color:var(--accent);background:rgba(0,212,255,0.1);box-shadow:0 0 24px rgba(0,212,255,0.15);}
.sol-card.balanced{border-color:var(--yellow);}
.sol-card.balanced:hover{border-color:var(--yellow);background:rgba(255,209,102,0.06);box-shadow:0 8px 24px rgba(255,209,102,0.12);}
.sol-card.balanced.selected{border-color:var(--yellow);background:rgba(255,209,102,0.1);box-shadow:0 0 24px rgba(255,209,102,0.2);}
.sol-label{font-family:var(--mono);font-size:0.72rem;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:14px;color:var(--accent);}
.sol-card.balanced .sol-label{color:var(--yellow);}
.sol-card.selected .sol-label{color:var(--accent);}
.selected-badge{position:absolute;top:10px;right:10px;font-family:var(--mono);font-size:0.6rem;background:var(--accent);color:#000;padding:2px 8px;border-radius:3px;font-weight:700;letter-spacing:0.5px;}
.sol-card.balanced .selected-badge{background:var(--yellow);}
.sol-metric{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.03);}
.sol-metric:last-child{border-bottom:none;}
.sol-metric-name{color:var(--text2);font-size:0.72rem;}
.sol-metric-val{font-family:var(--mono);font-size:0.78rem;font-weight:600;color:var(--text);}
.sol-metric-val.best{color:var(--green);}

/* Chart */
.chart-wrap{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:20px;margin-bottom:20px;}
.chart-title{font-family:var(--mono);font-size:0.72rem;color:var(--text2);margin-bottom:14px;letter-spacing:1px;text-transform:uppercase;}

/* Schedule table */
.sched-wrap{overflow-x:auto;border-radius:8px;border:1px solid var(--border);margin-bottom:24px;max-height:520px;overflow-y:auto;}
.sched-table{width:100%;border-collapse:collapse;font-size:0.78rem;}
.sched-table th{background:var(--bg3);color:var(--text3);font-family:var(--mono);font-size:0.65rem;letter-spacing:1px;text-transform:uppercase;padding:10px 14px;text-align:left;border-bottom:1px solid var(--border2);position:sticky;top:0;z-index:2;white-space:nowrap;}
.sched-table td{padding:9px 14px;border-bottom:1px solid var(--border);font-family:var(--mono);font-size:0.75rem;white-space:nowrap;}
.sched-table tr:hover td{background:rgba(255,255,255,0.02);}
.sched-table tr:last-child td{border-bottom:none;}

.badge{padding:2px 7px;border-radius:3px;font-size:0.68rem;font-weight:600;font-family:var(--mono);display:inline-block;}
.badge-late{background:rgba(255,68,102,0.15);color:var(--red);}
.badge-ok{background:rgba(0,229,160,0.12);color:var(--green);}
.badge-sec{background:rgba(255,209,102,0.15);color:var(--yellow);}
.badge-thk{background:rgba(176,106,255,0.15);color:var(--purple);}
.badge-none{background:rgba(90,100,120,0.15);color:var(--text3);}

.tabs{display:flex;gap:2px;margin-bottom:20px;background:var(--bg2);border-radius:8px;padding:4px;border:1px solid var(--border);width:fit-content;}
.tab{padding:7px 18px;border-radius:6px;cursor:pointer;font-family:var(--mono);font-size:0.75rem;font-weight:600;color:var(--text3);transition:all 0.2s;border:none;background:none;}
.tab.active{background:var(--bg3);color:var(--accent);border:1px solid var(--border2);}
.tab:hover:not(.active){color:var(--text2);}

.dl-btn{display:inline-flex;align-items:center;gap:8px;background:var(--bg3);border:1px solid var(--border2);color:var(--text);padding:8px 16px;border-radius:6px;font-family:var(--mono);font-size:0.75rem;cursor:pointer;transition:all 0.2s;margin-right:8px;}
.dl-btn:hover{border-color:var(--accent);color:var(--accent);}

.divider{height:1px;background:linear-gradient(to right,transparent,var(--border2),transparent);margin:28px 0;}

/* Comparison table */
.compare-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:24px;}
.compare-card{background:var(--bg2);border:1px solid var(--border);border-radius:10px;overflow:hidden;}
.compare-card-header{padding:14px 18px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border);}
.compare-card-title{font-family:var(--mono);font-size:0.8rem;font-weight:700;letter-spacing:1px;}
.compare-card-title.actual{color:var(--orange);}
.compare-card-title.nsga{color:var(--accent);}
.metrics-table{width:100%;border-collapse:collapse;font-size:0.8rem;}
.metrics-table th{background:var(--bg3);color:var(--text3);font-family:var(--mono);font-size:0.65rem;padding:10px 16px;text-align:left;letter-spacing:1px;border-bottom:1px solid var(--border2);}
.metrics-table td{padding:10px 16px;border-bottom:1px solid var(--border);font-family:var(--mono);font-size:0.78rem;}
.metrics-table .metric-name{font-size:0.8rem;color:var(--text);font-family:var(--sans);}
.better-val{color:var(--green);font-weight:700;}
.worse-val{color:var(--red);}
.kpi-delta{font-family:var(--mono);font-size:0.72rem;padding:2px 6px;border-radius:3px;display:inline-block;}
.kpi-delta.better{background:rgba(0,229,160,0.12);color:var(--green);}
.kpi-delta.worse{background:rgba(255,68,102,0.12);color:var(--red);}

.upload-zone{border:1.5px dashed var(--border2);border-radius:10px;padding:24px 20px;text-align:center;cursor:pointer;transition:all 0.25s;background:var(--bg2);position:relative;overflow:hidden;}
.upload-zone:hover{border-color:var(--accent);background:rgba(0,212,255,0.04);}
.upload-zone.ready{border-color:var(--green);border-style:solid;background:rgba(0,229,160,0.04);}
.upload-zone input{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%;}
.upload-status{font-family:var(--mono);font-size:0.72rem;margin-top:8px;padding:3px 8px;border-radius:4px;display:inline-block;}
.upload-status.ok{background:rgba(0,229,160,0.15);color:var(--green);}
.upload-status.opt{background:rgba(255,209,102,0.12);color:var(--yellow);}

/* Convergence chart */
.conv-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:24px;}

/* Radar chart */
.radar-wrap{display:flex;gap:20px;align-items:flex-start;margin-bottom:24px;flex-wrap:wrap;}
.radar-card{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:20px;flex:1;min-width:300px;}

::-webkit-scrollbar{width:6px;height:6px;}
::-webkit-scrollbar-track{background:var(--bg2);}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:3px;}
@media(max-width:900px){.compare-grid{grid-template-columns:1fr;}.conv-grid{grid-template-columns:1fr;}.radar-wrap{flex-direction:column;}}
</style>
</head>
<body>
<header>
  <div class="logo">
    <div class="logo-icon">⚙</div>
    <div class="logo-text">Steel<span>Opt</span></div>
  </div>
  <div style="display:flex;gap:12px;align-items:center;">
    <span style="font-size:0.75rem;color:var(--text3);font-family:var(--mono);">NSGA-III Multi-Objective Rolling Scheduler</span>
    <div class="header-badge">Results Dashboard</div>
  </div>
</header>
<main>
  <div class="nav-tabs">
    <button class="nav-tab active" id="tab1" onclick="goTab(1)">① Solution Space</button>
    <button class="nav-tab" id="tab2" onclick="goTab(2)">② Rolling Plan</button>
    <button class="nav-tab" id="tab3" onclick="goTab(3)">③ Convergence</button>
    <button class="nav-tab" id="tab4" onclick="goTab(4)">④ Actual vs NSGA-III</button>
  </div>

  <!-- TAB 1: Solution Space -->
  <div class="panel active" id="panel1">
    <div id="solution-space-content"></div>
  </div>

  <!-- TAB 2: Rolling Plan -->
  <div class="panel" id="panel2">
    <div id="plan-content">
      <div style="text-align:center;padding:60px;color:var(--text3);">
        <div style="font-size:3rem;margin-bottom:12px;">📋</div>
        <div>Select a solution in the Solution Space tab first</div>
      </div>
    </div>
  </div>

  <!-- TAB 3: Convergence -->
  <div class="panel" id="panel3">
    <div id="conv-content"></div>
  </div>

  <!-- TAB 4: Actual vs NSGA-III -->
  <div class="panel" id="panel4">
    <div id="compare-content">
      <div style="background:var(--bg2);border:1px solid var(--border2);border-radius:10px;padding:28px;margin-bottom:24px;">
        <div style="font-family:var(--mono);font-size:0.72rem;color:var(--yellow);margin-bottom:12px;">📂 UPLOAD ACTUAL ROLLING PLANS</div>
        <div style="font-size:0.82rem;color:var(--text2);margin-bottom:20px;">Upload your actual SM and LM rolling plan Excel files to compare against the NSGA-III optimized solutions.</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;max-width:600px;">
          <div class="upload-zone" id="zone-actual-sm">
            <input type="file" accept=".xlsx,.xls" onchange="loadActualPlan(this,'SM')">
            <div style="font-size:1.8rem;margin-bottom:8px;">⚙</div>
            <div style="font-weight:700;font-size:0.85rem;margin-bottom:4px;">SM Actual Plan</div>
            <div class="upload-status opt" id="status-actual-sm">Optional</div>
          </div>
          <div class="upload-zone" id="zone-actual-lm">
            <input type="file" accept=".xlsx,.xls" onchange="loadActualPlan(this,'LM')">
            <div style="font-size:1.8rem;margin-bottom:8px;">⚙</div>
            <div style="font-weight:700;font-size:0.85rem;margin-bottom:4px;">LM Actual Plan</div>
            <div class="upload-status opt" id="status-actual-lm">Optional</div>
          </div>
        </div>
      </div>
      <div id="compare-results"></div>
    </div>
  </div>
</main>

<script>
const EMBEDDED = ''' + results_js + ''';
const STATE = { results: EMBEDDED, actualSM: null, actualLM: null, selectedSM: null, selectedLM: null };
const OBJ_LABELS = EMBEDDED.obj_labels;
const SHIFT_HRS = 12.0;
const SEC_COST = 24100.0;
const OBJ_COLORS = ['#00d4ff','#00e5a0','#ffd166','#ff4466','#b06aff','#ff8c42'];

// ── Navigation ────────────────────────────────────────────

function goTab(n){
  [1,2,3,4].forEach(i=>{
    document.getElementById('tab'+i).classList.remove('active');
    document.getElementById('panel'+i).classList.remove('active');
  });
  document.getElementById('tab'+n).classList.add('active');
  document.getElementById('panel'+n).classList.add('active');
  if(n===1 && !document.getElementById('solution-space-content').children.length) renderSolutionSpace();
  if(n===3) renderConvergence();
  if(n===4) renderComparison();
}

// ── Render solution space (tab 1) ────────────────────────

function renderSolutionSpace(){
  const r = STATE.results;
  const container = document.getElementById('solution-space-content');

  container.innerHTML = `
    <div class="section-title">📊 Objective Space — All Solutions</div>
    <div class="chart-wrap" style="margin-bottom:24px;">
      <div style="display:flex;gap:8px;align-items:center;margin-bottom:14px;flex-wrap:wrap;">
        <button onclick="setSpaceMill('sm')" id="space-btn-sm" class="mill-btn active-mill">SM Mill</button>
        <button onclick="setSpaceMill('lm')" id="space-btn-lm" class="mill-btn">LM Mill</button>
        <span style="font-size:11px;color:#5a6478;margin-left:8px;">Each bar group = one solution · Click a solution to select it</span>
      </div>
      <canvas id="space-canvas" height="320" style="display:block;width:100%;cursor:pointer;border-radius:6px;"></canvas>
      <div id="space-legend" style="display:flex;gap:12px;flex-wrap:wrap;margin-top:12px;"></div>
    </div>
    <div class="divider"></div>
    <div id="sm-section">
      <div class="section-title">⚙ Small Mill (SM) — Click to Select a Solution</div>
      <div class="sol-grid" id="sm-cards"></div>
    </div>
    <div class="divider"></div>
    <div id="lm-section">
      <div class="section-title">⚙ Large Mill (LM) — Click to Select a Solution</div>
      <div class="sol-grid" id="lm-cards"></div>
    </div>
  `;

  // Inject mill-btn styles inline
  const style = document.createElement('style');
  style.textContent = `.mill-btn{font-size:12px;padding:5px 16px;border-radius:20px;cursor:pointer;font-family:var(--mono);font-weight:600;transition:all 0.2s;border:1.5px solid var(--border2);background:transparent;color:var(--text3);}
  .mill-btn:hover{border-color:var(--accent);color:var(--accent);}
  .mill-btn.active-mill{background:var(--accent);color:#000;border-color:var(--accent);}`;
  document.head.appendChild(style);

  renderCards('sm');
  renderCards('lm');
  spaceMill = 'sm';
  setTimeout(()=>renderSpaceChart(), 60);
}

let spaceMill = 'sm';

function setSpaceMill(mill){
  spaceMill = mill;
  document.getElementById('space-btn-sm').className = 'mill-btn' + (mill==='sm'?' active-mill':'');
  document.getElementById('space-btn-lm').className = 'mill-btn' + (mill==='lm'?' active-mill':'');
  renderSpaceChart();
}

function renderSpaceChart(){
  const r = STATE.results;
  const solutions = r[spaceMill].solutions;
  const cv = document.getElementById('space-canvas');
  if(!cv) return;

  const W = cv.offsetWidth || 900, H = 320;
  cv.width = W; cv.height = H;
  const ctx = cv.getContext('2d');
  ctx.clearRect(0,0,W,H);

  const ML=60, MR=20, MT=50, MB=80;
  const IW = W-ML-MR, IH = H-MT-MB;
  const nSols = solutions.length;
  const nObj = OBJ_LABELS.length;
  const barW = Math.max(4, Math.floor(IW/(nSols*nObj + nSols)));
  const groupW = barW*nObj + barW;

  // Per-objective min for "best" highlight
  const objMins = OBJ_LABELS.map(lbl => Math.min(...solutions.map(s=>s.objectives[lbl])));
  const objMaxs = OBJ_LABELS.map(lbl => Math.max(...solutions.map(s=>s.objectives[lbl])));

  // Draw axes
  ctx.strokeStyle = '#252a35'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(ML,MT); ctx.lineTo(ML,MT+IH); ctx.lineTo(ML+IW,MT+IH); ctx.stroke();

  // Y-axis label
  ctx.save(); ctx.fillStyle='#5a6478'; ctx.font='10px IBM Plex Mono,monospace';
  ctx.textAlign='center'; ctx.translate(15,MT+IH/2); ctx.rotate(-Math.PI/2);
  ctx.fillText('Normalised value (0=best, 1=worst)',0,0); ctx.restore();

  solutions.forEach((sol, si)=>{
    const gx = ML + si*groupW + barW*0.5;
    OBJ_LABELS.forEach((lbl, oi)=>{
      const val = sol.objectives[lbl];
      const norm = objMaxs[oi]>objMins[oi] ? (val-objMins[oi])/(objMaxs[oi]-objMins[oi]) : 0;
      const barH = Math.max(2, norm*IH);
      const x = gx + oi*barW;
      const y = MT + IH - barH;
      const isBest = val === objMins[oi];
      const isSelected = (spaceMill==='sm' && STATE.selectedSM===si) || (spaceMill==='lm' && STATE.selectedLM===si);

      ctx.fillStyle = OBJ_COLORS[oi] + (isBest?'ff': isSelected?'cc':'55');
      ctx.fillRect(x+1, y, barW-2, barH);

      if(isBest){
        ctx.fillStyle = OBJ_COLORS[oi];
        ctx.font='bold 8px IBM Plex Mono,monospace';
        ctx.textAlign='center';
        ctx.fillText('★', x+barW/2, y-3);
      }
    });

    // Solution label
    const isSelected = (spaceMill==='sm' && STATE.selectedSM===si) || (spaceMill==='lm' && STATE.selectedLM===si);
    const isBalanced = sol.label.includes('TOPSIS') || sol.label.includes('Balanced');
    ctx.fillStyle = isSelected ? (isBalanced?'#ffd166':'#00d4ff') : '#5a6478';
    ctx.font = (isSelected?'bold ':'')+'9px IBM Plex Mono,monospace';
    ctx.textAlign='center';
    const shortLabel = sol.label.replace('Best ','').replace(' (TOPSIS)','').replace('(MT·days)','MT·d').replace('(days)','days').replace(' (Rs)','');
    const labelX = gx + (nObj*barW)/2;
    // Wrap at 12 chars
    const words = shortLabel.split(' ');
    let line='', lines=[];
    words.forEach(w=>{ if((line+w).length>10&&line){lines.push(line.trim());line=w+' ';}else{line+=w+' ';} });
    if(line.trim()) lines.push(line.trim());
    lines.forEach((l,li)=>ctx.fillText(l, labelX, MT+IH+16+li*12));
  });

  // Legend
  const legend = document.getElementById('space-legend');
  if(legend){
    legend.innerHTML = OBJ_LABELS.map((lbl,i)=>
      `<span style="display:flex;align-items:center;gap:4px;font-family:var(--mono);font-size:10px;color:${OBJ_COLORS[i]};">
        <span style="width:10px;height:10px;border-radius:2px;background:${OBJ_COLORS[i]};display:inline-block;"></span>${lbl}
      </span>`
    ).join('');
  }

  // Click handler
  cv.onclick = e=>{
    const rect = cv.getBoundingClientRect();
    const mx = (e.clientX-rect.left)*(W/rect.width);
    solutions.forEach((sol,si)=>{
      const gx = ML + si*groupW + barW*0.5;
      const lx = gx;
      const rx = gx + nObj*barW;
      if(mx>=lx && mx<=rx+barW) selectSolution(spaceMill, si);
    });
  };
}

// ── Solution cards ────────────────────────────────────────

function renderCards(mill){
  const solutions = STATE.results[mill].solutions;
  const container = document.getElementById(mill+'-cards');
  if(!container) return;

  const bestVals = {};
  OBJ_LABELS.forEach(lbl=>{ bestVals[lbl] = Math.min(...solutions.map(s=>s.objectives[lbl])); });

  const metrics = OBJ_LABELS.map((lbl,i)=>({name:lbl, key:lbl, color:OBJ_COLORS[i]}));

  container.innerHTML = solutions.map((sol,idx)=>{
    const isBalanced = sol.label.includes('TOPSIS') || sol.label.includes('Balanced');
    const isSelected = (mill==='sm' && STATE.selectedSM===idx) || (mill==='lm' && STATE.selectedLM===idx);
    const mHtml = metrics.map(m=>{
      const val = sol.objectives[m.key];
      const isBest = val===bestVals[m.key];
      return `<div class="sol-metric">
        <span class="sol-metric-name" style="color:${m.color}80;">${m.name}</span>
        <span class="sol-metric-val ${isBest?'best':''}">${fmtNum(val)}</span>
      </div>`;
    }).join('');
    return `<div class="sol-card ${isBalanced?'balanced':''} ${isSelected?'selected':''}" id="card-${mill}-${idx}" onclick="selectSolution('${mill}',${idx})">
      ${isSelected?`<div class="selected-badge">✓ SELECTED</div>`:''}
      <div class="sol-label">${sol.label}</div>
      ${mHtml}
    </div>`;
  }).join('');
}

function selectSolution(mill, idx){
  if(mill==='sm') STATE.selectedSM=idx; else STATE.selectedLM=idx;
  renderCards('sm');
  renderCards('lm');
  renderSpaceChart();
  renderPlan();
  document.getElementById('tab2').classList.add('done');
}

// ── Rolling plan (tab 2) ─────────────────────────────────

function renderPlan(){
  const container = document.getElementById('plan-content');
  if(STATE.selectedSM===null && STATE.selectedLM===null){
    container.innerHTML=`<div style="text-align:center;padding:60px;color:var(--text3);"><div style="font-size:3rem;margin-bottom:12px;">📋</div><div>Select a solution in the Solution Space tab first</div></div>`;
    return;
  }

  const smSol = STATE.selectedSM!==null ? STATE.results.sm.solutions[STATE.selectedSM] : null;
  const lmSol = STATE.selectedLM!==null ? STATE.results.lm.solutions[STATE.selectedLM] : null;

  let html = `<div style="margin-bottom:16px;display:flex;gap:8px;flex-wrap:wrap;">
    <button class="dl-btn" onclick="downloadExcel()">⬇ Download as Excel</button>`;
  if(STATE.actualSM||STATE.actualLM){
    html += `<button class="dl-btn" onclick="goTab(4)" style="border-color:var(--yellow);color:var(--yellow);">📊 Compare with Actual →</button>`;
  }
  html += `</div>`;

  if(smSol && lmSol){
    html += `<div class="tabs">
      <button class="tab active" id="ptab-sm" onclick="showPlanMill('sm')">⚙ Small Mill (SM) — ${smSol.label}</button>
      <button class="tab" id="ptab-lm" onclick="showPlanMill('lm')">⚙ Large Mill (LM) — ${lmSol.label}</button>
    </div>`;
  }

  if(smSol){
    html += `<div id="plan-sm" ${lmSol?'':''}>${buildScheduleTable(smSol.schedule,'SM')}</div>`;
  }
  if(lmSol){
    html += `<div id="plan-lm" style="${smSol?'display:none;':''}"> ${buildScheduleTable(lmSol.schedule,'LM')}</div>`;
  }

  container.innerHTML = html;
}

function showPlanMill(mill){
  const sm = document.getElementById('plan-sm');
  const lm = document.getElementById('plan-lm');
  if(sm) sm.style.display = mill==='sm'?'block':'none';
  if(lm) lm.style.display = mill==='lm'?'block':'none';
  document.querySelectorAll('#plan-content .tab').forEach((t,i)=>{
    t.classList.toggle('active',(i===0&&mill==='sm')||(i===1&&mill==='lm'));
  });
}

function buildScheduleTable(schedule, mill){
  const color = mill==='SM'?'var(--accent)':'#ff6b6b';
  let html = `<div class="sched-wrap"><table class="sched-table"><thead><tr>
    <th>#</th><th>Section</th><th>Thk</th><th>Qty (MT)</th><th>Due Day</th>
    <th>Start Day</th><th>Finish Day</th><th>CO Type</th><th>CO Hrs</th>
    <th>CO Cost (Rs)</th><th>Status</th><th>Late MT</th><th>Early Days</th><th>Storage MT</th>
  </tr></thead><tbody>`;
  schedule.forEach(r=>{
    const lateClass = r.late_days>0?'badge-late':'badge-ok';
    const lateText  = r.late_days>0?`${r.late_days.toFixed(1)}d LATE`:'On Time';
    const coClass   = r.co_type==='Section'?'badge-sec':r.co_type==='Thickness'?'badge-thk':'badge-none';
    html += `<tr>
      <td>${r.pos}</td>
      <td style="color:${color};font-weight:600">${r.section}</td>
      <td>${r.thickness}</td>
      <td>${r.qty.toFixed(2)}</td>
      <td>${r.due_day}</td>
      <td>${r.start_day.toFixed(2)}</td>
      <td>${r.finish_day.toFixed(2)}</td>
      <td><span class="badge ${coClass}">${r.co_type}</span></td>
      <td>${r.co_hrs||'—'}</td>
      <td>${r.co_cost>0?'₹'+fmtNum(r.co_cost):'—'}</td>
      <td><span class="badge ${lateClass}">${lateText}</span></td>
      <td>${r.late_mt>0?r.late_mt.toFixed(1):'—'}</td>
      <td>${r.early_days>0?r.early_days.toFixed(1):'—'}</td>
      <td>${r.storage_mt>0?r.storage_mt.toFixed(1):'—'}</td>
    </tr>`;
  });
  html += `</tbody></table></div>`;
  return html;
}

// ── Convergence (tab 3) ─────────────────────────────────

function renderConvergence(){
  const r = STATE.results;
  const container = document.getElementById('conv-content');

  let html = `<div class="section-title">📈 Optimisation Convergence</div><div class="conv-grid">`;

  ['sm','lm'].forEach(mill=>{
    const data = r[mill] ? r[mill].convergence : null;
    if(!data){html+=`<div></div>`;return;}
    html += `<div class="chart-wrap">
      <div class="chart-title">${mill.toUpperCase()} Mill — Hypervolume over Generations</div>
      <canvas id="conv-${mill}" height="220" style="width:100%;display:block;"></canvas>
      <div style="display:flex;gap:16px;margin-top:12px;font-family:var(--mono);font-size:0.72rem;color:var(--text3);">
        <span>Generations: <strong style="color:var(--text)">${data.generations[data.generations.length-1]}</strong></span>
        <span>Initial HV: <strong style="color:var(--text)">${data.hypervolume[0].toFixed(4)}</strong></span>
        <span>Final HV: <strong style="color:var(--accent)">${data.hypervolume[data.hypervolume.length-1].toFixed(4)}</strong></span>
        <span>Gain: <strong style="color:var(--green)">${(((data.hypervolume[data.hypervolume.length-1]-data.hypervolume[0])/Math.max(data.hypervolume[0],1e-9))*100).toFixed(1)}%</strong></span>
      </div>
    </div>`;
  });
  html += `</div>`;

  // Diversity charts
  html += `<div class="section-title">🔀 Population Diversity</div><div class="conv-grid">`;
  ['sm','lm'].forEach(mill=>{
    const data = r[mill] ? r[mill].convergence : null;
    if(!data){html+=`<div></div>`;return;}
    html += `<div class="chart-wrap">
      <div class="chart-title">${mill.toUpperCase()} Mill — Diversity over Generations</div>
      <canvas id="div-${mill}" height="180" style="width:100%;display:block;"></canvas>
    </div>`;
  });
  html += `</div>`;

  container.innerHTML = html;

  // Draw after DOM update
  setTimeout(()=>{
    ['sm','lm'].forEach(mill=>{
      const data = r[mill] ? r[mill].convergence : null;
      if(data){
        drawLineChart('conv-'+mill, data.generations, data.hypervolume, '#00d4ff', 'Hypervolume');
        drawLineChart('div-'+mill, data.generations, data.diversity, '#00e5a0', 'Diversity');
      }
    });
  }, 60);
}

function drawLineChart(canvasId, xData, yData, color, label){
  const cv = document.getElementById(canvasId); if(!cv) return;
  const W = cv.offsetWidth||600, H = parseInt(cv.getAttribute('height'))||220;
  cv.width=W; cv.height=H;
  const ctx = cv.getContext('2d');
  ctx.clearRect(0,0,W,H);
  const ML=50,MR=15,MT=15,MB=35;
  const IW=W-ML-MR, IH=H-MT-MB;

  const mn=Math.min(...yData), mx=Math.max(...yData), rng=mx-mn||1;
  const xmn=Math.min(...xData), xmx=Math.max(...xData), xrng=xmx-xmn||1;

  // Grid lines
  for(let i=0;i<=4;i++){
    const y=MT+i*(IH/4);
    ctx.beginPath(); ctx.moveTo(ML,y); ctx.lineTo(ML+IW,y);
    ctx.strokeStyle='#252a35'; ctx.lineWidth=1; ctx.stroke();
    const val=(mx-(i/4)*rng);
    ctx.fillStyle='#5a6478'; ctx.font='9px IBM Plex Mono,monospace';
    ctx.textAlign='right'; ctx.fillText(val.toFixed(3),ML-5,y+3);
  }
  // X axis ticks
  for(let i=0;i<=4;i++){
    const x=ML+i*(IW/4);
    const val=Math.round(xmn+(i/4)*xrng);
    ctx.fillStyle='#5a6478'; ctx.font='9px IBM Plex Mono,monospace';
    ctx.textAlign='center'; ctx.fillText(val,x,H-8);
  }

  // Area fill
  ctx.beginPath();
  xData.forEach((x,i)=>{
    const cx=ML+(x-xmn)/xrng*IW;
    const cy=MT+IH-((yData[i]-mn)/rng)*IH;
    i===0?ctx.moveTo(cx,cy):ctx.lineTo(cx,cy);
  });
  ctx.lineTo(ML+(xData[xData.length-1]-xmn)/xrng*IW, MT+IH);
  ctx.lineTo(ML,MT+IH); ctx.closePath();
  const grad=ctx.createLinearGradient(0,MT,0,MT+IH);
  grad.addColorStop(0,color+'44'); grad.addColorStop(1,color+'05');
  ctx.fillStyle=grad; ctx.fill();

  // Line
  ctx.beginPath();
  xData.forEach((x,i)=>{
    const cx=ML+(x-xmn)/xrng*IW;
    const cy=MT+IH-((yData[i]-mn)/rng)*IH;
    i===0?ctx.moveTo(cx,cy):ctx.lineTo(cx,cy);
  });
  ctx.strokeStyle=color; ctx.lineWidth=2; ctx.lineJoin='round'; ctx.stroke();
}

// ── Actual vs NSGA-III (tab 4) ───────────────────────────

function parseSection(s){
  const parts=String(s).trim().split('X');
  if(parts.length>=3){const sec=parts[0]+'X'+parts[1];const thk=parseInt(parts[2])||6;return{sec,thk};}
  return{sec:s,thk:6};
}

function parseDueDay(bucket){
  if(!bucket) return 31;
  if(bucket instanceof Date){
    if(bucket.getFullYear()===2026&&bucket.getMonth()===0) return bucket.getDate();
    if(bucket<new Date(2026,0,1)) return 1;
    return 31;
  }
  return 31;
}

function loadActualPlan(input, mill){
  const file=input.files[0]; if(!file) return;
  const reader=new FileReader();
  reader.onload=e=>{
    const wb=XLSX.read(e.target.result,{type:'array',cellDates:true});
    // Find the right sheet - prefer 'JAN', else first sheet
    const sheetName=wb.SheetNames.find(s=>s.toUpperCase()==='JAN')||wb.SheetNames[0];
    // Row 0 = actual headers, Row 1 = blank (skip), Row 2+ = data
    const raw=XLSX.utils.sheet_to_json(wb.Sheets[sheetName],{header:1,cellDates:true,defval:null});
    const rows=[];
    for(let i=2;i<raw.length;i++){
      const r=raw[i]; if(!r||(!r[0]&&!r[11])) continue;
      const secRaw=String(r[11]||'').trim();
      const qty=parseFloat(r[12])||0;
      if(!secRaw||qty<=0) continue;
      const {sec,thk}=parseSection(secRaw);
      const startDate=r[0] instanceof Date?r[0]:null;
      const bucket=r[6] instanceof Date?r[6]:null;
      const dueDay=parseDueDay(bucket);
      rows.push({sec,thk,qty,dueDay,startDate,secRaw});
    }
    // Sort by start_date to preserve rolling order
    rows.sort((a,b)=>{
      if(!a.startDate&&!b.startDate) return 0;
      if(!a.startDate) return 1;
      if(!b.startDate) return -1;
      return a.startDate-b.startDate;
    });

    // Build campaigns: group by (sec, thk, dueDay) preserving order
    const seen=[], map={};
    rows.forEach(r=>{
      const key=`${r.sec}__${r.thk}__${r.dueDay}`;
      if(!map[key]){map[key]={sec:r.sec,thk:r.thk,qty:0,dueDay:r.dueDay,order:seen.length};seen.push(key);}
      map[key].qty+=r.qty;
    });
    const campaigns=seen.map(k=>map[k]);

    if(mill==='SM') STATE.actualSM=campaigns; else STATE.actualLM=campaigns;
    const el=document.getElementById('status-actual-'+mill.toLowerCase());
    if(el){el.textContent=`✓ ${campaigns.length} campaigns loaded`;el.className='upload-status ok';}
    document.getElementById('zone-actual-'+mill.toLowerCase()).classList.add('ready');
    renderComparison();
  };
  reader.readAsArrayBuffer(file);
}

function evaluateActualCampaigns(campaigns, cap, mill){
  // Mirrors Python evaluator.py logic exactly
  let secCoCost=0, thkCoCost=0, secCoTime=0, lateMtDays=0, storageMtDays=0, storageDays=0;
  let clock=0, prevSec=null, prevThk=null;
  const SHIFT=12.0, SEC_COST=24100.0, THK_CO_HRS=0.5, CONTRIB_PER_HR=62866.0;

  campaigns.forEach(c=>{
    const {sec,thk,qty,dueDay:due}=c;
    if(prevSec!==null){
      if(prevSec!==sec){
        // Section changeover: done post-shift, no hours lost inside shift
        const shiftPos=clock%SHIFT;
        const remaining=SHIFT-shiftPos;
        // Assume average 7 hrs CO (no matrix in browser); done post-shift → 0 hrs lost
        const coHrs=7.0;
        let hrsLost=0;
        if(coHrs<=remaining){ hrsLost=coHrs; clock+=coHrs; }
        else{ hrsLost=0; clock=(Math.floor(clock/SHIFT)+1)*SHIFT; }
        secCoCost+=SEC_COST+(hrsLost*CONTRIB_PER_HR);
        secCoTime+=hrsLost;
      } else if(prevThk!==thk){
        // Thickness changeover: 0.5 hrs in-place
        clock+=THK_CO_HRS;
        // No CO cost matrix in browser — mark as 0 (CO matrix not uploaded)
        thkCoCost+=0;
      }
    }
    // Rolling time
    const rollHrs=(qty/cap)*SHIFT;
    const shiftPos2=clock%SHIFT;
    const remaining2=SHIFT-shiftPos2;
    if(rollHrs<=remaining2){ clock+=rollHrs; }
    else{ const carried=rollHrs-remaining2; clock=(Math.floor(clock/SHIFT)+1)*SHIFT+carried; }

    const finDay=clock/SHIFT;
    if(finDay>due) lateMtDays+=qty*(finDay-due);
    if(finDay<due){ storageMtDays+=qty*(due-finDay); storageDays+=(due-finDay); }
    prevSec=sec; prevThk=thk;
  });

  return {
    'Sec CO time (hrs)': secCoTime,
    'Sec CO cost (Rs)':  secCoCost,
    'Thk CO cost (Rs)':  thkCoCost,
    'Late (MT\u00b7days)':      lateMtDays,
    'Storage (MT\u00b7days)':   storageMtDays,
    'Storage (days)':    storageDays,
  };
}

function renderComparison(){
  const container = document.getElementById('compare-results');
  if(!STATE.actualSM && !STATE.actualLM){
    container.innerHTML=''; return;
  }
  if(STATE.selectedSM===null && STATE.selectedLM===null){
    container.innerHTML=`<div style="padding:24px;background:var(--bg2);border:1px solid var(--border2);border-radius:8px;color:var(--yellow);font-family:var(--mono);font-size:0.8rem;">⚠ Select a solution in the Solution Space tab first, then come back here.</div>`;
    return;
  }

  const mills=[];
  if(STATE.actualSM&&STATE.selectedSM!==null) mills.push({label:'Small Mill (SM)',mill:'SM',campaigns:STATE.actualSM,cap:150,solIdx:STATE.selectedSM});
  if(STATE.actualLM&&STATE.selectedLM!==null) mills.push({label:'Large Mill (LM)',mill:'LM',campaigns:STATE.actualLM,cap:250,solIdx:STATE.selectedLM});
  if(!mills.length){
    container.innerHTML=`<div style="padding:24px;background:var(--bg2);border:1px solid var(--border2);border-radius:8px;color:var(--yellow);font-family:var(--mono);font-size:0.8rem;">⚠ Upload actual plans AND select a solution to see comparison.</div>`;
    return;
  }

  let html=`<div class="section-title">⚖ Actual Plan vs NSGA-III Optimization</div>`;

  mills.forEach(m=>{
    const sol=STATE.results[m.mill.toLowerCase()].solutions[m.solIdx];
    const nsgaObjs=OBJ_LABELS.map(lbl=>sol.objectives[lbl]);
    const actualObjs=evaluateActualCampaigns(m.campaigns, m.cap, m.mill);

    // KPI summary row
    html+=`<div style="background:var(--bg2);border:1px solid var(--border);border-radius:12px;overflow:hidden;margin-bottom:28px;">
      <div style="padding:16px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;">
        <div style="font-family:var(--mono);font-weight:700;font-size:0.9rem;color:var(--accent);">${m.label}</div>
        <div style="font-family:var(--mono);font-size:0.72rem;color:var(--text3);">${m.campaigns.length} actual campaigns → NSGA-III: ${sol.label}</div>
      </div>
      <div style="overflow-x:auto;"><table class="metrics-table">
        <thead><tr>
          <th>Objective</th>
          <th style="color:var(--orange)">📋 Actual Plan</th>
          <th style="color:var(--accent)">⚡ NSGA-III</th>
          <th>Δ Improvement</th>
          <th>Better?</th>
        </tr></thead><tbody>`;

    OBJ_LABELS.forEach(lbl=>{
      const aVal=actualObjs[lbl]||0;
      const nVal=nsgaObjs[OBJ_LABELS.indexOf(lbl)];
      const better=nVal<=aVal;
      const delta=aVal>0?((nVal-aVal)/aVal*100):0;
      const sign=delta>=0?'+':'';
      const note=lbl.includes('Thk CO')?' *':'';
      html+=`<tr>
        <td class="metric-name">${lbl}${note}</td>
        <td style="color:var(--orange);font-family:var(--mono)">${fmtNum(aVal)}</td>
        <td style="${better?'color:var(--green)':'color:var(--red)'};font-family:var(--mono);font-weight:700">${fmtNum(nVal)}</td>
        <td><span class="kpi-delta ${better?'better':'worse'}">${sign}${delta.toFixed(1)}%</span></td>
        <td style="font-size:1rem">${better?'✅':'❌'}</td>
      </tr>`;
    });

    html+=`</tbody></table></div>
      <div style="padding:12px 20px;font-size:0.72rem;color:var(--text3);border-top:1px solid var(--border);">
        * Thk CO cost requires the changeover matrix — showing 0 for actual (no matrix in browser). Sec CO cost uses average 7 hrs for section changeovers.
      </div>
    </div>`;

    // Actual plan sequence table
    html+=`<div class="section-title" style="margin-top:8px;">📋 ${m.label} — Actual Campaign Sequence (${m.campaigns.length} campaigns)</div>
    <div class="sched-wrap" style="margin-bottom:28px;"><table class="sched-table">
      <thead><tr><th>#</th><th>Section</th><th>Thk</th><th>Qty (MT)</th><th>Due Day</th></tr></thead><tbody>`;
    m.campaigns.forEach((c,i)=>{
      html+=`<tr><td>${i+1}</td><td style="color:var(--orange);font-weight:600">${c.sec}</td><td>${c.thk}</td><td>${c.qty.toFixed(2)}</td><td>${c.dueDay}</td></tr>`;
    });
    html+=`</tbody></table></div>`;
  });

  container.innerHTML = html;
}

// ── Excel download ────────────────────────────────────────

function downloadExcel(){
  const wb=XLSX.utils.book_new();
  function schedToSheet(schedule){
    const data=[['#','Section','Thickness','Qty (MT)','Due Day','Start Day','Finish Day','CO Type','CO Hrs','CO Cost (Rs)','Late Days','Late MT','Early Days','Storage MT']];
    schedule.forEach(r=>data.push([r.pos,r.section,r.thickness,r.qty,r.due_day,r.start_day,r.finish_day,r.co_type,r.co_hrs||0,r.co_cost||0,r.late_days,r.late_mt,r.early_days,r.storage_mt]));
    return XLSX.utils.aoa_to_sheet(data);
  }
  if(STATE.selectedSM!==null){const sol=STATE.results.sm.solutions[STATE.selectedSM];XLSX.utils.book_append_sheet(wb,schedToSheet(sol.schedule),`SM_${sol.label.replace(/[^a-zA-Z0-9]/g,'_').substring(0,25)}`);}
  if(STATE.selectedLM!==null){const sol=STATE.results.lm.solutions[STATE.selectedLM];XLSX.utils.book_append_sheet(wb,schedToSheet(sol.schedule),`LM_${sol.label.replace(/[^a-zA-Z0-9]/g,'_').substring(0,25)}`);}
  if(!STATE.selectedSM && !STATE.selectedLM){alert('Select a solution first');return;}
  XLSX.writeFile(wb,'SteelOpt_NSGA3_Rolling_Plan.xlsx');
}

// ── Utilities ─────────────────────────────────────────────

function fmtNum(n){
  if(n===0||n===null||n===undefined) return '0';
  if(n>=1000) return Math.round(n).toLocaleString('en-IN');
  return (+n).toFixed(1);
}

// ── Boot ─────────────────────────────────────────────────

window.onload = function(){
  renderSolutionSpace();
};
</script>
</body>
</html>'''

with open('results.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Done. Open results.html in your browser.")
