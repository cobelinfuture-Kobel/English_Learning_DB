'use strict';
const nativeFetch=window.fetch.bind(window);let csrfToken=null;
async function authSession(){const response=await nativeFetch('/auth/session',{credentials:'same-origin'});if(response.status===401){window.location.replace('/login.html');throw new Error('authentication_required');}const value=await response.json();csrfToken=value.csrf_token;return value;}
window.fetch=async(input,init={})=>{const method=String(init.method||'GET').toUpperCase();const headers=new Headers(init.headers||{});if(!['GET','HEAD','OPTIONS'].includes(method)){if(!csrfToken)await authSession();headers.set('X-CSRF-Token',csrfToken);}const response=await nativeFetch(input,{...init,headers,credentials:'same-origin'});if(response.status===401)window.location.replace('/login.html');return response;};
document.addEventListener('DOMContentLoaded',async()=>{try{await authSession();}catch(_){return;}const logout=document.querySelector('#logout');if(logout)logout.addEventListener('click',async()=>{await window.fetch('/auth/logout',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});window.location.replace('/login.html');});});

