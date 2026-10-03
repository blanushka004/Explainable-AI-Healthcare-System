"use strict";
const $=id=>document.getElementById(id);
const esc=value=>String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const pct=v=>v==null?"â€”":(v*100).toFixed(1)+"%";
const num=v=>v==null?"â€”":Number(v).toFixed(3);
let meta,report,currentAssessment,batchData,historySkip=0,historyTotal=0,thresholdTimer,thresholdSequence=0,account,csrfToken,sessionGeneration=0;
const USER_FEATURE_LABELS={age:"Age",sex:"Sex",cp:"Chest pain type",trestbps:"Resting blood pressure",chol:"Cholesterol",fbs:"Fasting blood sugar above 120 mg/dL?",restecg:"ECG result",thalach:"Highest heart rate during the exercise test",exang:"Chest pain during exercise",oldpeak:"Exercise ST depression",slope:"Peak exercise ST slope",ca:"Major vessels colored by fluoroscopy",thal:"Thallium stress-test result"};
const USER_FEATURE_HELP={restecg:"ECG records the heart’s electrical activity.",oldpeak:"Recorded ST-segment change during exercise compared with rest.",slope:"Use the peak exercise ST slope recorded in the report.",ca:"Use the major-vessels-by-fluoroscopy value recorded in the report.",thal:"Use the thallium stress-test result recorded in the report."};async function api(path,options={}){
 const response=await fetch(path,options);let data;
 try{data=await response.json()}catch{throw new Error("The server returned an unreadable response.")}
 if(!response.ok){let detail=data.detail;const field=e=>{const key=e.loc?.slice(1).join(".");return account?.role!=="ADMIN"&&USER_FEATURE_LABELS[key]?USER_FEATURE_LABELS[key]:key};const error=new Error(Array.isArray(detail)?detail.map(e=>`${field(e)}: ${e.msg}`).join("; "):typeof detail==="string"?detail:"Request failed");error.status=response.status;error.detail=detail;throw error}
 return data;
}
function showError(error){const authVisible=!$("authScreen").classList.contains("hidden");const target=authVisible?$("authError"):$("error");target.textContent=error.message||String(error);target.classList.remove("hidden");target.scrollIntoView({behavior:"smooth",block:"nearest"})}
function clearError(){$("error").classList.add("hidden")}
async function busy(button,work){const text=button.textContent;button.disabled=true;button.textContent="Workingâ€¦";clearError();try{await work()}catch(e){showError(e)}finally{button.disabled=false;button.textContent=text}}
async function sessionApi(path,options={},generation=sessionGeneration){const data=await api(path,options);if(generation!==sessionGeneration)throw new Error("Session changed; response discarded");return data}
async function refreshCsrfToken(){
 const seed=await api("/api/auth/csrf");csrfToken=seed.csrf_token;
 return api("/api/auth/me");
}
async function jsonPost(path,value){
 const generation=sessionGeneration;
 try{return await sessionApi(path,{method:"POST",headers:{"Content-Type":"application/json","X-CSRF-Token":csrfToken||""},body:JSON.stringify(value)},generation)}
 catch(error){
  if(error.status===403&&error.detail==="CSRF validation failed"){
   let active;
   try{active=await refreshCsrfToken()}catch(refreshError){
    if(refreshError.status===401){sessionGeneration++;currentAssessment=null;report=null;batchData=null;csrfToken=undefined;account=undefined;showAuth();throw new Error("Your session needs refreshing. Sign in again.")}
    throw refreshError;
   }
   if(!account||active.id!==account.id){sessionGeneration++;currentAssessment=null;account=active;location.reload();throw new Error("Your signed-in account changed. The workspace is refreshing.")}
   throw new Error("Your security token was refreshed. Please submit once more; no assessment was created.")
  }
  throw error;
 }
}
function download(name,content,type="application/json"){
 const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement("a");a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function metric(label,value,sub=""){return `<div class="metric"><small>${esc(label)}</small><strong>${esc(value)}</strong><span class="sub">${esc(sub)}</span></div>`}
function riskMetric(level){const label=riskIndicator(level);return `<div class="metric riskmetric ${esc(label)}"><small>Risk indicator</small><strong><span class="chip ${esc(label)}">${esc(label)}</span></strong><span class="sub">Score category, not confirmed disease.</span></div>`}
function table(headers,rows){return `<div class="tablewrap"><table><thead><tr>${headers.map(h=>`<th scope="col">${esc(h)}</th>`).join("")}</tr></thead><tbody>${rows.map(cells=>`<tr>${cells.map(c=>`<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`}
function chip(value){return `<span class="chip ${["HIGH","LOW","MEDIUM","MODERATE","TP","TN","FP","FN"].includes(value)?value:""}">${esc(value)}</span>`}
function userFeatureLabel(feature){return USER_FEATURE_LABELS[feature]||meta?.features?.[feature]?.label||feature}
function visibleFeatureLabel(feature){return account?.role==="ADMIN"?meta.features[feature].label:userFeatureLabel(feature)}
function inputMarkup(key,definition,prefix="field",value=definition.default){
 const input=definition.options?`<select id="${prefix}-${key}" name="${key}" required>${Object.entries(definition.options).map(([v,label])=>`<option value="${v}" ${Number(value)===Number(v)?"selected":""}>${esc(label)}</option>`).join("")}</select>`:`<input id="${prefix}-${key}" name="${key}" type="number" min="${definition.min}" max="${definition.max}" step="${definition.step||1}" value="${Number(value)}" required>`;
 const userHelp=account?.role!=="ADMIN"&&USER_FEATURE_HELP[key]?`<small class="fieldhelp">${esc(USER_FEATURE_HELP[key])}</small>`:"";
 return `<label for="${prefix}-${key}">${esc(account?.role==="ADMIN"?definition.label:userFeatureLabel(key))} ${definition.unit?`<small>${esc(definition.unit)}</small>`:""}${input}${userHelp}</label>`;
}
function formValues(){return Object.fromEntries(meta.feature_order.map(k=>[k,Number($("field-"+k).value)]))}
function fillInputs(data){for(const key of meta.feature_order)$("field-"+key).value=data[key]}
function chart(points,label,diagonal=false){
 const left=42,top=15,width=258,height=175;
 const path=points.x.map((x,i)=>`${i?"L":"M"}${left+Number(x)*width},${top+height-Number(points.y[i])*height}`).join(" ");
 return `<svg class="chart" viewBox="0 0 320 225" role="img" aria-label="${esc(label)}">${[0,.25,.5,.75,1].map(t=>`<line class="grid" x1="${left}" y1="${top+height-t*height}" x2="300" y2="${top+height-t*height}"/><text x="33" y="${top+height-t*height+4}" text-anchor="end">${t}</text><text x="${left+t*width}" y="209" text-anchor="middle">${t}</text>`).join("")}${diagonal?`<line class="diagonal" x1="42" y1="190" x2="300" y2="15"/>`:""}<path class="line" d="${path}"/></svg>`;
}
function waterfall(explanation,labels={reference:"Reference prediction",final:"Final model estimate"}){
 if(explanation.status!=="available")return `<p class="notice warn">${esc(explanation.note||"Explanation unavailable.")}</p>`;
 const factors=[...explanation.factors].sort((a,b)=>Math.abs(b.shap_contribution)-Math.abs(a.shap_contribution));
 let value=explanation.base_value;const steps=factors.map(f=>{const from=value;value+=f.shap_contribution;return {...f,from,to:value}});
 const min=Math.min(0,explanation.base_value,...steps.map(x=>Math.min(x.from,x.to))),max=Math.max(1,explanation.base_value,...steps.map(x=>Math.max(x.from,x.to)));
 const position=v=>100*(v-min)/(max-min);
 const endpoint=(label,v)=>`<div class="waterfallrow"><span>${esc(label)}</span><div class="waterfalltrack"><i class="waterfallmarker" style="left:${position(v)}%"></i></div><strong>${pct(v)}</strong></div>`;
 return `${endpoint(labels.reference,explanation.base_value)}${steps.map(f=>{const label=labels.user?`${userFeatureLabel(f.feature)} — ${recordedValue(f.feature,labels.values)}`:f.label;const tiny=Math.abs(f.contribution_pp)<0.1;const contribution=tiny?"Less than 0.1 percentage point":`${f.contribution_pp>0?"+":""}${f.contribution_pp.toFixed(1)} percentage points`;return `<div class="waterfallrow"><span>${esc(label)}</span><div class="waterfalltrack"><div class="waterfallbar ${f.shap_contribution>0?"up":""}" style="left:${position(Math.min(f.from,f.to))}%;width:${100*Math.abs(f.shap_contribution)/(max-min)}%"></div></div><strong class="${tiny?"tiny":""}">${esc(contribution)}</strong></div>`}).join("")}${endpoint(labels.final,explanation.output_value)}`;
}
function recordedValue(feature, values){
 const definition=meta.features[feature],value=values[feature];
 const display=definition.options?.[value]??value;
 return `${display}${definition.unit?` ${definition.unit}`:""}`;
}
function selectedFactors(factors, direction){
 return factors.filter(f=>(direction>0?f.shap_contribution>0:f.shap_contribution<0)&&Math.abs(f.contribution_pp)>=0.005)
  .sort((a,b)=>direction>0?b.shap_contribution-a.shap_contribution:a.shap_contribution-b.shap_contribution)
  .slice(0,5);
}
function influenceGroups(explanation, values, user=false){
 if(!explanation||explanation.status!=="available")return `<p class="notice warn">${esc(explanation?.note||"Explanation temporarily unavailable.")}</p>`;
 const raised=selectedFactors(explanation.factors,1),lowered=selectedFactors(explanation.factors,-1);
 const shown=[...raised,...lowered],maximum=Math.max(...shown.map(f=>Math.abs(f.contribution_pp)),0);
 const render=(factors,raisedDirection)=>{
  const direction=raisedDirection?"higher":"lower";
  if(!factors.length)return `<p class="empty">No meaningful factors ${raisedDirection?"raised":"lowered"} ${user?"the score":"the model estimate"} for this assessment.</p>`;
  return `<div class="influence-list">${factors.map(f=>{const points=f.contribution_pp,percent=maximum?100*Math.abs(points)/maximum:0;const label=user?userFeatureLabel(f.feature):f.label;return `<article class="influence ${raisedDirection?"raised":"lowered"}"><div class="influence-head"><strong>${raisedDirection?"▲":"▼"} ${esc(label)}</strong><span>${points>0?"+":""}${points.toFixed(2)} percentage points</span></div><p><b>Recorded value:</b> ${esc(recordedValue(f.feature,values))}</p><div class="influence-track" aria-label="${esc(label)} ${raisedDirection?"raised":"lowered"} the ${user?"score":"estimate"} by ${points.toFixed(2)} percentage points"><i style="width:${percent}%"></i></div><p class="muted">Your recorded ${esc(label)} value contributed to a ${direction} ${user?"score":"model estimate"} for this assessment.</p></article>`}).join("")}</div>`;
 };
 const raisedTitle=user?"Raised your score":"Factors that raised the estimate";
 const loweredTitle=user?"Lowered your score":"Factors that lowered the estimate";
 return `<div class="influence-groups"><section><h3>${raisedTitle}</h3>${render(raised,true)}</section><section><h3>${loweredTitle}</h3>${render(lowered,false)}</section></div>`;
}
function recommendationCards(recommendations){
 if(!recommendations||recommendations.status!=="stored")return `<section class="card recommendation-section"><h2>General guidance, not a treatment plan.</h2><p class="muted">Recommendations were not stored with this assessment.</p></section>`;
 if(!recommendations.cards.length)return "";
 return `<section class="card recommendation-section"><h2>General guidance, not a treatment plan.</h2><div class="recommendation-grid">${recommendations.cards.map(card=>`<article class="recommendation-card"><h3>${esc(card.title||"Review your report")}</h3><p>${esc(card.explanation||"")}</p><p><strong>Next step:</strong> ${esc(card.next_step||"")}</p></article>`).join("")}</div></section>`;
}
function setFormCollapsed(collapsed){
 const card=$("assessmentFormCard");
 if(card)card.classList.toggle("completed",collapsed);
}function riskIndicator(level){return level==="MEDIUM"?"MODERATE":level}
function measurementCheck(support){
 if(!support||support.status!=="available")return `<div class="measurement-check unavailable"><strong>Measurement check</strong><span>Checks inputs, not disease status.</span><p>Check unavailable</p><small>${esc(support?.message||"The measurement check was not available for this assessment.")}</small></div>`;
 if(support.flagged)return `<div class="measurement-check flagged"><strong>Measurement check</strong><span>Checks inputs, not disease status.</span><p>Check entered measurements</p><small>${esc(support.message||"Some entered measurements differ from the examples used to train this model. Check the values you entered; the estimate may be less reliable.")}</small></div>`;
 return `<div class="measurement-check"><strong>Measurement check</strong><span>Checks inputs, not disease status.</span><p>No unusual inputs detected</p></div>`;
}function renderAssessment(data){
 if(account?.role!=="ADMIN")return renderUserAssessment(data);
 return renderAdminAssessment(data);
}
function renderUserAssessment(data){
 currentAssessment=data;setFormCollapsed(false);$("assessmentResult").classList.remove("hidden");
 const explanation=data.explanation||{status:"not_stored",factors:[],note:"Explanation was not stored for this assessment."};
 $("assessmentResult").innerHTML=`<div class="summarybar"><div><p class="eyebrow">SAVED ASSESSMENT ${data.assessment_id?"#"+Number(data.assessment_id):""}</p><h2>Your heart-health assessment</h2><p class="muted">${esc(data.created_at?`Saved ${new Date(data.created_at).toLocaleString()}`:"Assessment ready to save")}</p></div><div class="actions"><details class="report-control"><summary>Download report</summary><div><button id="downloadAssessment" class="secondary" type="button">Download JSON</button><button id="printAssessment" class="secondary" type="button">Print / save PDF</button></div></details></div></div><div class="metrics usermetrics">${metric("Assessment score",pct(data.probability),"An estimate based on your measurements.")}${riskMetric(data.risk_level)}</div><section class="card explanation-section"><h2>What influenced your assessment?</h2><div class="legend"><span><i class="up"></i>Raised your score</span><span><i></i>Lowered your score</span></div>${waterfall(explanation,{reference:"Starting score",final:"Assessment score",user:true,values:data.features})}</section>${recommendationCards(data.recommendations)}<section class="card"><details><summary>Your measurements</summary>${measurementCheck(data.input_support)}${table(["Measurement","Recorded value"],meta.feature_order.map(k=>[esc(userFeatureLabel(k)),esc(recordedValue(k,data.features))]))}</details></section><section class="card limitation"><p>For educational use. This assessment cannot confirm or rule out heart disease.</p></section>`;
 $("downloadAssessment").onclick=()=>download(`assessment-${data.assessment_id||"preview"}.json`,JSON.stringify(data,null,2));$("printAssessment").onclick=()=>window.print();
}function renderAdminAssessment(data){
 currentAssessment=data;$("assessmentResult").classList.remove("hidden");
 const support=data.input_support;
 $("assessmentResult").innerHTML=`<div class="summarybar"><div><p class="eyebrow">ASSESSMENT ${data.assessment_id?"#"+Number(data.assessment_id):""}</p><h2>Your model evidence</h2><p class="muted mono">${esc(data.model_version)} Â· ${esc(data.created_at?new Date(data.created_at).toLocaleString():"")}</p></div><div class="actions"><button id="downloadAssessment" class="secondary">Download JSON</button><button id="printAssessment" class="secondary">Print / save PDF</button></div></div>
 <p class="printonly">${esc(data.disclaimer)}</p>
 <div class="metrics">${metric("Estimated positive-class probability",pct(data.probability),data.prediction)}${metric("Exploratory score band",data.risk_level,"Display bands: <30%, 30â€“70%, â‰¥70%")}${metric("Candidate probability spread",pct(data.disagreement.probability_spread),data.disagreement.class_disagreement?"Class predictions disagree":"Class predictions agree")}${metric("Input support",support.flagged?"Review":"In range","Heuristic training-data comparison")}</div>
 <div class="twocol"><section class="card"><h2>Why this prediction?</h2><p class="muted">SHAP contributions in percentage points (pp).</p><div class="legend"><span><i class="up"></i>Raises model output</span><span><i></i>Lowers model output</span></div>${influenceGroups(data.explanation,data.features,false)}${waterfall(data.explanation)}<p class="muted">${esc(data.explanation.note||"")}</p><details><summary>Explanation method</summary><p>${esc(data.explanation.method||"Unavailable")}.</p><p>The bars accumulate from the reference prediction to the final estimate. SHAP describes the model, not causes of disease.</p></details></section>
 <section class="card"><h2>Do the models agree?</h2><p class="muted">Uncalibrated candidate pipelines Â· threshold 0.5</p>${table(["Model","Probability","Class"],data.model_comparison.map(m=>[esc(m.model),pct(m.probability),m.prediction?"Positive":"Negative"]))}<p class="notice ${data.disagreement.class_disagreement?"warn":""}" style="margin-top:18px">${esc(data.disagreement.note)}</p><h3>Training-data support</h3><p>${support.flagged?"This combination deserves additional scrutiny against the training reference data.":"No flag from the implemented distance and range checks. This does not establish reliability."}</p><p class="muted">Nearest distance: ${num(support.nearest_distance)} Â· training 95th percentile: ${num(support.training_distance_95)}</p>${support.outside_training_range.length?table(["Feature","Input","Training range"],support.outside_training_range.map(f=>[esc(meta.features[f.feature].label),esc(f.value),`${f.training_min}â€“${f.training_max}`])):""}<small>${esc(support.note)}</small></section></div>
 <section class="card"><h2>Measurements behind this assessment</h2>${table(["Feature","Recorded value"],meta.feature_order.map(k=>[esc(meta.features[k].label),esc(meta.features[k].options?.[data.features[k]]??data.features[k])+(meta.features[k].unit?" "+esc(meta.features[k].unit):"")]))}</section>
 <section class="card"><h2>Similar training references</h2><p class="muted">Anonymized public dataset rows. Similarity supplies context, not confirmation of an individual result.</p>${data.similar_cases.map(c=>`<details><summary>${esc(c.reference)} Â· distance ${num(c.distance)} Â· recorded label ${c.recorded_label}</summary>${table(["Feature","Reference","This assessment"],meta.feature_order.map(k=>[esc(meta.features[k].label),esc(c.features[k]),esc(data.features[k])]))}</details>`).join("")}</section>
 <section class="card simulation"><h2>What if the measurements differed?</h2><p class="notice warn">Model sensitivity only. These hypothetical changes are not treatment targets or estimates of treatment benefit.</p><form id="simulationForm"><div class="simgrid">${["trestbps","chol","thalach","oldpeak"].map(k=>inputMarkup(k,meta.features[k],"sim",data.features[k])).join("")}</div><div class="formfoot"><small>Age and categorical features are held fixed. No history record is created.</small><button id="simulateButton" type="submit">Compare scenario</button></div></form><div id="simulationResult"></div></section>`;
 $("downloadAssessment").onclick=()=>download(`assessment-${data.assessment_id||"preview"}.json`,JSON.stringify(data,null,2));
 $("printAssessment").onclick=()=>window.print();
 $("simulationForm").onsubmit=event=>{event.preventDefault();busy($("simulateButton"),async()=>{const modified={...data.features};for(const k of ["trestbps","chol","thalach","oldpeak"])modified[k]=Number($("sim-"+k).value);const result=await jsonPost("/api/simulate",{original:data.features,modified});$("simulationResult").innerHTML=`<div class="minimetrics"><div><small>Original estimate</small><b>${pct(result.original_probability)}</b></div><div><small>Scenario estimate</small><b>${pct(result.modified.probability)}</b></div><div><small>Model output change</small><b>${result.delta_pp>0?"+":""}${result.delta_pp.toFixed(1)} pp</b></div></div><p>${esc(result.note)}</p>${result.modified.input_support.flagged?'<p class="notice warn">The scenario triggered an input-support flag.</p>':""}`})};
}
function matrix(m){const a=m.confusion_matrix;return `<div class="matrix"><div>True negatives<b>${a[0][0]}</b>Actual 0 / predicted 0</div><div class="errorcell">False positives<b>${a[0][1]}</b>Actual 0 / predicted 1</div><div class="errorcell">False negatives<b>${a[1][0]}</b>Actual 1 / predicted 0</div><div>True positives<b>${a[1][1]}</b>Actual 1 / predicted 1</div></div>`}
async function loadEvaluation(){
 const generation=sessionGeneration;report=report||await sessionApi("/api/evaluation",{},generation);const m=report.active_test,ci=report.test_intervals;
 $("evaluationContent").innerHTML=`<p class="notice">${esc(report.selection)}</p><p class="notice warn">${esc(report.evaluation_caveat)}</p><div class="metrics">${metric("Internal test accuracy",pct(m.accuracy),`95% bootstrap interval ${pct(ci.accuracy.low)}â€“${pct(ci.accuracy.high)}`)}${metric("Internal test ROC-AUC",num(m.roc_auc),`${num(ci.roc_auc.low)}â€“${num(ci.roc_auc.high)} interval`)}${metric("Sensitivity / recall",pct(m.recall),`${m.confusion_matrix[1][0]} false negatives at threshold 0.5`)}${metric("Brier score",num(m.brier),"Lower is better; probability error")}</div>
 <section class="card"><h2>Candidate comparison</h2><p class="muted">${report.dataset.train_count} training records Â· 5 stratified validation folds Â· ${m.n} internal test records</p>${table(["Candidate","CV AUC mean Â± SD","OOF Brier","Test accuracy","Test AUC"],Object.entries(report.candidates).map(([name,v])=>[esc(name)+(name===report.selected_model?' <span class="chip">Selected</span>':""),`${num(v.cv_roc_auc_mean)} Â± ${num(v.cv_roc_auc_std)}`,num(v.cv.brier),pct(v.test.accuracy),num(v.test.roc_auc)]))}<p class="muted" style="margin-top:15px">Sigmoid calibration ${report.calibrated?"accepted":"not applied"}. Nested OOF Brier: ${num(report.calibration_selection.uncalibrated_oof_brier)} uncalibrated / ${num(report.calibration_selection.calibrated_oof_brier)} calibrated.</p></section>
 <div class="threecol"><section class="card"><h2>ROC curve</h2>${chart(report.curves.roc,"ROC curve: false positive rate vs true positive rate",true)}<small>X: false positive rate Â· Y: true positive rate</small></section><section class="card"><h2>Precisionâ€“recall</h2>${chart(report.curves.precision_recall,"Precision recall curve")}<small>X: recall Â· Y: precision Â· AP ${num(m.average_precision)}</small></section><section class="card"><h2>Calibration</h2>${chart(report.curves.calibration,"Calibration curve: predicted vs observed fraction",true)}<small>X: mean probability Â· Y: observed fraction<br>Six quantile bins; small test sample.</small></section></div>
 <div class="twocol"><section class="card"><h2>Internal test confusion matrix</h2><p class="muted">Fixed deployment threshold: 0.5</p>${matrix(m)}<p>Precision ${pct(m.precision)} Â· specificity ${pct(m.specificity)} Â· F1 ${num(m.f1)}</p></section>
 <section class="card"><h2>Explore the decision threshold</h2><p class="muted">Uses training out-of-fold predictions. The deployed threshold remains 0.5.</p><label class="rangehead" for="thresholdSlider">Classification threshold<strong id="thresholdValue">0.50</strong></label><input id="thresholdSlider" type="range" min=".01" max=".99" step=".01" value=".5"><div id="thresholdResult" aria-live="polite"></div><small>Exploratory threshold reaching â‰¥90% OOF recall: ${report.exploratory_recall_90_threshold?.toFixed(2)??"not available"}. This is not a clinical recommendation.</small></section></div>
 <section class="card"><div class="sectionhead"><div><h2>Global feature influence</h2><p>Test-set permutation importance: decrease in ROC-AUC when one feature is shuffled.</p></div><button id="globalShapButton" class="secondary">Compute global SHAP</button></div>${table(["Feature","Mean AUC decrease","Shuffle SD"],report.global_importance.map(f=>[esc(meta.features[f.feature].label),num(f.mean),num(f.std)]))}<div id="globalShapResult"></div></section>
 <section class="card"><h2>Inspect errors</h2><p class="muted">Every internal test false positive and false negative at 0.5. Opening a case fills the assessment form; it does not save a prediction.</p>${table(["Dataset row","Actual label","Probability","Outcome","Inspect"],report.test_cases.filter(c=>c.outcome==="FN"||c.outcome==="FP").map(c=>[String(c.row_id),String(c.actual),pct(c.probability),chip(c.outcome),`<button class="secondary caseButton" data-row="${c.row_id}">Load inputs</button>`]))}</section>
 <section class="card"><h2>Exploratory subgroup results</h2><p class="notice warn">Small groups produce unstable estimates. These comparisons do not establish fairness or clinical validity.</p>${table(["Group","N","Accuracy","Recall","Specificity","AUC"],report.subgroups.map(s=>[esc(s.group),String(s.n)+(s.small_sample?" Â· small":""),pct(s.accuracy),pct(s.recall),pct(s.specificity),num(s.roc_auc)]))}</section>`;
 $("thresholdSlider").oninput=()=>{const value=Number($("thresholdSlider").value);$("thresholdValue").textContent=value.toFixed(2);clearTimeout(thresholdTimer);const sequence=++thresholdSequence;thresholdTimer=setTimeout(()=>loadThreshold(value,sequence).catch(showError),180)};
 await loadThreshold(.5,++thresholdSequence);
 document.querySelectorAll(".caseButton").forEach(b=>b.onclick=()=>{const c=report.test_cases.find(x=>x.row_id===Number(b.dataset.row));fillInputs(c.features);switchTab("assessment");$("assessmentResult").classList.add("hidden");currentAssessment=null;window.scrollTo({top:0,behavior:"smooth"})});
 $("globalShapButton").onclick=()=>busy($("globalShapButton"),async()=>{const d=await sessionApi("/api/global-shap");$("globalShapResult").innerHTML=`<h3 style="margin-top:24px">Global SHAP Â· ${d.n} fixed training reference cases</h3><p class="muted">Mean absolute probability contribution; magnitude, not direction.</p>${table(["Feature","Mean |SHAP| (pp)"],d.factors.map(f=>[esc(f.label),(f.mean_absolute_contribution*100).toFixed(2)]))}`});
}
async function loadThreshold(value,sequence){const d=await sessionApi(`/api/threshold?value=${value}`);if(sequence!==thresholdSequence)return;const m=d.metrics;$("thresholdResult").innerHTML=`<div class="minimetrics"><div><small>Recall</small><b>${pct(m.recall)}</b></div><div><small>Precision</small><b>${pct(m.precision)}</b></div><div><small>Specificity</small><b>${pct(m.specificity)}</b></div></div>${matrix(m)}`}
async function loadData(){report=report||await api("/api/evaluation");const d=report.dataset;const v=await api("/api/versions");$("dataContent").innerHTML=`<div class="metrics">${metric("Complete-case records",d.rows,"13 input features + binary target")}${metric("Training / internal test",`${d.train_count} / ${d.test_count}`,`Stratified split Â· seed ${report.seed}`)}${metric("Positive / negative labels",`${d.positive_count} / ${d.negative_count}`,"Recorded disease-presence label")}${metric("Duplicate rows removed",d.duplicates_removed,`${d.missing_values} missing cells in cleaned data`)}</div><section class="card"><h2>Dataset provenance</h2><p><a href="${esc(d.source)}" target="_blank" rel="noopener">UCI Heart Disease dataset â†—</a></p><p>The original preprocessing removes records with missing values and maps disease labels 1â€“4 to 1. The cleaned file contains ${d.raw_rows} records before exact deduplication. Complete-case exclusion can introduce selection bias.</p><p class="mono">SHA-256: ${esc(d.sha256)}</p><h3>Training reference ranges</h3>${table(["Feature","Minimum","Median","Maximum"],meta.feature_order.map(k=>{const s=report.feature_statistics[k];return [esc(meta.features[k].label),esc(s.min),esc(s.median),esc(s.max)]}))}</section><section class="card"><h2>Saved model versions</h2><p class="muted">${esc(v.note)}</p>${table(["Version","Model","Calibration","Test accuracy","Test AUC"],v.versions.map(x=>[esc(x.version)+(x.version===v.active?' <span class="chip">Active</span>':""),esc(x.selected_model),x.calibrated?"Sigmoid":"None",pct(x.active_test.accuracy),num(x.active_test.roc_auc)]))}<details><summary>Training environment</summary><pre>${esc(JSON.stringify(report.environment,null,2))}</pre></details></section><section class="card"><h2>What the evidence does not establish</h2><ul class="factorlist">${report.limitations.map(s=>`<li>${esc(s)}</li>`).join("")}</ul><button id="downloadEvaluation" class="secondary" style="margin-top:18px">Download evaluation JSON</button></section>`;$("downloadEvaluation").onclick=()=>download("model-evaluation.json",JSON.stringify(report,null,2))}
async function loadHistory(){const d=await sessionApi(`/api/history?skip=${historySkip}&limit=20&band=${encodeURIComponent($("historyBand").value)}`);historyTotal=d.total;const admin=account.role==="ADMIN";const headers=admin?["ID","Saved","Probability","Band","Model version",""]:["ID","Saved","Assessment score","Risk indicator",""];const rows=d.items.map(x=>admin?[String(x.id),esc(new Date(x.created_at).toLocaleString()),pct(x.probability),chip(x.risk_level),esc(x.model_version),`<button class="secondary openAssessment" data-id="${x.id}">Open</button>`]:[String(x.id),esc(new Date(x.created_at).toLocaleString()),pct(x.probability),chip(riskIndicator(x.risk_level)),`<button class="secondary openAssessment" data-id="${x.id}">Open</button>`]);$("historyContent").innerHTML=d.items.length?table(headers,rows):'<p class="empty">No saved assessments in this view. Run an assessment to create one.</p>';$("historyPage").textContent=d.total?`${historySkip+1}–${Math.min(historySkip+20,d.total)} of ${d.total}`:"0 records";$("previousPage").disabled=historySkip===0;$("nextPage").disabled=historySkip+20>=d.total;document.querySelectorAll(".openAssessment").forEach(b=>b.onclick=()=>busy(b,async()=>{const record=await sessionApi(`/api/history/${b.dataset.id}`);fillInputs(record.features);renderAssessment(record);switchTab("assessment");$("assessmentResult").scrollIntoView({behavior:"smooth"})}))}async function switchTab(name){document.querySelectorAll(".tab").forEach(t=>t.classList.toggle("hidden",t.id!=="tab-"+name));document.querySelectorAll("nav button").forEach(b=>{b.classList.toggle("active",b.dataset.tab===name);if(b.dataset.tab===name)b.setAttribute("aria-current","page");else b.removeAttribute("aria-current")});$("pageName").textContent={assessment:"Assessment",evaluation:"Model evaluation",data:"Data & versions",batch:"Batch analysis",history:"Saved assessments"}[name];try{if(name==="evaluation")await loadEvaluation();if(name==="data")await loadData();if(name==="history")await loadHistory()}catch(e){showError(e)}}
function showAuth(){
 document.querySelector(".sidebar").classList.add("hidden");document.querySelector("main").classList.add("hidden");$("authScreen").classList.remove("hidden");
 const setMode=register=>{$("loginForm").classList.toggle("hidden",register);$("registerForm").classList.toggle("hidden",!register)};
 $("showLogin").onclick=()=>setMode(false);$("showRegister").onclick=()=>setMode(true);
 $("loginForm").onsubmit=e=>{e.preventDefault();busy(e.target.querySelector("button"),async()=>{account=await jsonPost("/api/auth/login",{email:$("loginEmail").value,password:$("loginPassword").value});csrfToken=account.csrf_token;await startWorkspace()})};
 $("registerForm").onsubmit=e=>{e.preventDefault();busy(e.target.querySelector("button"),async()=>{account=await jsonPost("/api/auth/register",{email:$("registerEmail").value,display_name:$("registerName").value,password:$("registerPassword").value});csrfToken=account.csrf_token;await startWorkspace()})};
}
function configureAccess(){
 $("authScreen").classList.add("hidden");document.querySelector(".sidebar").classList.remove("hidden");document.querySelector("main").classList.remove("hidden");
 $("accountLabel").textContent=`${account.display_name} Â· ${account.role}`;const admin=account.role==="ADMIN";
 document.querySelectorAll("nav button").forEach(button=>{if(["evaluation","data","batch"].includes(button.dataset.tab))button.classList.toggle("hidden",!admin)});
 const link=document.createElement("a");link.href="/admin/docs";link.target="_blank";link.rel="noopener";link.textContent="Admin API docs â†—";link.className=admin?"":"hidden";document.querySelector(".sidefoot").append(link);
 const logout=document.createElement("button");logout.className="secondary";logout.textContent="Sign out";logout.onclick=async()=>{sessionGeneration++;currentAssessment=null;report=null;batchData=null;try{await api("/api/auth/logout",{method:"POST",headers:{"X-CSRF-Token":csrfToken}})}finally{location.reload()}};document.querySelector(".sidefoot").append(logout);
}
function configureUserCopy(){
 const user=account?.role!=="ADMIN";
 $("workspaceLabel").textContent=user?"YOUR PRIVATE WORKSPACE":"RESEARCH WORKSPACE";
 $("workspaceCrumb").innerHTML=user?"Heart-health assessment / <b id=\"pageName\">Assessment</b>":"Cardiovascular ML / <b id=\"pageName\">Assessment</b>";
 if(!user)return;
 $("assessmentEyebrow").textContent="YOUR RECORDED MEASUREMENTS";
 $("assessmentTitle").textContent="Your heart-health assessment";
 $("assessmentLead").textContent="Enter recorded measurements to see your assessment score and what influenced it.";
 $("assessmentTag").textContent="13 measurements";
 $("assessmentNotice").textContent="Use recorded report values. Do not guess specialized test measurements.";
 $("measurementsHeading").textContent="Your measurements";
 $("measurementsLead").textContent="Use the values recorded in the report. The prefilled example is demonstration data.";
 $("inputEncodingNote").textContent="All 13 measurements are required.";
 $("assessButton").innerHTML="Get assessment <span>↗</span>";
 $("historyEyebrow").textContent="REVIEW YOUR SAVED RESULTS";
 $("historyTitle").textContent="Your saved assessments";
 $("historyLead").textContent="Reopen the measurements and result saved with each assessment.";
 $("historyBandLabel").firstChild.nodeValue="Risk indicator ";$("historyBand").querySelector("option[value=MEDIUM]").textContent="MODERATE";
 $("legacyHistoryNote").classList.add("hidden");
}
async function startWorkspace(){
 sessionGeneration++;
 configureAccess();
 try{meta=await api("/api/meta");$("modelStatus").textContent=account.role==="ADMIN"?(meta.selected_model+(meta.calibrated?" · calibrated":" · active")):"Signed in";configureUserCopy();$("featureForm").innerHTML=meta.feature_order.map(k=>inputMarkup(k,meta.features[k])).join("")}catch(e){$("modelStatus").textContent="Unavailable";$("assessButton").disabled=true;showError(e);return} document.querySelectorAll("nav button").forEach(b=>b.onclick=()=>switchTab(b.dataset.tab));
 $("resetExample").onclick=()=>{fillInputs(Object.fromEntries(meta.feature_order.map(k=>[k,meta.features[k].default])));$("assessmentResult").classList.add("hidden");setFormCollapsed(false);currentAssessment=null};
 $("assessmentForm").onsubmit=event=>{event.preventDefault();busy($("assessButton"),async()=>{const data=await jsonPost("/api/predict",formValues());renderAssessment(data);$("assessmentResult").scrollIntoView({behavior:"smooth",block:"start"})})};
 $("templateButton").onclick=()=>download("assessment-template.csv",meta.feature_order.join(",")+"\n"+meta.feature_order.map(k=>meta.features[k].default).join(",")+"\n","text/csv");
 $("batchForm").onsubmit=event=>{event.preventDefault();busy($("batchButton"),async()=>{const f=$("csvFile").files[0];if(!f)throw new Error("Choose a CSV file first.");if(f.size>1000000)throw new Error("CSV must be under 1 MB.");batchData=await api("/api/batch",{method:"POST",headers:{"Content-Type":"text/csv","X-CSRF-Token":csrfToken},body:await f.text()});$("batchResult").innerHTML=`<div class="sectionhead" style="margin-top:24px"><h3>${batchData.valid} valid / ${batchData.count} total records</h3><button id="downloadBatch" class="secondary">Download results CSV</button></div>${table(["CSV line","Status","Probability","Model class","Input support","Details"],batchData.results.map(x=>[String(x.row),esc(x.status),pct(x.probability),esc(x.prediction||"â€”"),x.status==="ok"?(x.unusual_input?"Review":"No flag"):"â€”",x.errors?esc(x.errors.map(e=>`${e.field}: ${e.message}`).join("; ")):(x.model_disagreement?"Candidates disagree":"Candidates agree")]))}`;$("downloadBatch").onclick=()=>{const headers=["row","status","probability","prediction","risk_level","unusual_input","model_disagreement","error","model_version"];const cell=v=>'"'+String(v??"").replace(/^[=+@-]/,"'$&").replace(/"/g,'""')+'"';const lines=batchData.results.map(x=>[x.row,x.status,x.probability,x.prediction,x.risk_level,x.unusual_input,x.model_disagreement,x.errors?.map(e=>`${e.field}: ${e.message}`).join("; "),batchData.model_version].map(cell).join(","));download("batch-results.csv",headers.join(",")+"\n"+lines.join("\n"),"text/csv")}})};
 $("refreshHistory").onclick=()=>loadHistory().catch(showError);$("historyBand").onchange=()=>{historySkip=0;loadHistory().catch(showError)};
 $("previousPage").onclick=()=>{historySkip=Math.max(0,historySkip-20);loadHistory().catch(showError)};$("nextPage").onclick=()=>{historySkip+=20;loadHistory().catch(showError)};
}
async function init(){
 try{csrfToken=(await api("/api/auth/csrf")).csrf_token;account=await api("/api/auth/me")}catch(e){showAuth();return}
 await startWorkspace();
}
init();
