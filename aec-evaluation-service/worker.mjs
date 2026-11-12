/* Sohadot AEC-UAT-ENG-001 private collection service.
 * Public writes: consent + Cloudflare Turnstile + strict schema + origin check.
 * Admin reads: Cloudflare Access RS256 JWT verified server-side; no public read.
 * No IP, email, token, or challenge data stored. Separate D1 from Hoax.ai.
 */
const protocol="AEC-UAT-ENG-001";
const states={
 role:["electrical_engineering","data_center_operations","network_or_systems","technical_due_diligence","other_or_undisclosed"],
 experience:["0_2","3_5","6_10","over_10","undisclosed"],
 exposure:["yes","no","unsure"],
 completion:["completed","partial","not_completed","not_attempted"],
 distinction:["clear","partial","unclear","not_assessed"],
 access:["yes","partly","no","not_assessed"],
 issue:["yes","no","unsure"],
 intent:["yes","with_improvements","no","unsure"]
};
const ratingNames=["terminology","boundaries","document_requests","ease_of_use","export_utility","professional_value"];
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const fixedOrigin="https://sohadot.com";
const maxBody=9000;
const noCache={"Cache-Control":"no-store, max-age=0","X-Content-Type-Options":"nosniff","Referrer-Policy":"no-referrer","X-Frame-Options":"DENY"};
function cors(origin){return origin===fixedOrigin?{"Access-Control-Allow-Origin":fixedOrigin,"Access-Control-Allow-Methods":"GET, POST, OPTIONS","Access-Control-Allow-Headers":"Content-Type","Access-Control-Max-Age":"300","Vary":"Origin"}:{};}
function json(x,status=200,origin){return new Response(JSON.stringify(x),{status,headers:{"Content-Type":"application/json; charset=utf-8",...noCache,...cors(origin)}});}
function fail(error,status=400,origin){return json({error},status,origin);}
function choice(v,options,optional=false){return (optional&&v===null)||typeof v==="string"&&options.includes(v);}
function shortText(v,max){return typeof v==="string"&&v.length<=max&&!/[\u0000-\u001f\u007f]/.test(v);}
function requireKeys(obj,keys){return !!obj&&!Array.isArray(obj)&&typeof obj==="object"&&Object.keys(obj).every(k=>keys.includes(k))&&keys.every(k=>Object.hasOwn(obj,k));}
function normalize(raw){
 if(!requireKeys(raw,["format","protocol","format_version","generated_at_utc","context","tasks","evaluation","boundaries"]))throw Error("schema");
 if(raw.format!=="sohadot-aec-engineering-evaluation"||raw.protocol!==protocol||raw.format_version!=="1.0.0")throw Error("protocol");
 const c=raw.context,t=raw.tasks,e=raw.evaluation;
 if(!requireKeys(c,["specialization","experience_range","prior_tool_exposure"])||
    !choice(c.specialization,states.role)||!choice(c.experience_range,states.experience,true)||
    !choice(c.prior_tool_exposure,states.exposure))throw Error("context");
 if(!requireKeys(t,["electrical_redundancy_rc03","formal_acceptance_rc12","regulatory_access_rc15"]))throw Error("tasks");
 const power=t.electrical_redundancy_rc03,accept=t.formal_acceptance_rc12,access=t.regulatory_access_rc15;
 if(!requireKeys(power,["completion","observation"])||!choice(power.completion,states.completion)||!shortText(power.observation,600)||
    !requireKeys(accept,["completion","distinction_observed"])||!choice(accept.completion,states.completion)||!choice(accept.distinction_observed,states.distinction)||
    !requireKeys(access,["completion","appropriate_boundary_observed"])||!choice(access.completion,states.completion)||!choice(access.appropriate_boundary_observed,states.access))throw Error("task-details");
 if(!requireKeys(e,["ratings_1_to_5","potentially_misleading_wording","issue_detail","professional_intent","suggested_improvement"])||
    !requireKeys(e.ratings_1_to_5,ratingNames)||!ratingNames.every(k=>e.ratings_1_to_5[k]===null||Number.isInteger(e.ratings_1_to_5[k])&&e.ratings_1_to_5[k]>=1&&e.ratings_1_to_5[k]<=5)||
    !choice(e.potentially_misleading_wording,states.issue)||!shortText(e.issue_detail,900)||!shortText(e.suggested_improvement,700)||
    !choice(e.professional_intent,states.intent)||e.potentially_misleading_wording==="yes"&&!e.issue_detail.trim())throw Error("feedback");
 if(!requireKeys(raw.boundaries,["respondent_self_reported","tool_activity_observed_by_survey","engineering_or_scientific_review_certified","evidence_state_established","records_examined_by_sohadot","transmission"])||
    raw.boundaries.respondent_self_reported!==true||raw.boundaries.tool_activity_observed_by_survey!==false||
    raw.boundaries.engineering_or_scientific_review_certified!==false||raw.boundaries.evidence_state_established!==null||
    raw.boundaries.records_examined_by_sohadot!==false)throw Error("evidence");
 // Reconstruct server-owned fields; client cannot inject metadata, state claims, or extra attributes.
 return {
  protocol,format_version:"1.0.0",
  context:{specialization:c.specialization,experience_range:c.experience_range,prior_tool_exposure:c.prior_tool_exposure},
  tasks:{
   electrical_redundancy_rc03:{completion:power.completion,observation:power.observation},
   formal_acceptance_rc12:{completion:accept.completion,distinction_observed:accept.distinction_observed},
   regulatory_access_rc15:{completion:access.completion,appropriate_boundary_observed:access.appropriate_boundary_observed}
  },
  evaluation:{ratings_1_to_5:Object.fromEntries(ratingNames.map(k=>[k,e.ratings_1_to_5[k]])),
   potentially_misleading_wording:e.potentially_misleading_wording,
   issue_detail:e.potentially_misleading_wording==="yes"?e.issue_detail:"",
   professional_intent:e.professional_intent,suggested_improvement:e.suggested_improvement},
  boundaries:{respondent_self_reported:true,tool_activity_observed_by_survey:false,
   engineering_or_scientific_review_certified:false,evidence_state_established:null,
   records_examined_by_sohadot:false}
 };
}
async function parseRequest(req){
 if(!req.headers.get("Content-Type")?.toLowerCase().startsWith("application/json"))throw Error("content-type");
 if(Number(req.headers.get("Content-Length")||0)>maxBody)throw Error("size");
 const text=await req.text();if(new TextEncoder().encode(text).length>maxBody)throw Error("size");
 const obj=JSON.parse(text);if(!obj||typeof obj!=="object"||Array.isArray(obj))throw Error("shape");return obj;
}
async function turnstile(token,env){
 if(typeof token!=="string"||token.length<10||token.length>2048)return false;
 const res=await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify",{
  method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},
  body:new URLSearchParams({secret:env.TURNSTILE_SECRET,response:token})
 });
 if(!res.ok)return false;
 const data=await res.json();
 return data.success===true&&data.hostname==="sohadot.com"&&data.action==="aec_engineering_eval";
}
function decode64(str){return Uint8Array.from(atob(str.replace(/-/g,"+").replace(/_/g,"/")),x=>x.charCodeAt(0));}
function parsePart(part){return JSON.parse(new TextDecoder().decode(decode64(part)));}
async function authorized(req,env){
 // Access must be enabled at the Cloudflare edge, and its JWT verified here independently.
 const host=env.ACCESS_TEAM_DOMAIN,aud=env.ACCESS_AUD;
 if(typeof host!=="string"||!/^[a-z0-9-]+\.cloudflareaccess\.com$/.test(host)||typeof aud!=="string"||!aud)return false;
 const jwt=req.headers.get("Cf-Access-Jwt-Assertion");
 if(typeof jwt!=="string"||jwt.length>7000||jwt.length<100)return false;
 const parts=jwt.split(".");if(parts.length!==3)return false;
 try{
  const header=parsePart(parts[0]),claims=parsePart(parts[1]);
  if(header.alg!=="RS256"||!header.kid||claims.iss!=="https://"+host||
     !(Array.isArray(claims.aud)?claims.aud.includes(aud):claims.aud===aud))return false;
  const now=Math.floor(Date.now()/1000);
  if(!Number.isFinite(claims.exp)||claims.exp<=now||claims.exp>now+86400||
     claims.nbf!==undefined&&(!Number.isFinite(claims.nbf)||claims.nbf>now+60))return false;
  const res=await fetch("https://"+host+"/cdn-cgi/access/certs",{headers:{"Accept":"application/json"}});
  if(!res.ok)return false;
  const certs=await res.json(),key=certs.keys?.find(k=>k.kid===header.kid&&k.kty==="RSA");
  if(!key)return false;
  const cryptoKey=await crypto.subtle.importKey("jwk",key,{name:"RSASSA-PKCS1-v1_5",hash:"SHA-256"},false,["verify"]);
  return await crypto.subtle.verify("RSASSA-PKCS1-v1_5",cryptoKey,decode64(parts[2]),new TextEncoder().encode(parts[0]+"."+parts[1]));
 }catch(_){return false;}
}
function adminHTML(nonce){
 return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow,noarchive"><title>Private Engineering Reviews | Sohadot</title>
<style nonce="${nonce}">:root{color-scheme:light}body{font:16px/1.5 system-ui,sans-serif;color:#183354;background:#f4f5f7;margin:0;padding:2rem}main{max-width:1080px;margin:auto}header{border-bottom:3px solid #b48a44;padding-bottom:1rem}h1,h2{color:#13294c}section{background:#fff;border:1px solid #d6e0ec;padding:1.2rem;margin:1.3rem 0;border-radius:12px}button{background:#193d70;color:#fff;padding:.7rem 1rem;border:0;border-radius:7px;cursor:pointer}button:disabled{opacity:.5}table{border-collapse:collapse;width:100%}th,td{border-bottom:1px solid #ddd;padding:.6rem;text-align:left;vertical-align:top}th{background:#eaf1f9}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eaf0f7;padding:1rem;border-radius:8px;max-height:400px;overflow:auto}.muted{color:#5c6674}a{color:#164a87}.scroller{overflow-x:auto}:focus-visible{outline:3px solid #1957ad}dl{display:grid;grid-template-columns:1fr 1fr;gap:.5rem}dt{font-weight:700}@media(max-width:620px){body{padding:1rem}dl{display:block}}</style></head>
<body><main><header><p>SOHADOT / ACCESS-CONTROLLED OPERATIONS</p><h1>Engineering evaluation — private results</h1><p class="muted">Self-reported formative feedback. Not certified engineering review or statistical evidence of product-market fit.</p></header>
<section><h2>Aggregate observations</h2><div id="summary" role="status">Loading…</div></section>
<section><h2>Individual reports</h2><p class="muted">Only authorized reviewers may read comments. Do not publicly redistribute raw feedback.</p><div class="scroller"><table><thead><tr><th>Date (UTC)</th><th>Specialization</th><th>rc-03</th><th>rc-12</th><th>rc-15</th><th>Technical concern</th><th>Detail</th></tr></thead><tbody id="rows"></tbody></table></div><p><button id="prev" type="button">Previous</button> <button id="next" type="button">Next</button> <span id="page"></span></p><pre id="details" aria-live="polite">Select a report to inspect details.</pre></section>
<p class="muted">Private by policy and verified Cloudflare Access JWT. Records are automatically purged after 90 days. Deletion requests must be handled in the Cloudflare D1 operator console.</p></main>
<script nonce="${nonce}">"use strict";(()=>{const summary=document.getElementById("summary"),rows=document.getElementById("rows"),details=document.getElementById("details"),page=document.getElementById("page");let offset=0,records=[],count=0;const cell=(tr,txt)=>{const td=document.createElement("td");td.textContent=txt==null?"—":String(txt);tr.appendChild(td);};async function get(path){const r=await fetch(path,{credentials:"same-origin",cache:"no-store"});if(!r.ok)throw Error("Private request failed: "+r.status);return r.json();}
async function load(){try{const [overview,list]=await Promise.all([get("/admin/api/overview"),get("/admin/api/reviews?offset="+offset+"&limit=20")]);count=list.total;records=list.items;summary.replaceChildren();const d=document.createElement("dl");const values=[["Responses",overview.total],["rc-03 independently completed",overview.power_completed],["rc-12 independently completed",overview.acceptance_completed],["rc-15 independently completed",overview.access_completed],["Potentially misleading wording reported",overview.issues_reported],["Would use professionally",overview.professional_yes],["Would use with improvements",overview.professional_conditional]];values.forEach(([k,v])=>{const dt=document.createElement("dt"),dd=document.createElement("dd");dt.textContent=k;dd.textContent=String(v);d.append(dt,dd);});summary.appendChild(d);rows.replaceChildren();records.forEach((x,i)=>{const r=x.report,t=r.tasks,e=r.evaluation,tr=document.createElement("tr");cell(tr,x.created_at);cell(tr,r.context.specialization);cell(tr,t.electrical_redundancy_rc03.completion);cell(tr,t.formal_acceptance_rc12.completion);cell(tr,t.regulatory_access_rc15.completion);cell(tr,e.potentially_misleading_wording);const td=document.createElement("td"),b=document.createElement("button");b.type="button";b.textContent="View";b.addEventListener("click",()=>{details.textContent=JSON.stringify(x,null,2);});td.appendChild(b);tr.appendChild(td);rows.appendChild(tr);});page.textContent=(count===0?"No responses":(offset+1)+"–"+(offset+records.length)+" of "+count);document.getElementById("prev").disabled=offset===0;document.getElementById("next").disabled=offset+20>=count;}catch(e){summary.textContent="Unable to load authorized data: "+e.message;rows.replaceChildren();details.textContent="No results loaded.";}}
document.getElementById("prev").addEventListener("click",()=>{offset=Math.max(0,offset-20);load();});document.getElementById("next").addEventListener("click",()=>{offset+=20;load();});load();})();</script></body></html>`;
}
export default{
 async fetch(req,env){
  const url=new URL(req.url),path=url.pathname,origin=req.headers.get("Origin");
  if(path.startsWith("/admin")){
   if(req.method!=="GET")return fail("Method not allowed",405);
   if(!env.DB||!await authorized(req,env))return fail("Unauthorized",401);
   if(path==="/admin"||path==="/admin/"){
    const nonce=crypto.randomUUID().replace(/-/g,"");
    return new Response(adminHTML(nonce),{headers:{"Content-Type":"text/html; charset=utf-8",...noCache,
     "Content-Security-Policy":"default-src 'none'; connect-src 'self'; script-src 'nonce-"+nonce+"'; style-src 'nonce-"+nonce+"'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"}});
   }
   if(path==="/admin/api/overview"){
    try{
     const o=await env.DB.prepare(`SELECT count(*) total,
       COALESCE(sum(json_extract(payload,'$.tasks.electrical_redundancy_rc03.completion')='completed'),0) power_completed,
       COALESCE(sum(json_extract(payload,'$.tasks.formal_acceptance_rc12.completion')='completed'),0) acceptance_completed,
       COALESCE(sum(json_extract(payload,'$.tasks.regulatory_access_rc15.completion')='completed'),0) access_completed,
       COALESCE(sum(json_extract(payload,'$.evaluation.potentially_misleading_wording')='yes'),0) issues_reported,
       COALESCE(sum(json_extract(payload,'$.evaluation.professional_intent')='yes'),0) professional_yes,
       COALESCE(sum(json_extract(payload,'$.evaluation.professional_intent')='with_improvements'),0) professional_conditional
       FROM aec_engineering_evaluations`).first();
     return json(o||{total:0,power_completed:0,acceptance_completed:0,access_completed:0,issues_reported:0,professional_yes:0,professional_conditional:0});
    }catch(_){return fail("Unable to read summary",503);}
   }
   if(path==="/admin/api/reviews"){
    const limit=Number(url.searchParams.get("limit")||20),offset=Number(url.searchParams.get("offset")||0);
    if(!Number.isSafeInteger(limit)||limit<1||limit>25||!Number.isSafeInteger(offset)||offset<0||offset>100000)return fail("Invalid pagination");
    try{
     const [total,items]=await Promise.all([
      env.DB.prepare("SELECT count(*) AS total FROM aec_engineering_evaluations").first(),
      env.DB.prepare("SELECT id,created_at,payload FROM aec_engineering_evaluations ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?").bind(limit,offset).all()
     ]);
     return json({total:total?.total||0,items:(items.results||[]).map(x=>({id:x.id,created_at:x.created_at,report:JSON.parse(x.payload)}))});
    }catch(_){return fail("Unable to read responses",503);}
   }
   return fail("Not found",404);
  }
  if(path==="/v1/status"&&req.method==="GET"){
   const ready=!!(env.DB&&env.TURNSTILE_SECRET&&env.TURNSTILE_SITE_KEY&&env.FRONTEND_ORIGIN===fixedOrigin);
   return json({ready,site_key:ready?env.TURNSTILE_SITE_KEY:null,action:"aec_engineering_eval"},ready?200:503,origin);
  }
  if(path!=="/v1/evaluations")return fail("Not found",404,origin);
  if(req.method==="OPTIONS")return origin===fixedOrigin?new Response(null,{status:204,headers:{...noCache,...cors(origin)}}):fail("Forbidden origin",403);
  if(req.method!=="POST")return fail("Method not allowed",405,origin);
  if(origin!==fixedOrigin)return fail("Forbidden origin",403);
  if(!env.DB||!env.TURNSTILE_SECRET||!env.TURNSTILE_SITE_KEY||env.FRONTEND_ORIGIN!==fixedOrigin)return fail("Not configured",503,origin);
  let body;try{body=await parseRequest(req);}catch(_){return fail("Invalid request",400,origin);}
  if(!requireKeys(body,["submission_id","consent","consent_version","turnstile_token","report"])||
   !uuid.test(body.submission_id||"")||body.consent!==true||body.consent_version!=="2026-11-12")return fail("Consent or receipt identifier missing",400,origin);
  let normalized;try{normalized=normalize(body.report);}catch(_){return fail("Invalid evaluation answers",400,origin);}
  try{if(!await turnstile(body.turnstile_token,env))return fail("Verification failed",403,origin);}
  catch(_){return fail("Verification temporarily unavailable",503,origin);}
  try{
   const result=await env.DB.prepare("INSERT OR IGNORE INTO aec_engineering_evaluations (id,consent_version,payload) VALUES (?,?,?)")
     .bind(body.submission_id,body.consent_version,JSON.stringify(normalized)).run();
   if(result.meta?.changes===1)return json({saved:true,receipt:body.submission_id},201,origin);
   return json({saved:true,receipt:body.submission_id,already_received:true},200,origin);
  }catch(_){return fail("Unable to save evaluation",503,origin);}
 },
 async scheduled(_event,env,ctx){
  if(env.DB)ctx.waitUntil(env.DB.prepare("DELETE FROM aec_engineering_evaluations WHERE created_at < strftime('%Y-%m-%dT%H:%M:%fZ','now','-90 days')").run());
 }
};
