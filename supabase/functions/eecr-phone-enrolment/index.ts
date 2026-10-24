import {createClient} from "jsr:@supabase/supabase-js@2.95.0";
const allowed=new Set(["https://motocor28-boop.github.io","null","http://127.0.0.1:8788","http://localhost:8788"]);
const txt=new TextEncoder(),pattern=/^[A-Za-z0-9_-]{43}$/;
const hex=(u:Uint8Array)=>Array.from(u,x=>x.toString(16).padStart(2,"0")).join("");
async function hash(u:Uint8Array){return hex(new Uint8Array(await crypto.subtle.digest("SHA-256",u)))}
function bytes(s:unknown){if(typeof s!=="string"||!pattern.test(s))return null;try{const b=Uint8Array.from(atob(s.replace(/-/g,"+").replace(/_/g,"/")+"="),x=>x.charCodeAt(0));return b.length===32?b:null}catch{return null}}
function phone(s:unknown){if(typeof s!=="string"||s.length>30)return null;let n=s.trim().replace(/[\s()\-.]/g,"");if(/^9\d{8}$/.test(n))n="+56"+n;else if(/^56\d{9}$/.test(n))n="+"+n;return /^\+[1-9]\d{7,14}$/.test(n)?n:null}
Deno.serve(async req=>{
 const origin=req.headers.get("origin")||"";
 const headers={"Access-Control-Allow-Origin":allowed.has(origin)?origin:"https://motocor28-boop.github.io","Access-Control-Allow-Headers":"content-type,apikey,authorization,x-client-info","Access-Control-Allow-Methods":"POST,OPTIONS","Content-Type":"application/json","Cache-Control":"no-store","Vary":"Origin"};
 const send=(o:object,s=200)=>new Response(JSON.stringify(o),{status:s,headers});
 if(origin&&!allowed.has(origin))return send({ok:false,error:"origin_not_allowed"},403);
 if(req.method==="OPTIONS")return new Response("ok",{headers});
 if(req.method!=="POST")return send({ok:false,error:"method_not_allowed"},405);
 const url=Deno.env.get("SUPABASE_URL"),admin=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
 if(!url||!admin)return send({ok:false,error:"not_configured"},503);
 let body:Record<string,unknown>;
 try{const raw=await req.text();if(raw.length>5000)return send({ok:false,error:"oversized"},413);body=JSON.parse(raw)}catch{return send({ok:false,error:"invalid_body"},400)}
 const db=createClient(url,admin,{auth:{persistSession:false,autoRefreshToken:false}});
 const key=bytes(body.secret),workspace=key?await hash(key):null,num=phone(body.phone);
 const ph=async()=>{if(!num)return null;const k=await crypto.subtle.importKey("raw",txt.encode(admin),{name:"HMAC",hash:"SHA-256"},false,["sign"]);return hex(new Uint8Array(await crypto.subtle.sign("HMAC",k,txt.encode(num))))};
 const alias=await ph();
 const permitted=async()=>{if(!workspace||!alias)return false;const {data,error}=await db.from("eecr_phone_channels").select("workspace_key").eq("phone_hash",alias).maybeSingle();if(error)throw Error("storage");return data?.workspace_key===workspace};
 try{
 if(body.action==="bind_phone"){
  if(!alias||!workspace)return send({ok:false,error:"invalid_phone_or_channel"},400);
  const {data,error}=await db.from("eecr_phone_channels").select("workspace_key").eq("phone_hash",alias).maybeSingle();if(error)throw Error("storage");
  if(data&&data.workspace_key!==workspace)return send({ok:false,error:"phone_already_assigned"},409);
  if(!data){const r=await db.from("eecr_phone_channels").insert({phone_hash:alias,workspace_key:workspace});if(r.error)return send({ok:false,error:"phone_already_assigned"},409)}
  return send({ok:true,bound:true});
 }
 if(body.action==="request_join"){
  const token=bytes(body.token),jwk=body.publicKey as Record<string,unknown>;
  if(!alias||!token||!jwk||jwk.kty!=="RSA"||jwk.e!=="AQAB"||typeof jwk.n!=="string"||jwk.n.length<340||jwk.n.length>800||jwk.d!==undefined)return send({ok:false,error:"invalid_request"},400);
  const {count,error}=await db.from("eecr_device_join_requests").select("id",{count:"exact",head:true}).eq("phone_hash",alias).gte("requested_at",new Date(Date.now()-600000).toISOString());if(error)throw Error("storage");
  if((count||0)>=5)return send({ok:false,error:"too_many_requests"},429);
  const label=String(body.deviceLabel||"Informe KPI Windows").slice(0,80).replace(/[<>]/g,"");
  const {data,error:err}=await db.from("eecr_device_join_requests").insert({phone_hash:alias,request_token_hash:await hash(token),public_key:jwk,device_label:label}).select("id,expires_at").single();if(err)throw Error("storage");
  return send({ok:true,requestId:data.id,expiresAt:data.expires_at});
 }
 if(body.action==="poll_join"){
  const token=bytes(body.token),id=body.requestId;
  if(!token||typeof id!=="string"||!/^[-0-9a-f]{36}$/i.test(id))return send({ok:false,error:"invalid_request"},400);
  const {data,error}=await db.from("eecr_device_join_requests").select("request_token_hash,expires_at,approved_ciphertext,rejected_at").eq("id",id).maybeSingle();if(error)throw Error("storage");
  if(!data||data.request_token_hash!==await hash(token))return send({ok:false,error:"not_found"},404);
  if(data.rejected_at)return send({ok:true,status:"rejected"});
  if(Date.parse(data.expires_at)<Date.now())return send({ok:true,status:"expired"});
  return send({ok:true,status:data.approved_ciphertext?"approved":"pending",ciphertext:data.approved_ciphertext||undefined});
 }
 if(["pending_joins","approve_join","reject_join"].includes(String(body.action))){
  if(!await permitted())return send({ok:false,error:"not_authorized"},403);
  if(body.action==="pending_joins"){
   const {data,error}=await db.from("eecr_device_join_requests").select("id,device_label,public_key,requested_at").eq("phone_hash",alias).is("approved_at",null).is("rejected_at",null).gt("expires_at",new Date().toISOString()).order("requested_at",{ascending:false}).limit(5);if(error)throw Error("storage");
   return send({ok:true,requests:data||[]});
  }
  const id=body.requestId;
  if(typeof id!=="string"||!/^[-0-9a-f]{36}$/i.test(id))return send({ok:false,error:"invalid_request"},400);
  if(body.action==="approve_join"){
   const c=body.ciphertext;
   if(typeof c!=="string"||c.length<200||c.length>1500||!/^[A-Za-z0-9+/]+=*$/.test(c))return send({ok:false,error:"invalid_ciphertext"},400);
   const {data,error}=await db.from("eecr_device_join_requests").update({approved_ciphertext:c,approved_at:new Date().toISOString()}).eq("id",id).eq("phone_hash",alias).is("approved_at",null).is("rejected_at",null).gt("expires_at",new Date().toISOString()).select("id");if(error)throw Error("storage");
   return send({ok:true,approved:!!data?.length});
  }
  const {data,error}=await db.from("eecr_device_join_requests").update({rejected_at:new Date().toISOString()}).eq("id",id).eq("phone_hash",alias).is("approved_at",null).select("id");if(error)throw Error("storage");
  return send({ok:true,rejected:!!data?.length});
 }
 return send({ok:false,error:"invalid_action"},400);
 }catch(e){console.error("Join error",String(e));return send({ok:false,error:"storage_unavailable"},503)}
});