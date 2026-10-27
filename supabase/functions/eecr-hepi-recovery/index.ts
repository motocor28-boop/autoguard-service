/* EECR HEPI 2026-10-20 a 2026-10-27: exportación de rescate autorizada y de solo lectura. */
import {createClient} from "jsr:@supabase/supabase-js@2.95.0";
const allowed="https://motocor28-boop.github.io",encoder=new TextEncoder();
function hex(bytes:Uint8Array){return Array.from(bytes,b=>b.toString(16).padStart(2,"0")).join("")}
async function sha256(value:string){return hex(new Uint8Array(await crypto.subtle.digest("SHA-256",encoder.encode(value))))}
Deno.serve(async req=>{
 const origin=req.headers.get("origin")||"";
 const headers={"Access-Control-Allow-Origin":allowed,"Access-Control-Allow-Headers":"content-type,apikey,authorization","Access-Control-Allow-Methods":"POST,OPTIONS","Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store","Vary":"Origin"};
 const send=(body:unknown,status=200)=>new Response(JSON.stringify(body),{status,headers});
 if(origin&&origin!==allowed)return send({ok:false,error:"origin_forbidden"},403);
 if(req.method==="OPTIONS")return new Response("ok",{headers});
 if(req.method!=="POST")return send({ok:false,error:"method_forbidden"},405);
 let request:Record<string,unknown>;
 try{const raw=await req.text();if(raw.length>1000)throw Error();request=JSON.parse(raw)}catch{return send({ok:false,error:"invalid_request"},400)}
 const token=request.token;
 if(typeof token!=="string"||!/^[0-9a-f]{64}$/.test(token))return send({ok:false,error:"unauthorized"},403);
 const admin=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY"),url=Deno.env.get("SUPABASE_URL");
 if(!url||!admin)return send({ok:false,error:"server_unconfigured"},503);
 const db=createClient(url,admin,{auth:{persistSession:false,autoRefreshToken:false}});
 try{
   const hash=await sha256(token);
   const {data:authorization,error:authError}=await db.from("eecr_recovery_authorizations").select("token_hash,scope,expires_at,uses,max_uses").eq("token_hash",hash).maybeSingle();
   if(authError)throw Error("authorization_store");
   if(!authorization||authorization.scope!=="hepi-2026-10-20_27"||Date.parse(authorization.expires_at)<Date.now()||authorization.uses>=authorization.max_uses)return send({ok:false,error:"recovery_link_expired"},403);
   if(request.action==="preview"){
     const {count,error}=await db.from("eecr_recovery_oct2026").select("record_id",{head:true,count:"exact"});
     if(error)throw Error("backup_read");
     return send({ok:true,total:count||0,dates:"20 al 27 de octubre de 2026",mode:"read_only"});
   }
   if(request.action!=="page")return send({ok:false,error:"invalid_action"},400);
   const offset=request.offset,limit=request.limit;
   if(!Number.isInteger(offset)||Number(offset)<0||Number(offset)>100||limit!==2)return send({ok:false,error:"invalid_pagination"},400);
   const {data:claimed,error:claimError}=await db.from("eecr_recovery_authorizations").update({uses:authorization.uses+1}).eq("token_hash",hash).eq("uses",authorization.uses).lt("uses",authorization.max_uses).gt("expires_at",new Date().toISOString()).select("token_hash");
   if(claimError)throw Error("authorization_update");
   if(!claimed?.length)return send({ok:false,error:"request_conflict_try_again"},409);
   const {data,error}=await db.from("eecr_recovery_oct2026").select("record_id,payload").order("record_id",{ascending:true}).range(Number(offset),Number(offset)+1);
   if(error)throw Error("backup_read");
   return send({ok:true,records:(data||[]).map(x=>x.payload),offset,nextOffset:(data||[]).length===2?Number(offset)+2:null});
 }catch(e){console.error("HEPI recovery exception",String(e));return send({ok:false,error:"recovery_unavailable"},503)}
});