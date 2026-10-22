(()=>{
'use strict';
const $=id=>document.getElementById(id);
const fields=['q2','q3','q4'];let api='',turnstileResponse='',secretSession=null,busy=false;
const storage='hoax-survey-v1';
const ref=new URLSearchParams(location.search).get('ref')||'direct';
const referral=['rick','discord','direct','other'].includes(ref)?ref:'other';
function say(msg,error=false){$('notice').hidden=false;$('notice').textContent=msg;$('notice').className=error?'error':'';}
function clear(){ $('notice').hidden=true; }
function pick(q){return document.querySelector('input[name="'+q+'"]:checked')?.value||'';}
function move(n){
 $('first').hidden=n!==0;$('visit').hidden=n!==1;$('end').hidden=n!==2;
 ['p1','p2','p3'].forEach((id,i)=>$(id).classList.toggle('on',i===n));
 if(n===1){$('title').innerHTML='Explore <em>Hoax.ai</em>.';$('subtitle').textContent='Your first impression is already saved. Now explore the actual site.';}
 if(n===2){$('title').innerHTML='What did you <em>discover</em>?';$('subtitle').textContent='Tell us how you understand the actual site and what would make it useful.';}
 clear();
}
async function call(path,data){
 const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),12000);
 try{
 const r=await fetch(api+path,{method:data?'POST':'GET',mode:'cors',cache:'no-store',credentials:'omit',signal:controller.signal,headers:data?{'Content-Type':'application/json'}:{},body:data?JSON.stringify(data):undefined});
 const response=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(response.error||'Service unavailable');
 return response;
 }finally{clearTimeout(timeout);}
}
function refresh(){ $('start').disabled=busy||!pick('q1')||!turnstileResponse; }
function previous(){
 try{const s=JSON.parse(sessionStorage.getItem(storage)||'null');if(s&&/^[0-9a-f-]{36}$/i.test(s.id)&&/^[0-9a-f-]{36}$/i.test(s.secret))return s;}catch(e){}
 return null;
}
async function init(){
 try{
 const settings=await fetch('./config.json',{cache:'no-store'}).then(r=>r.json());
 if(typeof settings.apiBase!=='string'||!/^https:\/\/[a-z0-9.-]+\.workers\.dev\/?$/i.test(settings.apiBase))throw new Error('Not configured');
 api=settings.apiBase.replace(/\/$/,'');
 const status=await call('/status');
 if(status.ready!==true||!status.siteKey)throw new Error('Not ready');
 $('survey').hidden=false;secretSession=previous();
 if(secretSession){move(1);return;}
 move(0);
 const script=document.createElement('script');
 script.src='https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';script.async=true;
 script.onload=()=>window.turnstile.render('#challenge',{
 sitekey:status.siteKey,action:'hoax_first_impression',theme:'dark',
 callback:token=>{turnstileResponse=token;refresh();},
 'expired-callback':()=>{turnstileResponse='';refresh();},
 'error-callback':()=>{turnstileResponse='';refresh();say('Verification failed. Refresh the page to retry.',true);}
 });
 script.onerror=()=>say('Verification unavailable. Please try later.',true);document.head.append(script);
 }catch(e){say('The survey is not accepting responses yet. Please return after it launches.',true);}
}
$('survey').addEventListener('change',refresh);
$('visited').addEventListener('change',()=>{$('next').disabled=!$('visited').checked;});
$('start').addEventListener('click',async()=>{
 if(busy||!turnstileResponse||!pick('q1'))return;
 busy=true;refresh();
 try{
 const saved=await call('/start',{version:1,q1:pick('q1'),referral,verification:turnstileResponse});
 if(!saved.saved||!saved.id||!saved.secret)throw new Error('Could not confirm first answer');
 secretSession={id:saved.id,secret:saved.secret};
 sessionStorage.setItem(storage,JSON.stringify(secretSession));move(1);
 }catch(e){
 say('Your first answer was not confirmed. Please retry. '+e.message,true);
 turnstileResponse='';if(window.turnstile)window.turnstile.reset();
 }finally{busy=false;refresh();}
});
$('next').addEventListener('click',()=>{if(secretSession&&$('visited').checked)move(2);});
$('survey').addEventListener('submit',async(e)=>{
 e.preventDefault();if(busy||!secretSession)return;
 if(fields.some(q=>!pick(q))){say('Please answer questions 2, 3 and 4.',true);return;}
 busy=true;$('finish').disabled=true;
 try{
 const r=await call('/complete',{version:1,id:secretSession.id,secret:secretSession.secret,q2:pick('q2'),q3:pick('q3'),q4:pick('q4'),q5:$('q5').value.trim()});
 if(!r.saved)throw new Error('Saving could not be confirmed');
 sessionStorage.removeItem(storage);$('survey').hidden=true;$('thanks').hidden=false;
 $('title').textContent='Feedback received';$('subtitle').hidden=true;clear();
 }catch(e){say('Unable to confirm submission. Please retry. '+e.message,true);}
 finally{busy=false;$('finish').disabled=false;}
});
init();
})();