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
test('status advertises only the public key',async()=>{const r=await worker.fetch(new Request(base+'/status',{headers:{Origin:origin}}),env);const x=await r.json();assert.equal(r.status,200);assert.equal(x.siteKey,'public-test-key');assert.equal(JSON.stringify(x).includes('private-test-key'),false);});
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
