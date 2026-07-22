-- Ejecutar en Supabase SQL Editor antes de completar config.js.
create table if not exists public.mantpro_records (
 id uuid primary key, record_type text not null,
 payload jsonb not null, occurred_at timestamptz not null, created_at timestamptz default now()
);
alter table public.mantpro_records enable row level security;
-- Reemplace el correo. La PWA publica usa solo anon key; esta politica protege los datos.
create policy "supervisor-only" on public.mantpro_records for all to authenticated
using ((auth.jwt() ->> 'email') = 'REEMPLAZAR_CON_CORREO_AUTORIZADO')
with check ((auth.jwt() ->> 'email') = 'REEMPLAZAR_CON_CORREO_AUTORIZADO');
-- Cree un bucket PRIVADO mantpro-evidence para fotografias. No convierta el bucket en publico.
