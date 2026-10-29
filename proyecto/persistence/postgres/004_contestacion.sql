BEGIN;
CREATE FUNCTION schema_judicial.validar_contestacion() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, schema_judicial, pg_temp AS $$
DECLARE e schema_judicial.expediente%ROWTYPE;
BEGIN
    SELECT * INTO e FROM schema_judicial.expediente WHERE id = NEW.expediente_id FOR UPDATE;
    IF NOT FOUND OR e.estado <> 'ADMITIDO' OR e.fecha_emplazamiento_validado IS NULL THEN
        RAISE EXCEPTION 'No existe emplazamiento válido en expediente admitido';
    END IF;
    NEW.en_plazo := NEW.fecha_presentacion::date <= e.fecha_limite_contestacion;
    RETURN NEW;
END $$;
CREATE TRIGGER tr_validar_contestacion BEFORE INSERT ON schema_judicial.contestacion
FOR EACH ROW EXECUTE FUNCTION schema_judicial.validar_contestacion();
COMMIT;
