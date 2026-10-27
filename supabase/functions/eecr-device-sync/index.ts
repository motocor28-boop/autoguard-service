// EECR: canal privado por clave aleatoria de 256 bits; sin correo ni permisos de lectura pública.
import { createClient } from "jsr:@supabase/supabase-js@2.95.0";
const allowed="https://motocor28-boop.github.io";
const allowedLocal=new Set(["null","http://127.0.0.1:8788","http://localhost:8788"]);
const cors={"Access-Control-Allow-Origin":allowed,"Access-Control-Allow-Headers":"content-type, apikey, authorization, x-client-info","Access-Control-Allow-Methods":"POST, OPTIONS","Vary":"Origin"};
const json=(x:unknown,status=200)=>new Response(JSON.stringify(x),{status,headers:{...cors,"Access-Control-Allow-Origin":allowed,"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store"}});
const hex=(a:Uint8Array)=>Array.from(a,b=>b.toString(16).padStart(2,"0")).join("");
function timestamp(s:unknown) {
  if(typeof s!=="string"||s.length>40)return null;
  const t=Date.parse(s);
  return Number.isFinite(t)&&t>0&&t<=Date.now()+3600000?new Date(t).toISOString():null;
}
Deno.serve(async(request:Request)=>{
  const clientOrigin=request.headers.get("origin")||"";
  const responseOrigin=allowedLocal.has(clientOrigin)?clientOrigin:allowed;
  const respond=(body:unknown,status=200)=>new Response(JSON.stringify(body),{status,headers:{...cors,"Access-Control-Allow-Origin":responseOrigin,"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store"}});

  if(request.method==="OPTIONS")return new Response("ok",{headers:{...cors,"Access-Control-Allow-Origin": allowedLocal.has(request.headers.get("origin")||"") ? request.headers.get("origin")! : allowed}});
  if(request.method!=="POST")return respond({error:"method_not_allowed"},405);
  const origin=request.headers.get("origin");
  if(origin&&origin!==allowed&&!allowedLocal.has(origin))return respond({error:"origin_not_allowed"},403);
  let raw="";
  try{raw=await request.text();}catch{return respond({error:"invalid_body"},400);}
  if(raw.length>2600000)return respond({error:"payload_too_large"},413);
  let body:Record<string,unknown>;
  try{body=JSON.parse(raw);}catch{return respond({error:"invalid_json"},400);}
  const secret=body.secret;
  if(typeof secret!=="string"||!/^[A-Za-z0-9_-]{43}$/.test(secret))return respond({error:"invalid_pairing_key"},401);
  let bytes:Uint8Array;
  try{bytes=Uint8Array.from(atob(secret.replace(/-/g,"+").replace(/_/g,"/")+"="),v=>v.charCodeAt(0));}
  catch{return respond({error:"invalid_pairing_key"},401);}
  if(bytes.length!==32)return respond({error:"invalid_pairing_key"},401);
  const digest=await crypto.subtle.digest("SHA-256",bytes);
  const key=hex(new Uint8Array(digest));
  const url=Deno.env.get("SUPABASE_URL"),admin=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if(!url||!admin)return respond({error:"backend_not_configured"},503);
  const db=createClient(url,admin,{auth:{persistSession:false,autoRefreshToken:false}});
  if(body.action==="health")return respond({ok:true,version:"eecr-device-v2"});
  // Defender la limpieza aun si un dispositivo antiguo conserva archivos PWA en cache.
  const isQ1Demo=(x:Record<string,unknown>)=>String(x.id||"").startsWith("q1-")||
    (x.provenance&&typeof x.provenance==="object"&&(x.provenance as Record<string,unknown>).kind==="synthetic-training")||
    (x.data&&typeof x.data==="object"&&
     (x.data as Record<string,unknown>).provenance&&
     ((x.data as Record<string,unknown>).provenance as Record<string,unknown>).kind==="synthetic-training");
  if(body.action==="push"){
    if(!Array.isArray(body.records)||body.records.length<1||body.records.length>30)return respond({error:"invalid_batch"},400);
    const records=new Map<string,{id:string;payload:unknown;updated_at:string}>();
    for(const obj of body.records){
      if(!obj||typeof obj!=="object"||Array.isArray(obj))return respond({error:"invalid_record"},400);
      const row=obj as Record<string,unknown>,id=row.id,time=timestamp(row.updatedAt||row.at);
      if(isQ1Demo(row))continue;
      if(typeof id!=="string"||id.length===0||id.length>160||!time)return respond({error:"invalid_record_metadata"},400);
      if(JSON.stringify(row).length>1900000)return respond({error:"record_too_large"},413);
      const old=records.get(id);
      if(!old||time>old.updated_at)records.set(id,{id,payload:row,updated_at:time});
    }
    if(!records.size)return respond({ok:true,changed:0,accepted:0,discardedDemo:true});
    const {data,error}=await db.rpc("eecr_device_merge_batch",{p_workspace_key:key,p_items:[...records.values()]});
    if(error)return respond({error:"storage_unavailable"},503);
    return respond({ok:true,changed:data,accepted:records.size});
  }
  if(body.action==="pull"){
    const since=body.since===undefined||body.since===null?null:timestamp(body.since);
    if(body.since!=null&&!since)return respond({error:"invalid_since"},400);
    const offset=Number(body.offset||0);
    if(!Number.isInteger(offset)||offset<0||offset>100000)return respond({error:"invalid_offset"},400);
    const limit=Math.min(8,Math.max(1,Math.floor(Number(body.limit)||8)));
    let q=db.from("eecr_device_records").select("record_id,payload,received_at").eq("workspace_key",key).order("received_at",{ascending:true}).order("record_id",{ascending:true}).range(offset,offset+limit-1);
    if(since)q=q.gt("received_at",since);
    const {data,error}=await q;
    if(error)return respond({error:"read_unavailable"},503);
    const list=data||[];
    return respond({ok:true,records:list.map(r=>r.payload),nextOffset:list.length===limit?offset+list.length:null,watermark:list.length?list[list.length-1].received_at:null});
  }
  return respond({error:"invalid_action"},400);
});
