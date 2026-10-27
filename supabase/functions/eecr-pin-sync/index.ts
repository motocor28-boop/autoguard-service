import {createClient} from "jsr:@supabase/supabase-js@2.95.0";
const b64=(u:Uint8Array)=>btoa(String.fromCharCode(...u));
const un64=(s:string)=>Uint8Array.from(atob(s),v=>v.charCodeAt(0));
const hex=(u:Uint8Array)=>Array.from(u,v=>v.toString(16).padStart(2,"0")).join("");
const te=new TextEncoder();
async function hashed(data:Uint8Array){return hex(new Uint8Array(await crypto.subtle.digest("SHA-256",data)))}
async function hmac(key:string,data:string){const k=await crypto.subtle.importKey("raw",te.encode(key),{name:"HMAC",hash:"SHA-256"},false,["sign"]);return hex(new Uint8Array(await crypto.subtle.sign("HMAC",k,te.encode(data))))}
async function aesKey(key:string){return crypto.subtle.importKey("raw",await crypto.subtle.digest("SHA-256",te.encode("pin-key-v1:"+key)),"AES-GCM",false,["encrypt","decrypt"])}
function decodeSecret(s:unknown){if(typeof s!=="string"||!/^[\w-]{43}$/.test(s))return null;try{const d=un64(s.replace(/-/g,"+").replace(/_/g,"/")+"=");return d.length===32?d:null}catch{return null}}
function code(){let a=new Uint32Array(1);do{crypto.getRandomValues(a)}while(a[0]>=4200000000);return String(a[0]%100000000).padStart(8,"0")}
Deno.serve(async req=>{
 const origin=req.headers.get("origin")||"",okOrigin=["https://motocor28-boop.github.io","null"];
 const headers={"Access-Control-Allow-Origin":okOrigin.includes(origin)?origin:okOrigin[0],"Access-Control-Allow-Headers":"content-type,apikey,authorization","Access-Control-Allow-Methods":"POST,OPTIONS","Content-Type":"application/json","Cache-Control":"no-store"};
 const reply=(v:unknown,s=200)=>new Response(JSON.stringify(v),{status:s,headers});
 if(origin&&!okOrigin.includes(origin))return reply({ok:false,error:"origin_denied"},403);
 if(req.method==="OPTIONS")return new Response("ok",{headers});
 if(req.method!=="POST")return reply({ok:false,error:"invalid_method"},405);
 let data:Record<string,unknown>;try{const raw=await req.text();if(raw.length>3500)throw Error();data=JSON.parse(raw)}catch{return reply({ok:false,error:"invalid_payload"},400)}
 const admin=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY"),url=Deno.env.get("SUPABASE_URL");if(!admin||!url)return reply({ok:false,error:"server_config"},503);
 const db=createClient(url,admin,{auth:{persistSession:false,autoRefreshToken:false}});
 try{
  if(data.action==="create"){
   const secret=decodeSecret(data.secret);if(!secret)return reply({ok:false,error:"invalid_channel"},400);
   const k=await aesKey(admin),iv=crypto.getRandomValues(new Uint8Array(12)),cipher=b64(new Uint8Array(await crypto.subtle.encrypt({name:"AES-GCM",iv},k,secret)));
   const workspace=await hashed(secret);
   for(let i=0;i<4;i++){const pin=code(),pinHash=await hmac(admin,"join:"+pin);const {error}=await db.from("eecr_pin_pairings").insert({pin_hash:pinHash,workspace_key:workspace,sealed_secret:cipher,iv:b64(iv)});
    if(!error)return reply({ok:true,pin,expiresInSeconds:300});if(error.code!=="23505")throw Error("create_storage")}
   return reply({ok:false,error:"try_again"},503);
  }
  if(data.action==="join"){
   const pin=data.pin,k=data.publicKey as Record<string,unknown>;
   if(typeof pin!=="string"||!/^\d{8}$/.test(pin)||!k||k.kty!=="RSA"||k.e!=="AQAB"||typeof k.n!=="string"||k.n.length<340||k.n.length>800||k.d)return reply({ok:false,error:"bad_pin"},400);
   const address=(req.headers.get("cf-connecting-ip")||"unknown").slice(0,150);
   const addressHash=await hmac(admin,"ip:"+address),since=new Date(Date.now()-600000).toISOString();
   const {count,error:cErr}=await db.from("eecr_pin_attempts").select("id",{head:true,count:"exact"}).eq("ip_hash",addressHash).gte("attempted_at",since);
   if(cErr)throw Error("rate_read");if((count||0)>=8)return reply({ok:false,error:"too_many_attempts"},429);
   const {error:aErr}=await db.from("eecr_pin_attempts").insert({ip_hash:addressHash});if(aErr)throw Error("rate_write");
   const pinHash=await hmac(admin,"join:"+pin);const {data:row,error:rErr}=await db.from("eecr_pin_pairings").select("sealed_secret,iv,expires_at,used_at").eq("pin_hash",pinHash).maybeSingle();
   if(rErr)throw Error("pin_read");if(!row||row.used_at||Date.parse(row.expires_at)<Date.now())return reply({ok:false,error:"pin_expired"},403);
   const bytes=new Uint8Array(await crypto.subtle.decrypt({name:"AES-GCM",iv:un64(row.iv)},await aesKey(admin),un64(row.sealed_secret)));
   const publicKey=await crypto.subtle.importKey("jwk",k,{name:"RSA-OAEP",hash:"SHA-256"},false,["encrypt"]);
   const ciphertext=b64(new Uint8Array(await crypto.subtle.encrypt({name:"RSA-OAEP"},publicKey,bytes)));
   const {data:claimed,error:uErr}=await db.from("eecr_pin_pairings").update({used_at:new Date().toISOString()}).eq("pin_hash",pinHash).is("used_at",null).gt("expires_at",new Date().toISOString()).select("pin_hash");
   if(uErr)throw Error("pin_claim");if(!claimed?.length)return reply({ok:false,error:"pin_used"},409);
   return reply({ok:true,ciphertext});
  }
  return reply({ok:false,error:"unknown_action"},400);
 }catch(error){console.error("PIN connection",String(error));return reply({ok:false,error:"service_unavailable"},503)}
});