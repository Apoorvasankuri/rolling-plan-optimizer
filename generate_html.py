import json

# ── Load results ──────────────────────────────────────────
with open('results.json', 'r') as f:
    results = json.load(f)

results_js = json.dumps(results)

# ── Build HTML ────────────────────────────────────────────
html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SteelOpt — NSGA-III Rolling Schedule Optimizer</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=IBM+Plex+Sans:ital,wght@0,300;0,400;0,600;0,700;1,300&display=swap');
:root{--bg:#0a0c10;--bg2:#111318;--bg3:#181c24;--border:#252a35;--border2:#2e3545;--text:#e2e8f0;--text2:#8892a4;--text3:#5a6478;--accent:#00d4ff;--accent2:#0096ff;--green:#00e5a0;--red:#ff4466;--yellow:#ffd166;--orange:#ff8c42;--purple:#b06aff;--mono:'IBM Plex Mono',monospace;--sans:'IBM Plex Sans',sans-serif;}
*{box-sizing:border-box;margin:0;padding:0;}html{font-size:14px;}
body{background:var(--bg);color:var(--text);font-family:var(--sans);min-height:100vh;overflow-x:hidden;}
body::before{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(0,212,255,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(0,212,255,0.03) 1px,transparent 1px);background-size:40px 40px;pointer-events:none;z-index:0;}
header{position:relative;z-index:10;padding:20px 32px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;background:rgba(10,12,16,0.95);backdrop-filter:blur(10px);}
.logo{display:flex;align-items:center;gap:12px;}.logo-icon{width:36px;height:36px;background:linear-gradient(135deg,var(--accent),var(--accent2));border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:18px;}
.logo-text{font-family:var(--mono);font-size:1.3rem;font-weight:700;letter-spacing:-0.5px;}.logo-text span{color:var(--accent);}
.header-badge{font-family:var(--mono);font-size:0.7rem;color:var(--text3);background:var(--bg3);border:1px solid var(--border);padding:4px 10px;border-radius:4px;letter-spacing:1px;text-transform:uppercase;}
main{position:relative;z-index:1;max-width:1400px;margin:0 auto;padding:32px 24px;}
.steps{display:flex;align-items:center;gap:0;margin-bottom:36px;}
.step{display:flex;align-items:center;gap:10px;padding:10px 20px;border:1px solid var(--border);background:var(--bg2);cursor:pointer;transition:all 0.2s;flex:1;position:relative;}
.step:first-child{border-radius:8px 0 0 8px;}.step:last-child{border-radius:0 8px 8px 0;}
.step.active{background:rgba(0,212,255,0.08);border-color:var(--accent);}
.step.done{background:rgba(0,229,160,0.06);border-color:var(--green);}
.step-num{width:24px;height:24px;border-radius:50%;background:var(--border2);display:flex;align-items:center;justify-content:center;font-family:var(--mono);font-size:0.75rem;font-weight:700;flex-shrink:0;}
.step.active .step-num{background:var(--accent);color:var(--bg);}.step.done .step-num{background:var(--green);color:var(--bg);}
.step-label{font-size:0.8rem;font-weight:600;color:var(--text2);white-space:nowrap;}
.step.active .step-label{color:var(--accent);}.step.done .step-label{color:var(--green);}
.panel{display:none;animation:fadeIn 0.3s ease;}.panel.active{display:block;}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:translateY(0);}}
.section-title{font-family:var(--mono);font-size:0.7rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--accent);margin-bottom:16px;display:flex;align-items:center;gap:8px;}
.section-title::after{content:'';flex:1;height:1px;background:linear-gradient(to right,var(--border2),transparent);}
.upload-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:28px;}
.upload-zone{border:1.5px dashed var(--border2);border-radius:10px;padding:24px 20px;text-align:center;cursor:pointer;transition:all 0.25s;background:var(--bg2);position:relative;overflow:hidden;}
.upload-zone:hover{border-color:var(--accent);background:rgba(0,212,255,0.04);}
.upload-zone.ready{border-color:var(--green);border-style:solid;background:rgba(0,229,160,0.04);}
.upload-zone.optional{border-color:var(--border);opacity:0.8;}
.upload-zone input{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%;}
.upload-icon{font-size:2rem;margin-bottom:10px;}.upload-label{font-weight:700;font-size:0.9rem;margin-bottom:4px;}
.upload-hint{font-size:0.75rem;color:var(--text3);margin-bottom:6px;}
.upload-status{font-family:var(--mono);font-size:0.72rem;margin-top:8px;padding:3px 8px;border-radius:4px;display:inline-block;}
.upload-status.ok{background:rgba(0,229,160,0.15);color:var(--green);}.upload-status.waiting{background:var(--bg3);color:var(--text3);}.upload-status.opt{background:rgba(255,209,102,0.12);color:var(--yellow);}
.config-row{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:28px;}
.config-field label{display:block;font-family:var(--mono);font-size:0.68rem;color:var(--text3);letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;}
.config-field input{width:100%;background:var(--bg3);border:1px solid var(--border2);border-radius:6px;padding:8px 12px;color:var(--text);font-family:var(--mono);font-size:0.85rem;outline:none;}
.run-btn{display:flex;align-items:center;justify-content:center;gap:10px;background:linear-gradient(135deg,var(--accent),var(--accent2));color:#000;border:none;border-radius:8px;padding:14px 32px;font-family:var(--mono);font-size:0.95rem;font-weight:700;cursor:pointer;transition:all 0.2s;letter-spacing:0.5px;}
.run-btn:hover{transform:translateY(-1px);box-shadow:0 8px 24px rgba(0,212,255,0.3);}
.run-btn:disabled{opacity:0.4;cursor:not-allowed;transform:none;box-shadow:none;}
.pareto-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:28px;}
.chart-wrap{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:20px;margin-bottom:20px;}
.chart-title{font-family:var(--mono);font-size:0.72rem;color:var(--text2);margin-bottom:14px;letter-spacing:1px;text-transform:uppercase;}
.sol-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:28px;}
.sol-card{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:18px;cursor:pointer;transition:all 0.2s;position:relative;}
.sol-card:hover{border-color:var(--accent);background:rgba(0,212,255,0.04);}
.sol-card.selected{border-color:var(--accent);background:rgba(0,212,255,0.08);box-shadow:0 0 20px rgba(0,212,255,0.1);}
.sol-card.balanced{border-color:var(--yellow);}.sol-card.balanced.selected{background:rgba(255,209,102,0.08);}
.sol-label{font-family:var(--mono);font-size:0.72rem;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:14px;color:var(--accent);}
.sol-card.balanced .sol-label{color:var(--yellow);}
.sol-metric{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.03);}
.sol-metric:last-child{border-bottom:none;}.sol-metric-name{color:var(--text2);font-size:0.72rem;}
.sol-metric-val{font-family:var(--mono);font-size:0.78rem;font-weight:600;color:var(--text);}
.sol-metric-val.best{color:var(--green);}
.selected-badge{position:absolute;top:10px;right:10px;font-family:var(--mono);font-size:0.6rem;background:var(--accent);color:#000;padding:2px 6px;border-radius:3px;font-weight:700;}
.tabs{display:flex;gap:2px;margin-bottom:20px;background:var(--bg2);border-radius:8px;padding:4px;border:1px solid var(--border);width:fit-content;}
.tab{padding:7px 18px;border-radius:6px;cursor:pointer;font-family:var(--mono);font-size:0.75rem;font-weight:600;color:var(--text3);transition:all 0.2s;border:none;background:none;}
.tab.active{background:var(--bg3);color:var(--accent);border:1px solid var(--border2);}
.sched-wrap{overflow-x:auto;border-radius:8px;border:1px solid var(--border);margin-bottom:24px;max-height:500px;overflow-y:auto;}
.sched-table{width:100%;border-collapse:collapse;font-size:0.78rem;}
.sched-table th{background:var(--bg3);color:var(--text3);font-family:var(--mono);font-size:0.65rem;letter-spacing:1px;text-transform:uppercase;padding:10px 14px;text-align:left;border-bottom:1px solid var(--border2);position:sticky;top:0;z-index:2;white-space:nowrap;}
.sched-table td{padding:9px 14px;border-bottom:1px solid var(--border);font-family:var(--mono);font-size:0.75rem;white-space:nowrap;}
.sched-table tr:hover td{background:rgba(255,255,255,0.02);}.sched-table tr:last-child td{border-bottom:none;}
.badge{padding:2px 7px;border-radius:3px;font-size:0.68rem;font-weight:600;font-family:var(--mono);display:inline-block;}
.badge-late{background:rgba(255,68,102,0.15);color:var(--red);}.badge-ok{background:rgba(0,229,160,0.12);color:var(--green);}
.badge-sec{background:rgba(255,209,102,0.15);color:var(--yellow);}.badge-thk{background:rgba(176,106,255,0.15);color:var(--purple);}
.badge-none{background:rgba(90,100,120,0.15);color:var(--text3);}
.dl-btn{display:inline-flex;align-items:center;gap:8px;background:var(--bg3);border:1px solid var(--border2);color:var(--text);padding:8px 16px;border-radius:6px;font-family:var(--mono);font-size:0.75rem;cursor:pointer;transition:all 0.2s;margin-right:8px;}
.dl-btn:hover{border-color:var(--accent);color:var(--accent);}
.compare-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:24px;}
.compare-card{background:var(--bg2);border:1px solid var(--border);border-radius:10px;overflow:hidden;}
.compare-card-header{padding:14px 18px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border);}
.compare-card-title{font-family:var(--mono);font-size:0.8rem;font-weight:700;letter-spacing:1px;}
.compare-card-title.actual{color:var(--orange);}.compare-card-title.nsga{color:var(--accent);}
.compare-card-body{padding:0;}
.metrics-table{width:100%;border-collapse:collapse;font-size:0.8rem;}
.metrics-table th{background:var(--bg3);color:var(--text3);font-family:var(--mono);font-size:0.65rem;padding:10px 16px;text-align:left;letter-spacing:1px;border-bottom:1px solid var(--border2);}
.metrics-table td{padding:10px 16px;border-bottom:1px solid var(--border);font-family:var(--mono);font-size:0.78rem;}
.metrics-table .metric-name{font-size:0.8rem;color:var(--text);font-family:var(--sans);}
.better-val{color:var(--green);font-weight:700;}.worse-val{color:var(--red);}
.kpi-delta{font-family:var(--mono);font-size:0.72rem;padding:2px 6px;border-radius:3px;display:inline-block;}
.kpi-delta.better{background:rgba(0,229,160,0.12);color:var(--green);}.kpi-delta.worse{background:rgba(255,68,102,0.12);color:var(--red);}
.divider{height:1px;background:linear-gradient(to right,transparent,var(--border2),transparent);margin:28px 0;}
.empty-state{text-align:center;padding:60px 20px;color:var(--text3);font-size:0.85rem;}.empty-icon{font-size:3rem;margin-bottom:12px;}
::-webkit-scrollbar{width:6px;height:6px;}::-webkit-scrollbar-track{background:var(--bg2);}::-webkit-scrollbar-thumb{background:var(--border2);border-radius:3px;}
@media(max-width:900px){.upload-grid{grid-template-columns:1fr 1fr;}.sol-grid{grid-template-columns:repeat(2,1fr);}.pareto-grid{grid-template-columns:1fr;}.compare-grid{grid-template-columns:1fr;}}
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
    <div class="header-badge">pymoo v3</div>
  </div>
</header>
<main>
  <div class="steps">
    <div class="step active" id="step1" onclick="goStep(1)"><div class="step-num">1</div><div class="step-label">Upload Files</div></div>
    <div class="step" id="step2" onclick="goStep(2)"><div class="step-num">2</div><div class="step-label">Run Parameters</div></div>
    <div class="step" id="step3" onclick="goStep(3)"><div class="step-num">3</div><div class="step-label">Results</div></div>
    <div class="step" id="step4" onclick="goStep(4)"><div class="step-num">4</div><div class="step-label">Actual vs NSGA-III</div></div>
  </div>

  <!-- PANEL 1 -->
  <div class="panel active" id="panel1">
    <div class="section-title">⬆ Upload Files</div>
    <div class="upload-grid">
      <div class="upload-zone" id="zone-loi">
        <input type="file" accept=".xlsx,.xls" onchange="loadLOI(this)">
        <div class="upload-icon">📋</div><div class="upload-label">LOI File</div>
        <div class="upload-hint">LOI_Jan_2026.xlsx (required)</div>
        <div class="upload-status waiting" id="status-loi">Waiting...</div>
      </div>
      <div class="upload-zone" id="zone-co">
        <input type="file" accept=".xlsx,.xls" onchange="loadCO(this)">
        <div class="upload-icon">🔄</div><div class="upload-label">Changeover Matrix</div>
        <div class="upload-hint">Section & Thickness costs (required)</div>
        <div class="upload-status waiting" id="status-co">Waiting...</div>
      </div>
      <div class="upload-zone ready" id="zone-results">
        <input type="file" accept=".json" onchange="loadResults(this)">
        <div class="upload-icon">⚡</div><div class="upload-label">NSGA-III Results</div>
        <div class="upload-hint">Upload new results.json to refresh</div>
        <div class="upload-status ok" id="status-results">✓ Embedded results loaded</div>
      </div>
      <div class="upload-zone optional" id="zone-actual">
        <input type="file" accept=".xlsx,.xls" multiple onchange="loadActual(this)">
        <div class="upload-icon">📊</div><div class="upload-label">Actual Rolling Plans</div>
        <div class="upload-hint">SM + LM plans (optional, for comparison)</div>
        <div class="upload-status opt" id="status-actual">Optional</div>
      </div>
    </div>
    <div style="display:flex;gap:12px;align-items:center;">
      <button class="run-btn" onclick="goStep(2)" id="btn-next1" disabled>Continue to Parameters →</button>
      <span style="font-size:0.75rem;color:var(--text3);">LOI + Changeover files required to proceed</span>
    </div>
  </div>

  <!-- PANEL 2 -->
  <div class="panel" id="panel2">
    <div class="section-title">⚙ Run Parameters</div>
    <div class="config-row" id="params-display"></div>
    <div style="background:var(--bg2);border:1px solid var(--border2);border-radius:8px;padding:20px;margin-bottom:24px;">
      <div style="font-family:var(--mono);font-size:0.72rem;color:var(--yellow);margin-bottom:10px;">▶ TO RE-RUN WITH DIFFERENT PARAMETERS</div>
      <div style="font-size:0.8rem;color:var(--text2);line-height:2;">
        1. Edit <code style="color:var(--accent)">main.py</code> — change SM_CAP, LM_CAP, N_GEN, POP_SIZE<br>
        2. Run <code style="color:var(--accent)">python main.py</code> in terminal<br>
        3. Run <code style="color:var(--accent)">python generate_html.py</code> to regenerate this page<br>
        4. Or upload the new <code style="color:var(--accent)">results.json</code> on Step 1
      </div>
    </div>
    <button class="run-btn" onclick="goStep(3)">View Results →</button>
  </div>

  <!-- PANEL 3 -->
  <div class="panel" id="panel3">
    <div id="results-content">
      <div class="empty-state"><div class="empty-icon">⚙</div><div>Loading results...</div></div>
    </div>
  </div>

  <!-- PANEL 4 -->
  <div class="panel" id="panel4">
    <div id="compare-content">
      <div class="empty-state"><div class="empty-icon">📊</div><div>Upload actual rolling plans and select a solution to see comparison</div></div>
    </div>
  </div>
</main>

<script>
const EMBEDDED = ''' + results_js + ''';

const STATE = {loi:null, co:null, results:EMBEDDED, actualSM:null, actualLM:null};
let charts = {};
let selectedSM = null;
let selectedLM = null;
const OBJ_LABELS = EMBEDDED.obj_labels;
const SHIFT_HRS = 12.0;
const STRETCH_MAX = 15.6;
const SEC_COST = 24100.0;

function goStep(n) {
  [1,2,3,4].forEach(i=>{
    document.getElementById('step'+i).classList.remove('active');
    document.getElementById('panel'+i).classList.remove('active');
  });
  document.getElementById('step'+n).classList.add('active');
  document.getElementById('panel'+n).classList.add('active');
  if(n===3) renderResults();
  if(n===4) renderComparison();
}

function loadLOI(input) {
  const file=input.files[0]; if(!file) return;
  const reader=new FileReader();
  reader.onload=e=>{
    STATE.loi=XLSX.read(e.target.result,{type:'array',cellDates:true});
    setStatus('loi',`✓ ${file.name}`,'ok');
    document.getElementById('zone-loi').classList.add('ready');
    checkReady();
  };
  reader.readAsArrayBuffer(file);
}

function loadCO(input) {
  const file=input.files[0]; if(!file) return;
  const reader=new FileReader();
  reader.onload=e=>{
    const wb=XLSX.read(e.target.result,{type:'array',cellDates:true});
    STATE.co=parseCO(wb);
    setStatus('co',`✓ ${file.name}`,'ok');
    document.getElementById('zone-co').classList.add('ready');
    checkReady();
  };
  reader.readAsArrayBuffer(file);
}

function loadResults(input) {
  const file=input.files[0]; if(!file) return;
  const reader=new FileReader();
  reader.onload=e=>{
    try{
      STATE.results=JSON.parse(e.target.result);
      setStatus('results',`✓ ${file.name}`,'ok');
      document.getElementById('zone-results').classList.add('ready');
      checkReady();
    } catch(err){ setStatus('results','✗ Invalid JSON','waiting'); }
  };
  reader.readAsText(file);
}

function loadActual(input) {
  Array.from(input.files).forEach(file=>{
    const reader=new FileReader();
    reader.onload=e=>{
      const wb=XLSX.read(e.target.result,{type:'array',cellDates:true});
      const plan=parseActualPlan(wb);
      const isSM=file.name.toLowerCase().includes('sm');
      if(isSM) STATE.actualSM=plan; else STATE.actualLM=plan;
      const count=[STATE.actualSM,STATE.actualLM].filter(Boolean).length;
      setStatus('actual',`✓ ${count} plan(s) loaded`,'ok');
      document.getElementById('zone-actual').classList.add('ready');
    };
    reader.readAsArrayBuffer(file);
  });
}

function setStatus(type,msg,cls){
  const el=document.getElementById('status-'+type);
  el.textContent=msg; el.className='upload-status '+cls;
}

function checkReady(){
  const ok=STATE.loi&&STATE.co;
  document.getElementById('btn-next1').disabled=!ok;
  if(ok){
    document.getElementById('step1').classList.add('done');
    renderParams();
  }
}

function parseCO(wb){
  const result={secTime:{},thickSM:{},thickLM:{}};
  const secSheet=wb.Sheets['Section Roll Changeover Time'];
  if(secSheet){
    const raw=XLSX.utils.sheet_to_json(secSheet,{header:1,defval:null});
    const labels=raw[0].slice(1).map(String);
    for(let i=1;i<raw.length;i++){
      const rowLabel=String(raw[i][0]||'').trim();
      if(!rowLabel||rowLabel==='Section') continue;
      result.secTime[rowLabel]={};
      labels.forEach((col,j)=>{result.secTime[rowLabel][col]=parseHrs(raw[i][j+1]);});
    }
  }
  ['Thickness Changeover Cost_SM','Thickness Changeover Cost_LM'].forEach(name=>{
    const sh=wb.Sheets[name]; if(!sh) return;
    const raw=XLSX.utils.sheet_to_json(sh,{header:1,defval:null});
    const headers=raw[0].slice(1).map(Number).filter(v=>!isNaN(v));
    const target=name.includes('SM')?result.thickSM:result.thickLM;
    for(let i=1;i<raw.length;i++){
      const t1=parseInt(raw[i][0]); if(isNaN(t1)) continue;
      target[t1]={};
      headers.forEach((t2,j)=>{
        const v=raw[i][j+1];
        target[t1][t2]=(v&&v!=='X'&&!isNaN(parseFloat(v)))?parseFloat(v):null;
      });
    }
  });
  return result;
}

function parseHrs(v){
  if(!v||v==='X') return null;
  const s=String(v).toLowerCase();
  if(s.includes('8-12')||s.includes('8 -12')) return 10;
  if(s.includes('6-8')||s.includes('6 -8')) return 7;
  return null;
}

function parseActualPlan(wb){
  const sheetName=wb.SheetNames.find(s=>s.toUpperCase()==='JAN')||wb.SheetNames[0];
  const raw=XLSX.utils.sheet_to_json(wb.Sheets[sheetName],{header:1,cellDates:true,defval:null});
  const rows=[];
  for(let i=1;i<raw.length;i++){
    const r=raw[i]; if(!r[0]) continue;
    const startDate=r[0] instanceof Date?r[0]:new Date(r[0]);
    const sec=String(r[11]||'').trim();
    const qty=parseFloat(r[12])||0;
    const bucket=r[6] instanceof Date?r[6]:new Date(r[6]);
    if(!sec||qty<=0||isNaN(startDate)) continue;
    rows.push({startDate,section:sec,qty,bucket});
  }
  rows.sort((a,b)=>a.startDate-b.startDate);
  return rows;
}

function buildActualCampaigns(rows){
  const seen=[],map={};
  rows.forEach(r=>{
    const parts=r.section.split('X');
    const section=parts.slice(0,2).join('X');
    const thickness=parseInt(parts[2])||6;
    const key=section+'__'+thickness;
    if(!map[key]){map[key]={section,thickness,qty:0,maxDue:31,minDue:1,order:seen.length};seen.push(key);}
    map[key].qty+=r.qty;
    const bd=r.bucket instanceof Date&&!isNaN(r.bucket)?r.bucket:null;
    let dueDay=31;
    if(bd){
      if(bd.getFullYear()===2026&&bd.getMonth()===0) dueDay=bd.getDate();
      else if(bd<new Date(2026,0,1)) dueDay=1;
    }
    map[key].maxDue=Math.max(map[key].maxDue,dueDay);
    map[key].minDue=Math.min(map[key].minDue,dueDay);
  });
  return seen.map(k=>map[k]);
}

function evaluateActual(camps,cap,mill,co){
  let secCoTime=0,secCoCost=0,thkCoCost=0,lateMtDays=0,storageMtDays=0,storageDays=0;
  let clock=0,prevSec=null,prevThk=null;
  camps.forEach(c=>{
    const sec=c.section,thk=c.thickness,qty=c.qty,due=c.maxDue;
    if(prevSec!==null){
      if(prevSec!==sec){
        const coHrs=(co.secTime[prevSec]&&co.secTime[prevSec][sec])||7;
        const remaining=SHIFT_HRS-(clock%SHIFT_HRS);
        secCoTime+=Math.min(coHrs,remaining);
        secCoCost+=SEC_COST;
        clock=(Math.floor(clock/SHIFT_HRS)+1)*SHIFT_HRS;
      } else if(prevThk!==thk){
        const mat=mill==='SM'?co.thickSM:co.thickLM;
        const cost=(mat[prevThk]&&mat[prevThk][thk]!=null)?mat[prevThk][thk]:null;
        if(cost!==null&&cost>0){clock=(Math.floor(clock/SHIFT_HRS)+1)*SHIFT_HRS;thkCoCost+=cost;}
      }
    }
    const rollHrs=(qty/cap)*SHIFT_HRS;
    clock=rollHrs<=STRETCH_MAX?(Math.floor(clock/SHIFT_HRS)+1)*SHIFT_HRS:clock+rollHrs;
    const finDay=clock/SHIFT_HRS;
    if(finDay>due) lateMtDays+=qty*(finDay-due);
    if(finDay<due){storageMtDays+=qty*(due-finDay);storageDays+=(due-finDay);}
    prevSec=sec;prevThk=thk;
  });
  return [secCoTime,secCoCost,thkCoCost,lateMtDays,storageMtDays,storageDays];
}

function renderParams(){
  const r=STATE.results;
  const params=[
    {label:'SM Campaigns',val:r.sm.solutions[0].schedule.length},
    {label:'LM Campaigns',val:r.lm.solutions[0].schedule.length},
    {label:'SM Pareto Solutions',val:r.sm.solutions.length},
    {label:'LM Pareto Solutions',val:r.lm.solutions.length},
    {label:'Objectives',val:r.obj_labels?r.obj_labels.length:6},
    {label:'Solutions per Mill',val:r.sm.solutions.length},
    {label:'SM Capacity (MT/day)',val:140},
    {label:'LM Capacity (MT/day)',val:250},
  ];
  document.getElementById('params-display').innerHTML=params.map(p=>`
    <div class="config-field"><label>${p.label}</label>
    <input type="text" value="${p.val}" readonly style="opacity:0.7;cursor:default;"></div>`).join('');
}

function renderResults(){
  const r=STATE.results;
  const container=document.getElementById('results-content');
  container.innerHTML=`
    <div class="section-title">◈ Pareto Fronts</div>
    <div class="chart-wrap">
      <div style="display:flex;gap:8px;align-items:center;margin-bottom:16px;flex-wrap:wrap;">
        <button onclick="setPCPMill('sm')" id="pcp-btn-sm" style="font-size:12px;padding:5px 14px;border-radius:20px;border:1px solid #00d4ff;background:#00d4ff;color:#000;cursor:pointer;font-weight:600;">SM mill</button>
        <button onclick="setPCPMill('lm')" id="pcp-btn-lm" style="font-size:12px;padding:5px 14px;border-radius:20px;border:1px solid #252a35;background:transparent;color:#8892a4;cursor:pointer;">LM mill</button>
        <span style="font-size:11px;color:#5a6478;">Click a solution chip to highlight it · Lower is better on every axis</span>
      </div>
      <div id="pcp-chips" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:16px;"></div>
      <canvas id="pcp-canvas" height="300" style="display:block;width:100%;border-radius:6px;"></canvas>
      <p style="font-size:11px;color:#5a6478;margin-top:8px;text-align:center;">Each line = one solution · Each vertical axis = one objective · Click any line or chip to focus</p>
    </div>
    <div class="divider"></div>
    <div class="section-title">⚙ Small Mill (SM) — Select a Solution</div>
    <div class="sol-grid" id="sm-cards"></div>
    <div class="divider"></div>
    <div class="section-title">⚙ Large Mill (LM) — Select a Solution</div>
    <div class="sol-grid" id="lm-cards"></div>
    <div class="divider"></div>
    <div id="plan-section" style="display:none">
      <div class="section-title">📋 Rolling Plan</div>
      <div style="margin-bottom:16px;">
        <button class="dl-btn" onclick="downloadExcel()">⬇ Download as Excel</button>
        <button class="dl-btn" onclick="goStep(4)" style="border-color:var(--yellow);color:var(--yellow);">📊 Compare with Actual →</button>
      </div>
      <div class="tabs">
        <button class="tab active" onclick="showMill('sm')">Small Mill (SM)</button>
        <button class="tab" onclick="showMill('lm')">Large Mill (LM)</button>
      </div>
      <div id="plan-sm"></div>
      <div id="plan-lm" style="display:none"></div>
    </div>`;
  setTimeout(()=>{renderParetoCharts(r);renderCards('sm',r.sm.solutions,'sm-cards');renderCards('lm',r.lm.solutions,'lm-cards');pcpMill='sm';},50);
}

const PCP_DIMS=[
  {key:'late', label:'Late delivery', unit:'MT·days', color:'#ff4466'},
  {key:'sct',  label:'Sec CO time',   unit:'hrs',     color:'#00d4ff'},
  {key:'scc',  label:'Sec CO cost',   unit:'Rs',      color:'#00e5a0'},
  {key:'thk',  label:'Thk CO cost',   unit:'Rs',      color:'#ffd166'},
  {key:'stmt', label:'Storage',       unit:'MT·days', color:'#b06aff'},
  {key:'stday',label:'Storage days',  unit:'days',    color:'#ff8c42'},
];
const PCP_COLORS=['#ff4466','#00d4ff','#00e5a0','#ffd166','#b06aff','#ff8c42','#0096ff','#ff6b9d','#40e0d0','#ffaa00'];
let pcpMill='sm', pcpActive=0;

function setPCPMill(mill){
  pcpMill=mill;
  pcpActive=0;
  document.getElementById('pcp-btn-sm').style.background=mill==='sm'?'#00d4ff':'transparent';
  document.getElementById('pcp-btn-sm').style.color=mill==='sm'?'#000':'#8892a4';
  document.getElementById('pcp-btn-sm').style.borderColor=mill==='sm'?'#00d4ff':'#252a35';
  document.getElementById('pcp-btn-lm').style.background=mill==='lm'?'#00d4ff':'transparent';
  document.getElementById('pcp-btn-lm').style.color=mill==='lm'?'#000':'#8892a4';
  document.getElementById('pcp-btn-lm').style.borderColor=mill==='lm'?'#00d4ff':'#252a35';
  renderParetoCharts(STATE.results);
}

function renderParetoCharts(r){
  const data=r[pcpMill].solutions.map(sol=>({
    late: sol.objectives['Late (MT\u00b7days)'],
    sct:  sol.objectives['Sec CO time (hrs)'],
    scc:  sol.objectives['Sec CO cost (Rs)'],
    thk:  sol.objectives['Thk CO cost (Rs)'],
    stmt: sol.objectives['Storage (MT\u00b7days)'],
    stday:sol.objectives['Storage (days)'],
    lbl:  sol.label
  }));

  const cv=document.getElementById('pcp-canvas');
  if(!cv) return;
  const ctx=cv.getContext('2d');
  const W=cv.offsetWidth||900, H=300;
  cv.width=W; cv.height=H;
  ctx.clearRect(0,0,W,H);

  const ML=50,MR=20,MT=65,MB=35;
  const IW=W-ML-MR, IH=H-MT-MB;
  const nDims=PCP_DIMS.length;

  function xOf(i){return ML+i*(IW/(nDims-1));}
  function yOf(dimIdx,val){
    const vals=data.map(d=>d[PCP_DIMS[dimIdx].key]);
    const mn=Math.min(...vals),mx=Math.max(...vals),r=mx-mn||1;
    return MT+IH-((val-mn)/r)*IH;
  }
  function fmt(v,k){
    if(k==='scc'||k==='thk') return v>=1000?(v/1000).toFixed(0)+'k':''+v;
    if(v>=10000) return (v/1000).toFixed(0)+'k';
    return Number.isInteger(v)?''+v:v.toFixed(1);
  }

  // background lines
  data.forEach((d,i)=>{
    if(i===pcpActive) return;
    ctx.beginPath();
    PCP_DIMS.forEach((dim,j)=>{
      const x=xOf(j),y=yOf(j,d[dim.key]);
      j===0?ctx.moveTo(x,y):ctx.lineTo(x,y);
    });
    ctx.strokeStyle=PCP_COLORS[i%PCP_COLORS.length]+'25';
    ctx.lineWidth=1.5; ctx.stroke();
  });

  // highlighted line
  const hi=data[pcpActive];
  ctx.beginPath();
  PCP_DIMS.forEach((dim,j)=>{
    const x=xOf(j),y=yOf(j,hi[dim.key]);
    j===0?ctx.moveTo(x,y):ctx.lineTo(x,y);
  });
  ctx.strokeStyle=PCP_COLORS[pcpActive%PCP_COLORS.length];
  ctx.lineWidth=3; ctx.lineJoin='round'; ctx.stroke();

  // axes + labels + dots + values
  PCP_DIMS.forEach((dim,i)=>{
    const x=xOf(i);
    const vals=data.map(d=>d[dim.key]);
    const mn=Math.min(...vals),mx=Math.max(...vals);

    ctx.beginPath();ctx.moveTo(x,MT);ctx.lineTo(x,MT+IH);
    ctx.strokeStyle='#252a35';ctx.lineWidth=1.5;ctx.stroke();

    ctx.fillStyle=dim.color;ctx.font='bold 11px IBM Plex Mono,monospace';ctx.textAlign='center';
    ctx.fillText(dim.label,x,MT-30);
    ctx.fillStyle='#5a6478';ctx.font='10px IBM Plex Mono,monospace';
    ctx.fillText('('+dim.unit+')',x,MT-16);

    ctx.fillStyle='#5a6478';ctx.font='9px IBM Plex Mono,monospace';ctx.textAlign='right';
    ctx.fillText(fmt(mn,dim.key),x-8,MT+IH+4);
    ctx.fillText(fmt(mx,dim.key),x-8,MT+4);

    const hy=yOf(i,hi[dim.key]);
    ctx.beginPath();ctx.arc(x,hy,7,0,Math.PI*2);
    ctx.fillStyle=dim.color;ctx.fill();
    ctx.strokeStyle='#0a0c10';ctx.lineWidth=2;ctx.stroke();

    ctx.fillStyle=dim.color;ctx.font='bold 10px IBM Plex Mono,monospace';ctx.textAlign='center';
    ctx.fillText(fmt(hi[dim.key],dim.key),x,hy-12);
  });

  ctx.textAlign='left';

  // chips
  const chips=document.getElementById('pcp-chips');
  if(!chips) return;
  chips.innerHTML='';
  data.forEach((d,i)=>{
    const chip=document.createElement('button');
    chip.textContent=d.lbl;
    chip.style.cssText=`font-size:11px;padding:4px 12px;border-radius:20px;cursor:pointer;border:1.5px solid ${PCP_COLORS[i%PCP_COLORS.length]};background:${i===pcpActive?PCP_COLORS[i%PCP_COLORS.length]:'transparent'};color:${i===pcpActive?'#000':PCP_COLORS[i%PCP_COLORS.length]};font-family:IBM Plex Mono,monospace;`;
    chip.onclick=()=>{pcpActive=i;renderParetoCharts(r);};
    chips.appendChild(chip);
  });

  // click on canvas line
  cv.onclick=e=>{
    const rect=cv.getBoundingClientRect();
    const mx=e.clientX-rect.left,my=e.clientY-rect.top;
    let best=null,bestD=Infinity;
    data.forEach((d,i)=>{
      PCP_DIMS.forEach((dim,j)=>{
        const dist=Math.hypot(mx-xOf(j),my-yOf(j,d[dim.key]));
        if(dist<bestD){bestD=dist;best=i;}
      });
    });
    if(best!==null&&bestD<20){pcpActive=best;renderParetoCharts(r);}
  };
}

function renderCards(mill,solutions,containerId){
  const container=document.getElementById(containerId); if(!container) return;
  const bestVals={};
  OBJ_LABELS.forEach(obj=>{bestVals[obj]=Math.min(...solutions.map(s=>s.objectives[obj]));});
  const metrics=[
    {name:'Late (MT×days)',key:OBJ_LABELS[3]},{name:'Sec CO Time (hrs)',key:OBJ_LABELS[0]},
    {name:'Sec CO Cost (Rs)',key:OBJ_LABELS[1]},{name:'Thk CO Cost (Rs)',key:OBJ_LABELS[2]},
    {name:'Storage (MT×days)',key:OBJ_LABELS[4]},{name:'Storage Days',key:OBJ_LABELS[5]},
  ];
  container.innerHTML=solutions.map((sol,idx)=>{
    const isBalanced=sol.label==='Balanced';
    const mHtml=metrics.map(m=>{
      const val=sol.objectives[m.key];
      const isBest=val===bestVals[m.key];
      return `<div class="sol-metric"><span class="sol-metric-name">${m.name}</span><span class="sol-metric-val ${isBest?'best':''}">${fmtNum(val)}</span></div>`;
    }).join('');
    return `<div class="sol-card ${isBalanced?'balanced':''}" id="card-${mill}-${idx}" onclick="selectSolution('${mill}',${idx})">
      <div class="sol-label">${sol.label}</div>${mHtml}</div>`;
  }).join('');
}

function selectSolution(mill,idx){
  if(mill==='sm') selectedSM=idx; else selectedLM=idx;
  ['sm','lm'].forEach(m=>{
    const count=STATE.results[m].solutions.length;
    for(let i=0;i<count;i++){
      const card=document.getElementById(`card-${m}-${i}`);
      if(card){card.classList.remove('selected');const b=card.querySelector('.selected-badge');if(b)b.remove();}
    }
  });
  const sel=document.getElementById(`card-${mill}-${idx}`);
  if(sel){sel.classList.add('selected');sel.innerHTML+=`<div class="selected-badge">SELECTED</div>`;}
  if(selectedSM!==null||selectedLM!==null) renderPlan();
}

function renderPlan(){
  document.getElementById('plan-section').style.display='block';
  if(selectedSM!==null){const sol=STATE.results.sm.solutions[selectedSM];document.getElementById('plan-sm').innerHTML=buildScheduleTable(sol.schedule,'SM');}
  if(selectedLM!==null){const sol=STATE.results.lm.solutions[selectedLM];document.getElementById('plan-lm').innerHTML=buildScheduleTable(sol.schedule,'LM');}
}

function buildScheduleTable(schedule,mill){
  const color=mill==='SM'?'var(--accent)':'#ff6b6b';
  let html=`<div style="font-family:var(--mono);font-size:0.85rem;font-weight:700;padding:12px 0;margin-bottom:12px;border-bottom:1px solid var(--border2);color:${color};">
    ${mill==='SM'?'⚙ Small Mill (SM)':'⚙ Large Mill (LM)'} — ${schedule.length} campaigns</div>
  <div class="sched-wrap"><table class="sched-table"><thead><tr>
    <th>#</th><th>Section</th><th>Thk</th><th>Qty (MT)</th><th>Due Day</th>
    <th>Start Day</th><th>Finish Day</th><th>CO Type</th><th>CO Hrs</th>
    <th>CO Hrs Lost</th><th>CO Cost (Rs)</th><th>Status</th><th>Late MT</th>
    <th>Early Days</th><th>Storage MT</th>
  </tr></thead><tbody>`;
  schedule.forEach(r=>{
    const lateClass=r.late_days>0?'badge-late':'badge-ok';
    const lateText=r.late_days>0?`${r.late_days.toFixed(1)}d LATE`:'On Time';
    const coClass=r.co_type==='Section'?'badge-sec':r.co_type==='Thickness'?'badge-thk':'badge-none';
    html+=`<tr><td>${r.pos}</td><td style="color:${color};font-weight:600">${r.section}</td>
      <td>${r.thickness}</td><td>${r.qty.toFixed(2)}</td><td>${r.due_day}</td>
      <td>${r.start_day.toFixed(2)}</td><td>${r.finish_day.toFixed(2)}</td>
      <td><span class="badge ${coClass}">${r.co_type}</span></td>
      <td>${r.co_hrs}</td><td>${r.co_hrs_lost}</td>
      <td>${r.co_cost>0?'₹'+fmtNum(r.co_cost):'—'}</td>
      <td><span class="badge ${lateClass}">${lateText}</span></td>
      <td>${r.late_mt>0?r.late_mt.toFixed(1):'—'}</td>
      <td>${r.early_days>0?r.early_days.toFixed(1):'—'}</td>
      <td>${r.storage_mt>0?r.storage_mt.toFixed(1):'—'}</td></tr>`;
  });
  html+=`</tbody></table></div>`;
  return html;
}

function showMill(mill){
  document.getElementById('plan-sm').style.display=mill==='sm'?'block':'none';
  document.getElementById('plan-lm').style.display=mill==='lm'?'block':'none';
  document.querySelectorAll('.tab').forEach((t,i)=>{t.classList.toggle('active',(i===0&&mill==='sm')||(i===1&&mill==='lm'));});
}

function renderComparison(){
  const container=document.getElementById('compare-content');
  if(!STATE.actualSM&&!STATE.actualLM){
    container.innerHTML=`<div class="empty-state"><div class="empty-icon">📊</div><div>Upload actual SM and/or LM rolling plans in Step 1 to see comparison</div></div>`;
    return;
  }
  if(selectedSM===null&&selectedLM===null){
    container.innerHTML=`<div class="empty-state"><div class="empty-icon">📋</div><div>Select a solution in Step 3 first, then come back here</div></div>`;
    return;
  }
  const mills=[];
  if(STATE.actualSM&&selectedSM!==null) mills.push({label:'Small Mill (SM)',mill:'SM',actual:STATE.actualSM,cap:140});
  if(STATE.actualLM&&selectedLM!==null) mills.push({label:'Large Mill (LM)',mill:'LM',actual:STATE.actualLM,cap:250});
  if(!mills.length){container.innerHTML=`<div class="empty-state"><div class="empty-icon">📊</div><div>No matching actual plans and selected solutions</div></div>`;return;}
  document.getElementById('step4').classList.add('done');

  mills.forEach(m=>{
    const camps=buildActualCampaigns(m.actual);
    m.actualF=evaluateActual(camps,m.cap,m.mill,STATE.co||{secTime:{},thickSM:{},thickLM:{}});
    const selIdx=m.mill==='SM'?selectedSM:selectedLM;
    m.nsgaF=OBJ_LABELS.map(lbl=>STATE.results[m.mill.toLowerCase()].solutions[selIdx].objectives[lbl]);
    m.actualCamps=camps;
    m.nsgaSol=STATE.results[m.mill.toLowerCase()].solutions[selIdx];
  });

  const objNames=['Sec CO Time (hrs)','Sec CO Cost (Rs)','Thk CO Cost (Rs)','Late (MT×days)','Storage (MT×days)','Storage Days'];
  let html=`<div class="section-title">⚖ Actual Plan vs NSGA-III Optimization</div>
  <div class="chart-wrap" style="margin-bottom:24px;">
    <div class="chart-title">Performance Comparison</div>
    <table class="metrics-table"><thead><tr><th>Objective</th>
      ${mills.map(m=>`<th style="color:var(--orange)">${m.label} — Actual</th><th style="color:var(--accent)">${m.label} — NSGA-III</th><th>Δ Improvement</th>`).join('')}
    </tr></thead><tbody>`;

  objNames.forEach((name,i)=>{
    html+=`<tr><td class="metric-name">${name}</td>`;
    mills.forEach(m=>{
      const aVal=m.actualF[i],nVal=m.nsgaF[i];
      const better=nVal<=aVal;
      const delta=aVal>0?((nVal-aVal)/aVal*100):0;
      const sign=delta>0?'+':'';
      html+=`<td style="color:var(--orange)">${fmtNum(aVal)}</td>
             <td class="${better?'better-val':'worse-val'}">${fmtNum(nVal)}</td>
             <td><span class="kpi-delta ${better?'better':'worse'}">${sign}${delta.toFixed(1)}%</span></td>`;
    });
    html+=`</tr>`;
  });
  html+=`</tbody></table></div>`;

  mills.forEach(m=>{
    html+=`<div class="section-title">📅 ${m.label} — Schedule Comparison</div>
    <div class="compare-grid">
      <div class="compare-card">
        <div class="compare-card-header">
          <div class="compare-card-title actual">📋 ACTUAL PLAN</div>
          <div style="font-family:var(--mono);font-size:0.72rem;color:var(--text3)">${m.actualCamps.length} campaigns</div>
        </div>
        <div class="compare-card-body">${buildActualTable(m.actualCamps,m.mill)}</div>
      </div>
      <div class="compare-card">
        <div class="compare-card-header">
          <div class="compare-card-title nsga">⚡ NSGA-III — ${m.nsgaSol.label}</div>
          <div style="font-family:var(--mono);font-size:0.72rem;color:var(--text3)">${m.nsgaSol.schedule.length} campaigns</div>
        </div>
        <div class="compare-card-body">${buildScheduleTable(m.nsgaSol.schedule,m.mill)}</div>
      </div>
    </div>`;
  });

  container.innerHTML=html;
}

function buildActualTable(camps,mill){
  const color=mill==='SM'?'var(--accent)':'#ff6b6b';
  let html=`<div style="overflow-x:auto;max-height:450px;overflow-y:auto;">
  <table class="sched-table"><thead><tr>
    <th>#</th><th>Section</th><th>Thk</th><th>Qty (MT)</th><th>Due Day</th>
  </tr></thead><tbody>`;
  camps.forEach((c,i)=>{html+=`<tr><td>${i+1}</td><td style="color:${color};font-weight:600">${c.section}</td><td>${c.thickness}</td><td>${c.qty.toFixed(2)}</td><td>${c.maxDue}</td></tr>`;});
  html+=`</tbody></table></div>`;
  return html;
}

function downloadExcel(){
  const wb=XLSX.utils.book_new();
  function schedToSheet(schedule){
    const data=[['#','Section','Thickness','Qty (MT)','Due Day','Start Day','Finish Day','CO Type','CO Hrs','CO Hrs Lost','CO Cost (Rs)','Late Days','Late MT','Early Days','Storage MT']];
    schedule.forEach(r=>data.push([r.pos,r.section,r.thickness,r.qty,r.due_day,r.start_day,r.finish_day,r.co_type,r.co_hrs,r.co_hrs_lost,r.co_cost,r.late_days,r.late_mt,r.early_days,r.storage_mt]));
    return XLSX.utils.aoa_to_sheet(data);
  }
  if(selectedSM!==null){const sol=STATE.results.sm.solutions[selectedSM];XLSX.utils.book_append_sheet(wb,schedToSheet(sol.schedule),`SM_${sol.label.replace(/ /g,'_').substring(0,25)}`);}
  if(selectedLM!==null){const sol=STATE.results.lm.solutions[selectedLM];XLSX.utils.book_append_sheet(wb,schedToSheet(sol.schedule),`LM_${sol.label.replace(/ /g,'_').substring(0,25)}`);}
  const sumRows=[['Mill','Solution',...OBJ_LABELS]];
  ['sm','lm'].forEach(mill=>{
    const idx=mill==='sm'?selectedSM:selectedLM; if(idx===null) return;
    const sol=STATE.results[mill].solutions[idx];
    sumRows.push([mill.toUpperCase(),sol.label,...OBJ_LABELS.map(l=>sol.objectives[l])]);
  });
  XLSX.utils.book_append_sheet(wb,XLSX.utils.aoa_to_sheet(sumRows),'Summary');
  XLSX.writeFile(wb,'SteelOpt_NSGA3_Rolling_Plan.xlsx');
}

function fmtNum(n){
  if(n===0||n===null||n===undefined) return '0';
  if(n>=1000) return Math.round(n).toLocaleString('en-IN');
  return (+n).toFixed(1);
}

window.onload=function(){
  renderResults();
  document.getElementById('step3').classList.add('done');
};
</script>
</body>
</html>'''

with open('results.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Done. Open outputs/results.html in your browser.")