// Sohadot public survey collection. Raw results remain in private D1; no public read endpoint.
const CHOICES={
 q1:['detector','guidance','news','other','unsure'],
 q2:['evidence','detector','reporting','unsure'],
 q3:['checklist','sources','synthetic','gaps'],
 q4:['regular','occasional','conditional','unlikely'],
 referral:['rick','discord','direct','other'],
 source_detail:['rick','discord','direct','other','hoax','x','linkedin'],
 prior_exposure:['yes','no','unsure']
};
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const good=(s,k)=>typeof s==='string'&&CHOICES[k].includes(s);
function headers(origin,env){
 const allowed=env.FRONTEND_ORIGIN||'https://sohadot.com';
 return origin===allowed?{'Access-Control-Allow-Origin':allowed,'Access-Control-Allow-Methods':'GET,POST,OPTIONS','Access-Control-Allow-Headers':'Content-Type','Access-Control-Max-Age':'600','Vary':'Origin'}:{};
}
function json(data,status,origin,env){
 return new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff',...headers(origin,env)}});
}
async function hash(secret){
 const b=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(secret));
 return Array.from(new Uint8Array(b),n=>n.toString(16).padStart(2,'0')).join('');
}
async function bodyOf(req){
 if(!req.headers.get('Content-Type')?.startsWith('application/json'))throw Error('type');
 if(Number(req.headers.get('Content-Length')||0)>3000)throw Error('size');
 const raw=await req.text();if(raw.length>3000)throw Error('size');
 const o=JSON.parse(raw);if(!o||Array.isArray(o)||typeof o!=='object')throw Error('shape');
 return o;
}
async function verify(token,env){
 if(typeof token!=='string'||token.length<10||token.length>2048)return false;
 const r=await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify',{
  method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},
  body:new URLSearchParams({secret:env.TURNSTILE_SECRET,response:token})
 });
 if(!r.ok)return false;
 const v=await r.json();
 return v.success===true&&v.hostname==='sohadot.com'&&v.action==='hoax_first_impression';
}
export default {
 async fetch(req,env){
  const origin=req.headers.get('Origin'),allowed=env.FRONTEND_ORIGIN||'https://sohadot.com',path=new URL(req.url).pathname;
  if(req.method==='OPTIONS')return origin===allowed?new Response(null,{status:204,headers:headers(origin,env)}):json({error:'Forbidden'},403,origin,env);
  const configured=!!(env.DB&&env.TURNSTILE_SITE_KEY&&env.TURNSTILE_SECRET&&env.FRONTEND_ORIGIN);
  if(path==='/status'&&req.method==='GET')return json({ready:configured,siteKey:configured?env.TURNSTILE_SITE_KEY:null,instrumentRevision:configured?2:null},configured?200:503,origin,env);
  if(!['/start','/complete'].includes(path)||req.method!=='POST')return json({error:'Not found'},404,origin,env);
  if(!configured)return json({error:'Not configured'},503,origin,env);
  if(origin!==allowed)return json({error:'Forbidden origin'},403,origin,env);
  let body;try{body=await bodyOf(req);}catch(e){return json({error:'Invalid JSON'},400,origin,env);}
  if(body.version!==1)return json({error:'Invalid questionnaire version'},400,origin,env);
  if(path==='/start'){
   if(!good(body.q1,'q1')||!good(body.referral,'referral'))return json({error:'Invalid choice'},400,origin,env);
   // Backward-compatible: legacy clients omit revision and detail.
   const revision=body.instrument_revision===undefined?1:body.instrument_revision;
   const detail=body.source_detail===undefined?body.referral:body.source_detail;
   if(![1,2].includes(revision)||!good(detail,'source_detail')||
      (detail==='rick'||detail==='discord'||detail==='direct'||detail==='other'?body.referral!==detail:body.referral!=='other')){
    return json({error:'Invalid survey source'},400,origin,env);
   }
   try{if(!await verify(body.verification,env))return json({error:'Verification failed'},403,origin,env);}
   catch(e){return json({error:'Verification temporarily unavailable'},503,origin,env);}
   const id=crypto.randomUUID(),secret=crypto.randomUUID();
   try{
    await env.DB.prepare('INSERT INTO survey_responses (id,secret_hash,version,q1,referral,source_detail,instrument_revision) VALUES (?,?,?,?,?,?,?)')
      .bind(id,await hash(secret),1,body.q1,body.referral,detail,revision).run();
    return json({id,secret,saved:true},201,origin,env);
   }catch(e){return json({error:'Unable to save first response'},503,origin,env);}
  }
  if(!uuid.test(body.id||'')||!uuid.test(body.secret||'')||
     !good(body.q2,'q2')||!good(body.q3,'q3')||!good(body.q4,'q4')||
     typeof body.q5!=='string'||body.q5.length>400||/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(body.q5)||
     (body.prior_exposure!==undefined && body.prior_exposure!==null && !good(body.prior_exposure,'prior_exposure'))){
    return json({error:'Invalid feedback'},400,origin,env);
  }
  try{
   const exposure=body.prior_exposure===undefined?null:body.prior_exposure;
   const r=await env.DB.prepare("UPDATE survey_responses SET q2=?,q3=?,q4=?,q5=?,prior_exposure=?,completed_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=? AND secret_hash=? AND completed_at IS NULL")
     .bind(body.q2,body.q3,body.q4,body.q5,exposure,body.id,await hash(body.secret)).run();
   if(r.meta?.changes!==1)return json({error:'Missing or already completed response'},409,origin,env);
   return json({saved:true},200,origin,env);
  }catch(e){return json({error:'Unable to save feedback'},503,origin,env);}
 },
 async scheduled(event,env,ctx){
  if(env.DB)ctx.waitUntil(env.DB.prepare("DELETE FROM survey_responses WHERE created_at < strftime('%Y-%m-%dT%H:%M:%fZ','now','-90 days')").run());
 }
};