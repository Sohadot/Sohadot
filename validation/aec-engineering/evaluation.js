"use strict";
/* AEC-UAT-ENG-001: client-only voluntary engineer feedback.
   No network submission, analytics, or browser storage. */
(function(){
  const form=document.getElementById("evaluation");if(!form)return;
  const stages=Array.from(form.querySelectorAll(".stage"));
  const names=["Reviewer context","Electrical redundancy","Formal acceptance","Access boundaries","Professional evaluation","Review and export"];
  const status=document.getElementById("form-status"),exportStatus=document.getElementById("export-status");
  let current=0;
  const selected=name=>{const n=form.querySelector('input[name="'+name+'"]:checked');return n?n.value:null;};
  const note=name=>{const n=form.elements.namedItem(name);return n&&typeof n.value==="string"?n.value.trim():"";};
  function report(){
    const ratings={};
    ["terminology","boundaries","document_requests","ease_of_use","export_utility","professional_value"].forEach(k=>{
      const v=selected("rating_"+k);ratings[k]=v?Number(v):null;
    });
    return {
      format:"sohadot-aec-engineering-evaluation",protocol:"AEC-UAT-ENG-001",format_version:"1.0.0",
      generated_at_utc:new Date().toISOString(),
      context:{specialization:selected("role"),experience_range:selected("experience"),prior_tool_exposure:selected("prior_exposure")},
      tasks:{
        electrical_redundancy_rc03:{completion:selected("power_completion"),observation:note("power_observation")},
        formal_acceptance_rc12:{completion:selected("acceptance_completion"),distinction_observed:selected("acceptance_distinction")},
        regulatory_access_rc15:{completion:selected("access_completion"),appropriate_boundary_observed:selected("access_boundary")}
      },
      evaluation:{ratings_1_to_5:ratings,potentially_misleading_wording:selected("issue_flag"),
        issue_detail:selected("issue_flag")==="yes"?note("issue_text"):"",
        professional_intent:selected("professional_intent"),suggested_improvement:note("improvement")},
      boundaries:{respondent_self_reported:true,tool_activity_observed_by_survey:false,
        engineering_or_scientific_review_certified:false,evidence_state_established:null,
        records_examined_by_sohadot:false,
        transmission:"No submission; the participant may explicitly export or compose a separate email."}
    };
  }
  function summary(r){
    const t=r.tasks,e=r.evaluation;
    return [
      "AEC-UAT-ENG-001 | Voluntary self-reported engineering evaluation",
      "Specialization: "+(r.context.specialization||"not supplied"),
      "Experience: "+(r.context.experience_range||"not supplied"),
      "Previously used tool: "+(r.context.prior_tool_exposure||"not supplied"),
      "",
      "TASKS",
      "rc-03 electrical redundancy: "+(t.electrical_redundancy_rc03.completion||"not supplied"),
      "rc-12 formal acceptance: "+(t.formal_acceptance_rc12.completion||"not supplied"),
      "  Distinction observed: "+(t.formal_acceptance_rc12.distinction_observed||"not supplied"),
      "rc-15 access: "+(t.regulatory_access_rc15.completion||"not supplied"),
      "  Boundary observed: "+(t.regulatory_access_rc15.appropriate_boundary_observed||"not supplied"),
      "",
      "RATINGS (1=poor, 5=excellent; unselected=not assessed)",
      ...Object.entries(e.ratings_1_to_5).map(([k,v])=>k+": "+(v===null?"—":v+"/5")),
      "Potentially misleading wording: "+(e.potentially_misleading_wording||"not supplied"),
      "Would use professionally: "+(e.professional_intent||"not supplied"),
      "",
      "Electrical-task observation: "+(t.electrical_redundancy_rc03.observation||"—"),
      "Specific concern: "+(e.issue_detail||"—"),
      "Suggested improvement: "+(e.suggested_improvement||"—"),
      "",
      "No engineering assessment or certification is produced.",
      "Nothing has been transmitted to Sohadot."
    ].join("\n");
  }
  function render(i){
    current=i;stages.forEach((n,j)=>{n.hidden=j!==i;});
    document.getElementById("step-count").textContent="Step "+(i+1)+" of "+stages.length;
    document.getElementById("step-name").textContent=names[i];
    document.getElementById("progress-fill").style.width=String(Math.round((i+1)/stages.length*100))+"%";
    status.textContent="";
    if(i===stages.length-1)document.getElementById("report-preview").textContent=summary(report());
    const heading=stages[i].querySelector("h2");if(heading)heading.focus({preventScroll:true});
    window.scrollTo(0,0);
  }
  function invalid(stage){
    for(const f of stage.querySelectorAll("fieldset[data-required-group]"))
      if(!f.querySelector('input[type="radio"]:checked'))return f.querySelector("input");
    if(current===4&&selected("issue_flag")==="yes"&&!note("issue_text"))
      return document.getElementById("issue_text");
    return null;
  }
  function issueVisibility(){
    const open=selected("issue_flag")==="yes";
    document.getElementById("issue-detail").hidden=!open;
    document.getElementById("issue_text").required=open;
  }
  document.querySelectorAll("[data-rating]").forEach(host=>{
    const key=host.getAttribute("data-rating");
    [1,2,3,4,5].forEach(v=>{
      const label=document.createElement("label"),input=document.createElement("input");
      input.type="radio";input.name="rating_"+key;input.value=String(v);
      input.setAttribute("aria-label",String(v)+" out of five");
      label.appendChild(input);label.appendChild(document.createTextNode(String(v)));host.appendChild(label);
    });
  });
  form.addEventListener("change",e=>{if(e.target.name==="issue_flag")issueVisibility();status.textContent="";});
  form.addEventListener("submit",e=>e.preventDefault());
  stages.forEach((s,i)=>{
    const next=s.querySelector(".next"),back=s.querySelector(".back");
    if(next)next.addEventListener("click",()=>{
      const target=invalid(s);
      if(target){status.textContent="Please answer the required choices. If you could not test, select that option.";target.focus();return;}
      render(Math.min(stages.length-1,i+1));
    });
    if(back)back.addEventListener("click",()=>render(Math.max(0,i-1)));
  });
  function download(ext,type,content){
    const blob=new Blob([content],{type}),url=URL.createObjectURL(blob),a=document.createElement("a");
    a.href=url;a.download="sohadot-aec-uat-eng-001."+ext;
    document.body.appendChild(a);a.click();a.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function csvCell(value){
    let s=value===null||value===undefined?"":String(value);
    if(/^[=+\-@\t\r]/.test(s))s="'"+s;
    return '"'+s.replace(/"/g,'""')+'"';
  }
  function csv(r){
    const rows=[["section","field","value"]];
    function flatten(value,parts){
      if(value&&typeof value==="object"&&!Array.isArray(value)){
        Object.keys(value).forEach(k=>flatten(value[k],parts.concat(k)));
      }else rows.push([parts[0],parts.slice(1).join("."),value]);
    }
    flatten(r,[]);
    return rows.map(row=>row.map(csvCell).join(",")).join("\r\n")+"\r\n";
  }
  document.getElementById("export-json").addEventListener("click",()=>{
    download("json","application/json;charset=utf-8",JSON.stringify(report(),null,2)+"\n");
    exportStatus.textContent="JSON prepared for download. Nothing was submitted.";
  });
  document.getElementById("export-csv").addEventListener("click",()=>{
    download("csv","text/csv;charset=utf-8",csv(report()));
    exportStatus.textContent="CSV prepared for download. Nothing was submitted.";
  });
  document.getElementById("copy-summary").addEventListener("click",async()=>{
    if(!navigator.clipboard||!navigator.clipboard.writeText){
      exportStatus.textContent="Clipboard unavailable; download the report instead.";return;
    }
    try{await navigator.clipboard.writeText(summary(report()));exportStatus.textContent="Summary copied locally, not submitted.";}
    catch(_){exportStatus.textContent="Clipboard denied; download the report instead.";}
  });
  document.getElementById("compose-email").addEventListener("click",()=>{
    const r=report(),subject="AEC-UAT-ENG-001 — Voluntary engineering evaluation";
    const body=[
      "AEC-UAT-ENG-001 voluntary engineering evaluation",
      "Specialization: "+(r.context.specialization||"not supplied"),
      "rc-03: "+(r.tasks.electrical_redundancy_rc03.completion||"not supplied"),
      "rc-12: "+(r.tasks.formal_acceptance_rc12.completion||"not supplied"),
      "rc-15: "+(r.tasks.regulatory_access_rc15.completion||"not supplied"),
      "Technical concern: "+(r.evaluation.potentially_misleading_wording||"not supplied"),
      "Professional use: "+(r.evaluation.professional_intent||"not supplied"),
      "",
      "Please attach the downloaded JSON report if you choose to share full answers.",
      "Sending is voluntary; no confidential records or site identifiers are requested."
    ].join("\n");
    exportStatus.textContent="Opening a draft only. You choose whether to send it.";
    window.location.href="mailto:agent@sohadot.com?subject="+encodeURIComponent(subject)+"&body="+encodeURIComponent(body);
  });
  document.getElementById("reset").addEventListener("click",()=>{
    if(!window.confirm("Clear every answer from this tab?"))return;
    form.reset();issueVisibility();exportStatus.textContent="";render(0);
  });
  issueVisibility();render(0);
})();
