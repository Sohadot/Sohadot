const HOST = 'sohadot.com';
const PATH = '/api/acquisition/topsight';
const TO = 'agent@sohadot.com';
const FROM = 'acquisition@notify.sohadot.com';
const MAX = 12000;
function json(status, value) {
  return Response.json(value, {status, headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
}
async function readBody(request) {
  const reader = request.body?.getReader();
  if (!reader) throw new Error('missing body');
  const decoder = new TextDecoder('utf-8', {fatal:true});
  let total=0, result='';
  try {
    for (;;) {
      const {done,value}=await reader.read();
      if(done) break;
      total+=value.byteLength;
      if(total>MAX) { await reader.cancel(); throw new Error('too large'); }
      result+=decoder.decode(value,{stream:true});
    }
    return JSON.parse(result+decoder.decode());
  } finally { reader.releaseLock(); }
}
function field(value, max, required=true) {
  if(typeof value!=='string') { if(!required && value===undefined) return ''; throw new Error('invalid field'); }
  const v=value.trim();
  if(v.length>max || (required && !v) || /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(v)) throw new Error('invalid field');
  return v;
}
export default {
  async fetch(request, env) {
    const url=new URL(request.url);
    if(url.hostname!==HOST || url.pathname!==PATH) return json(404,{ok:false});
    if(request.method!=='POST') return json(405,{ok:false,code:'method'});
    if(request.headers.get('Origin')!=='https://'+HOST) return json(403,{ok:false,code:'origin'});
    if(!/^application\/json(?:\s*;|$)/i.test(request.headers.get('Content-Type')||'')) return json(415,{ok:false,code:'format'});
    if(Number(request.headers.get('Content-Length')||0)>MAX) return json(413,{ok:false,code:'size'});
    let name,email,company,message,token;
    try {
      const d=await readBody(request);
      if(!d || typeof d!=='object' || Array.isArray(d)) throw new Error('invalid payload');
      name=field(d.name,120); email=field(d.email,254); company=field(d.company,160,false); message=field(d.message,2500); token=field(d.token,2048);
      if(!/^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}$/.test(email)) throw new Error('invalid email');
      if(/[\r\n]/.test(name+company)) throw new Error('invalid header');
      if(d.website) throw new Error('invalid payload');
    } catch (_) { return json(400,{ok:false,code:'invalid'}); }
    try {
      const v=await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify',{method:'POST',body:new URLSearchParams({secret:env.TURNSTILE_SECRET,response:token}),signal:AbortSignal.timeout(10000)});
      if(!v.ok) return json(503,{ok:false,code:'unavailable'});
      const check=await v.json();
      if(check.success!==true || check.hostname!==HOST || check.action!=='topsight_acquisition') return json(403,{ok:false,code:'verification'});
      const ref=crypto.randomUUID();
      const result=await env.EMAIL.send({
        from:FROM,to:TO,replyTo:email,
        subject:'TopSight — Complete set acquisition inquiry',
        text:['Reference: '+ref,'Scope: AITopSight.com + ARTopSight.com + VRTopSight.com','Listed price: USD 5,780','Name: '+name,'Contact email (visitor supplied, not verified): '+email,'Company: '+(company||'Not provided'),'','Inquiry:',message].join('\n')
      });
      if(!result?.messageId) return json(503,{ok:false,code:'delivery'});
      return json(200,{ok:true,reference:ref});
    } catch (_) { return json(503,{ok:false,code:'unavailable'}); }
  }
};
