-- EECR: canal de sincronización privado por dispositivo, sin acceso público a los registros.
-- Aplicado en el proyecto gecrjlkfrcrlsjhanfjz, sin cambiar mantpro_records.
CREATE TABLE IF NOT EXISTS public.eecr_device_records (
  workspace_key text NOT NULL CHECK (workspace_key ~ '^[a-f0-9]{64}$'),
  record_id text NOT NULL CHECK (char_length(record_id) BETWEEN 1 AND 160),
  payload jsonb NOT NULL,
  updated_at timestamptz NOT NULL,
  received_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT eecr_device_records_pkey PRIMARY KEY (workspace_key,record_id)
);
ALTER TABLE public.eecr_device_records ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.eecr_device_records FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON TABLE public.eecr_device_records TO service_role;
CREATE OR REPLACE FUNCTION public.eecr_device_merge_batch(p_workspace_key text,p_items jsonb)
RETURNS integer LANGUAGE plpgsql SECURITY INVOKER SET search_path=public AS $$
DECLARE changed integer := 0;
BEGIN
  IF p_workspace_key !~ '^[a-f0-9]{64}$' OR jsonb_typeof(p_items)<>'array'
     OR jsonb_array_length(p_items)>30 THEN
    RAISE EXCEPTION 'invalid batch';
  END IF;
  INSERT INTO public.eecr_device_records AS existing(workspace_key,record_id,payload,updated_at)
  SELECT p_workspace_key,value->>'id',value->'payload',(value->>'updated_at')::timestamptz
  FROM jsonb_array_elements(p_items)
  ON CONFLICT (workspace_key,record_id)
  DO UPDATE SET payload=EXCLUDED.payload,updated_at=EXCLUDED.updated_at,received_at=now()
  WHERE existing.updated_at<EXCLUDED.updated_at;
  GET DIAGNOSTICS changed=ROW_COUNT;
  RETURN changed;
END $$;
REVOKE ALL ON FUNCTION public.eecr_device_merge_batch(text,jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.eecr_device_merge_batch(text,jsonb) TO service_role;
