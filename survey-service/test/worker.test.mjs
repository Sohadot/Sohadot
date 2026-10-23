import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../worker.mjs';

const base='https://example.workers.dev',origin='https://sohadot.com';
const env={FRONTEND_ORIGIN:origin,TURNSTILE_SITE_KEY:'public-test-key',TURNSTILE_SECRET:'private-test-key',
 DB:{prepare(){return {bind(){return {async run(){return {meta:{changes:1}};}};}};}}};
const start={version:1,q1:'detector',referral:'discord',verification:'valid-turnstile-sample'};
const finish={version:1,id:'5ed2ed7f-4619-4b3e-9af6-494214341bcb',secret:'c120c039-5002-4c24-b66c-3e17e7870880',
 q2:'evidence',q3:'sources',q4:'conditional',q5:'Useful'};
const request=(path,data,from=origin)=>new Request(base+path,{method:'POST',headers:{Origin:from,'Content-Type':'application/json'},body:JSON.stringify(data)});
test('unconfigured service fails closed',async()=>{assert.equal((await worker.fetch(new Request(base+'/status'),{})).status,503);});
test('status advertises only the public key',async()=>{const r=await worker.fetch(new Request(base+'/status',{headers:{Origin:origin}}),env);const x=await r.json();assert.equal(r.status,200);assert.equal(x.siteKey,'public-test-key');assert.equal(x.instrumentRevision,2);assert.equal(JSON.stringify(x).includes('private-test-key'),false);});
test('cross-origin write rejected',async()=>{assert.equal((await worker.fetch(request('/start',start,'https://bad.example'),env)).status,403);});
test('preflight rejects untrusted origin',async()=>{
 const r=await worker.fetch(new Request(base+'/start',{method:'OPTIONS',headers:{Origin:'https://bad.example'}}),env);
 assert.equal(r.status,403);assert.equal(r.headers.get('Access-Control-Allow-Origin'),null);
});
test('bad choices fail without storing',async()=>{assert.equal((await worker.fetch(request('/start',{...start,q1:'fake'}),env)).status,400);});
test('Turnstile validation required at start',async()=>{
 const old=globalThis.fetch;globalThis.fetch=async()=>Response.json({success:false});
 try{assert.equal((await worker.fetch(request('/start',start),env)).status,403);}finally{globalThis.fetch=old;}
});
test('first response stored before exploration',async()=>{
 const old=globalThis.fetch;let wrote=false;
 globalThis.fetch=async()=>Response.json({success:true,hostname:'sohadot.com',action:'hoax_first_impression'});
 const configured={...env,DB:{prepare(sql){assert.match(sql,/INSERT INTO/);return {bind(){return {async run(){wrote=true;return {meta:{changes:1}};}};}};}}};
 try{const r=await worker.fetch(request('/start',start),configured);const data=await r.json();assert.equal(r.status,201);assert.equal(wrote,true);assert.equal(data.saved,true);assert.match(data.secret,/^[\da-f-]{36}$/i);}finally{globalThis.fetch=old;}
});
test('final response updates existing row',async()=>{const r=await worker.fetch(request('/complete',finish),env);assert.equal(r.status,200);assert.equal((await r.json()).saved,true);});
test('invalid second-stage choice blocked',async()=>{assert.equal((await worker.fetch(request('/complete',{...finish,q3:'unknown'}),env)).status,400);});
test('no false success when row was not updated',async()=>{
 const absent={...env,DB:{prepare(){return {bind(){return {async run(){return {meta:{changes:0}};}};}};}}};
 assert.equal((await worker.fetch(request('/complete',finish),absent)).status,409);
});

test('Hoax-origin and X-origin source detail stored with legacy referral group',async()=>{
 const old=globalThis.fetch;
 globalThis.fetch=async()=>Response.json({success:true,hostname:'sohadot.com',action:'hoax_first_impression'});
 const seen=[];
 const custom={...env,DB:{prepare(sql){assert.match(sql,/source_detail,instrument_revision/);return {bind(...args){seen.push(args);return {async run(){return {meta:{changes:1}};}};}};}}};
 try{
  for(const source_detail of ['hoax','x','linkedin']){
   const r=await worker.fetch(request('/start',{...start,referral:'other',source_detail,instrument_revision:2}),custom);
   assert.equal(r.status,201);
  }
  assert.deepEqual(seen.map(args=>args[5]),['hoax','x','linkedin']);
  assert.deepEqual(seen.map(args=>args[6]),[2,2,2]);
 }finally{globalThis.fetch=old;}
});
test('referral cannot pretend to be discord when source detail indicates hoax',async()=>{
 const r=await worker.fetch(request('/start',{...start,referral:'discord',source_detail:'hoax',instrument_revision:2}),env);
 assert.equal(r.status,400);
});
test('prior exposure saved with completed feedback, separate from Q1',async()=>{
 let vals;
 const custom={...env,DB:{prepare(sql){assert.match(sql,/prior_exposure/);return {bind(...args){vals=args;return {async run(){return {meta:{changes:1}};}};}};}}};
 const r=await worker.fetch(request('/complete',{...finish,prior_exposure:'yes'}),custom);
 assert.equal(r.status,200);
 assert.equal(vals[4],'yes');
});
test('invalid prior exposure blocked',async()=>{
 const r=await worker.fetch(request('/complete',{...finish,prior_exposure:'not-verified'}),env);
 assert.equal(r.status,400);
});

test('single survey keeps all five original questions and the exposure metadata item',async()=>{
 const {readFileSync}=await import('node:fs');
 const {resolve}=await import('node:path');
 const html=readFileSync(resolve(import.meta.dirname,'../../hoax-ai-survey/index.html'),'utf8');
 const js=readFileSync(resolve(import.meta.dirname,'../../hoax-ai-survey/survey.js'),'utf8');
 for(const q of ['q1','q2','q3','q4'])assert.ok(html.includes('name="'+q+'"'));
 assert.match(html,/id="q5"/);
 assert.match(html,/name="prior_exposure"/);
 assert.match(js,/sourceDetail/);
 assert.match(js,/instrumentRevision!==2/);
 assert.match(js,/instrument_revision:2/);
 assert.match(js,/prior_exposure:pick/);
});
