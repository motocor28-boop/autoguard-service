-- MANTPRO IA Cloud 3.1
-- Ejecutar una sola vez en Supabase > SQL Editor.
create table if not exists public.mantpro_records (
  id uuid primary key,
  user_id uuid not null default auth.uid(),
  record_type text not null,
  payload jsonb not null,
  occurred_at timestamptz not null,
  created_at timestamptz not null default now()
);

create index if not exists mantpro_records_user_date_idx
  on public.mantpro_records (user_id, occurred_at desc);

alter table public.mantpro_records enable row level security;

drop policy if exists "Cada usuario consulta sus propios registros" on public.mantpro_records;
drop policy if exists "Cada usuario crea sus propios registros" on public.mantpro_records;
drop policy if exists "Cada usuario actualiza sus propios registros" on public.mantpro_records;
drop policy if exists "Cada usuario elimina sus propios registros" on public.mantpro_records;

create policy "Cada usuario consulta sus propios registros" on public.mantpro_records
for select to authenticated using (auth.uid() = user_id and (auth.jwt() ->> 'email') = 'motocor28@gmail.com');
create policy "Cada usuario crea sus propios registros" on public.mantpro_records
for insert to authenticated with check (auth.uid() = user_id and (auth.jwt() ->> 'email') = 'motocor28@gmail.com');
create policy "Cada usuario actualiza sus propios registros" on public.mantpro_records
for update to authenticated using (auth.uid() = user_id and (auth.jwt() ->> 'email') = 'motocor28@gmail.com')
with check (auth.uid() = user_id and (auth.jwt() ->> 'email') = 'motocor28@gmail.com');
create policy "Cada usuario elimina sus propios registros" on public.mantpro_records
for delete to authenticated using (auth.uid() = user_id and (auth.jwt() ->> 'email') = 'motocor28@gmail.com');

