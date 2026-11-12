import test from "node:test";
import assert from "node:assert/strict";
import worker from "../worker.mjs";

const host="https://aec-evaluation.sohadot.com",origin="https://sohadot.com";
const id="27b2ea5b-4e7f-4f15-9cda-08cdfcf52ad9";
function report(){
 return {
  format:"sohadot-aec-engineering-evaluation",protocol:"AEC-UAT-ENG-001",format_version:"1.0.0",
  generated_at_utc:"2026-11-12T09:00:00Z",
  context:{specialization:"electrical_engineering",experience_range:"6_10",prior_tool_exposure:"no"},
  tasks:{
   electrical_redundancy_rc03:{completion:"completed",observation:"A commissioning record needs criteria.\nMore evidence is needed."},
   formal_acceptance_rc12:{completion:"partial",distinction_observed:"partial"},
   regulatory_access_rc15:{completion:"completed",appropriate_boundary_observed:"yes"}
  },
  evaluation:{
   ratings_1_to_5:{terminology:4,boundaries:5,document_requests:4,ease_of_use:3,export_utility:4,professional_value:4},
   potentially_misleading_wording:"yes",issue_detail:"The test record alone cannot establish acceptance.",
   professional_intent:"with_improvements",suggested_improvement:"Show who may hold signed acceptance."
  },
  boundaries:{respondent_self_reported:true,tool_activity_observed_by_survey:false,
   engineering_or_scientific_review_certified:false,evidence_state_established:null,
   records_examined_by_sohadot:false,transmission:"Storage requires separate voluntary consent."}
 };
}
function payload(overrides={}){return {submission_id:id,consent:true,consent_version:"2026-11-12",turnstile_token:"valid-turnstile-token",report:report(),...overrides};}
function post(b=payload(),from=origin){
 return new Request(host+"/v1/evaluations",{method:"POST",headers:{"Content-Type":"application/json",Origin:from},body:JSON.stringify(b)});
}
class MemoryDB{
 constructor(){this.rows=new Map();this.statements=[];}
 prepare(sql){
  const db=this;
  function binder(args){
   return {
    async run(){
     if(sql.includes("INSERT OR IGNORE")){
      if(db.rows.has(args[0]))return {meta:{changes:0}};
      db.rows.set(args[0],{id:args[0],consent_version:args[1],payload:args[2],created_at:"2026-11-12T09:00:00.000Z"});
      return {meta:{changes:1}};
     }
     if(sql.includes("DELETE FROM")){
      db.rows.clear();return {meta:{changes:1}};
     }
     throw Error("Unexpected SQL run: "+sql);
    },
    async first(){
     if(sql.includes("json_extract")){
      const vals=Array.from(db.rows.values()).map(row=>JSON.parse(row.payload));
      return {total:vals.length,
       power_completed:vals.filter(r=>r.tasks.electrical_redundancy_rc03.completion==="completed").length,
       acceptance_completed:vals.filter(r=>r.tasks.formal_acceptance_rc12.completion==="completed").length,
       access_completed:vals.filter(r=>r.tasks.regulatory_access_rc15.completion==="completed").length,
       issues_reported:vals.filter(r=>r.evaluation.potentially_misleading_wording==="yes").length,
       professional_yes:vals.filter(r=>r.evaluation.professional_intent==="yes").length,
       professional_conditional:vals.filter(r=>r.evaluation.professional_intent==="with_improvements").length};
     }
     if(sql.includes("count(*)"))return {total:db.rows.size};
     throw Error("Unexpected SQL first: "+sql);
    },
    async all(){
     if(sql.includes("SELECT id,created_at,payload"))return {results:Array.from(db.rows.values()).slice(args[1],args[1]+args[0])};
     throw Error("Unexpected SQL all: "+sql);
    }
   };
  }
  return {bind(...args){db.statements.push(sql);return binder(args);},
   ...binder([])};
 }
}
function env(db=new MemoryDB()){return {DB:db,FRONTEND_ORIGIN:origin,TURNSTILE_SITE_KEY:"0x4AAAAABCDEF000000000000000",TURNSTILE_SECRET:"private-test-secret",
 ACCESS_TEAM_DOMAIN:"test.cloudflareaccess.com",ACCESS_AUD:"aec-access-aud-test"};}
async function withFetch(callback,options={}){
 const original=globalThis.fetch;
 globalThis.fetch=async(input)=>{
  const url=String(input);
  if(url.includes("siteverify"))return Response.json({success:options.turnstileSuccess??true,
   hostname:options.hostname??"sohadot.com",action:options.action??"aec_engineering_eval"});
  if(url.includes("/cdn-cgi/access/certs"))return Response.json({keys:options.keys||[]});
  throw Error("Unapproved external fetch: "+url);
 };
 try{return await callback();}finally{globalThis.fetch=original;}
}

test("public status fails closed when D1 or Turnstile absent",async()=>{
 const e=env();delete e.DB;
 const r=await worker.fetch(new Request(host+"/v1/status",{headers:{Origin:origin}}),e);
 assert.equal(r.status,503);const v=await r.json();assert.equal(v.ready,false);
 assert.equal(JSON.stringify(v).includes("private-test-secret"),false);
});
test("public collection stays unavailable if operator Access settings are absent",async()=>{
 const e=env();delete e.ACCESS_AUD;
 let r=await worker.fetch(new Request(host+"/v1/status",{headers:{Origin:origin}}),e);
 assert.equal(r.status,503);
 r=await worker.fetch(post(),e);
 assert.equal(r.status,503);
 assert.equal(e.DB.rows.size,0);
});
test("status advertises only public site key and rejects other origins in CORS",async()=>{
 const e=env();
 const r=await worker.fetch(new Request(host+"/v1/status",{headers:{Origin:origin}}),e);
 assert.equal(r.status,200);assert.equal((await r.json()).ready,true);
 assert.equal(r.headers.get("Access-Control-Allow-Origin"),origin);
 const o=await worker.fetch(new Request(host+"/v1/status",{headers:{Origin:"https://attacker.invalid"}}),e);
 assert.equal(o.headers.get("Access-Control-Allow-Origin"),null);
});
test("no unauthorized origin, malformed consent, or missing challenge can write",async()=>{
 const e=env();
 assert.equal((await worker.fetch(post(payload(),"https://evil.invalid"),e)).status,403);
 assert.equal((await worker.fetch(post(payload({consent:false})),e)).status,400);
 assert.equal((await worker.fetch(post(payload({consent_version:"wrong"})),e)).status,400);
 assert.equal((await worker.fetch(post(payload({turnstile_token:"abc"})),e)).status,403);
 assert.equal(e.DB.rows.size,0);
});
test("CORS preflight allows trusted front end only",async()=>{
 const e=env();
 let r=await worker.fetch(new Request(host+"/v1/evaluations",{method:"OPTIONS",headers:{Origin:origin}}),e);
 assert.equal(r.status,204);assert.equal(r.headers.get("Access-Control-Allow-Origin"),origin);
 r=await worker.fetch(new Request(host+"/v1/evaluations",{method:"OPTIONS",headers:{Origin:"https://evil.invalid"}}),e);
 assert.equal(r.status,403);
});
test("reject unknown fields, invalid ratings and unsupported evidence claims",async()=>{
 const e=env();
 const extra=report();extra.context.injected="pwn";
 const badrating=report();badrating.evaluation.ratings_1_to_5.terminology=19;
 const fake=report();fake.boundaries.evidence_state_established="operational";
 for(const r of [extra,badrating,fake]){
  const res=await worker.fetch(post(payload({report:r})),e);
  assert.equal(res.status,400);
 }
 assert.equal(e.DB.rows.size,0);
});
test("Turnstile server response must match hostname and action",async()=>{
 const e=env();
 for(const opts of [{hostname:"evil.invalid"},{action:"unrelated"},{turnstileSuccess:false}]){
  await withFetch(async()=>assert.equal((await worker.fetch(post(),e)).status,403),opts);
 }
 assert.equal(e.DB.rows.size,0);
});
test("complete authorized consent saves exactly one bounded normalized review",async()=>{
 const e=env();
 await withFetch(async()=>{
  const r=await worker.fetch(post(),e);
  assert.equal(r.status,201);
  assert.deepEqual(await r.json(),{saved:true,receipt:id});
  assert.equal(e.DB.rows.size,1);
  const saved=JSON.parse(e.DB.rows.get(id).payload);
  assert.equal(saved.tasks.electrical_redundancy_rc03.observation.includes("\n"),true);
  assert.equal(saved.boundaries.evidence_state_established,null);
  assert.equal(saved.context.specialization,"electrical_engineering");
  assert.equal(saved.generated_at_utc,undefined);
  assert.equal(JSON.stringify(saved).includes("valid-turnstile-token"),false);
  assert.equal(JSON.stringify(e.DB.rows.get(id)).includes("private-test-secret"),false);
 });
});
test("repeated idempotent submission is not duplicated",async()=>{
 const e=env();
 await withFetch(async()=>{
  assert.equal((await worker.fetch(post(),e)).status,201);
  const second=await worker.fetch(post(),e);
  assert.equal(second.status,200);
  assert.equal((await second.json()).already_received,true);
  assert.equal(e.DB.rows.size,1);
 });
});
test("private dashboard and its APIs never allow anonymous reads",async()=>{
 const e=env();
 for(const path of ["/admin","/admin/api/overview","/admin/api/reviews"]){
  const r=await worker.fetch(new Request(host+path),e);
  assert.equal(r.status,401);assert.equal(r.headers.get("Access-Control-Allow-Origin"),null);
 }
 assert.equal((await worker.fetch(new Request(host+"/admin",{method:"POST"}),e)).status,405);
});
function enc(x){return Buffer.from(JSON.stringify(x)).toString("base64url");}
async function accessFixture(opts={}){
 const key=await crypto.subtle.generateKey({name:"RSASSA-PKCS1-v1_5",modulusLength:2048,publicExponent:new Uint8Array([1,0,1]),hash:"SHA-256"},true,["sign","verify"]);
 const jwk=await crypto.subtle.exportKey("jwk",key.publicKey);jwk.kid="test-rsa-key";
 const now=Math.floor(Date.now()/1000);
 const head=enc({alg:"RS256",kid:"test-rsa-key",typ:"JWT"});
 const data=enc({iss:"https://test.cloudflareaccess.com",aud:opts.aud??["aec-access-aud-test"],nbf:now-30,exp:now+300});
 const raw=head+"."+data;
 const sig=Buffer.from(await crypto.subtle.sign("RSASSA-PKCS1-v1_5",key.privateKey,new TextEncoder().encode(raw))).toString("base64url");
 return {jwt:raw+"."+sig,keys:[jwk]};
}
test("cryptographically verified Cloudflare Access token unlocks private summary and review list",async()=>{
 const e=env(),{jwt,keys}=await accessFixture();
 await withFetch(async()=>{await worker.fetch(post(),e);},{keys});
 await withFetch(async()=>{
  const headers={"Cf-Access-Jwt-Assertion":jwt};
  let r=await worker.fetch(new Request(host+"/admin",{headers}),e);
  assert.equal(r.status,200);
  const html=await r.text();
  assert.match(html,/private results/);
  assert.match(html,/<script nonce="[a-z0-9]+">/);
  assert.doesNotMatch(html,/private-test-secret/);
  r=await worker.fetch(new Request(host+"/admin/api/overview",{headers}),e);
  assert.equal(r.status,200);
  const stats=await r.json();assert.equal(stats.total,1);assert.equal(stats.issues_reported,1);
  r=await worker.fetch(new Request(host+"/admin/api/reviews?limit=20&offset=0",{headers}),e);
  const v=await r.json();
  assert.equal(v.total,1);assert.equal(v.items[0].report.tasks.electrical_redundancy_rc03.completion,"completed");
  r=await worker.fetch(new Request(host+"/admin/api/reviews?limit=200",{headers}),e);
  assert.equal(r.status,400);
 },{keys});
});
test("signed Access JWT for wrong audience is rejected",async()=>{
 const e=env(),{jwt,keys}=await accessFixture({aud:["different-application"]});
 await withFetch(async()=>{
  assert.equal((await worker.fetch(new Request(host+"/admin",{headers:{"Cf-Access-Jwt-Assertion":jwt}}),e)).status,401);
 },{keys});
});
test("spoofed invalid JWT signature is rejected",async()=>{
 const e=env(),{jwt,keys}=await accessFixture();
 const tampered=jwt.slice(0,-6)+"ABCDEF";
 await withFetch(async()=>{
  assert.equal((await worker.fetch(new Request(host+"/admin",{headers:{"Cf-Access-Jwt-Assertion":tampered}}),e)).status,401);
 },{keys});
});
test("scheduled maintenance purges records older than 90 days",async()=>{
 const e=env();e.DB.rows.set(id,{id,created_at:"2020-01-01T00:00:00.000Z",payload:"{}"});
 let scheduled;
 await worker.scheduled({},e,{waitUntil(p){scheduled=p;}});
 await scheduled;
 assert.equal(e.DB.rows.size,0);
});
