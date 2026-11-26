-- 012 · Materias conciliables: se agregan MERCANTIL y LABORAL a CIVIL y FAMILIAR.
BEGIN;

ALTER TABLE nucleo_comun.conflicto DROP CONSTRAINT conflicto_materia_check,
  ADD CONSTRAINT conflicto_materia_check CHECK (materia IN ('CIVIL','FAMILIAR','MERCANTIL','LABORAL'));
ALTER TABLE schema_judicial.demanda DROP CONSTRAINT demanda_materia_check,
  ADD CONSTRAINT demanda_materia_check CHECK (materia IN ('CIVIL','FAMILIAR','MERCANTIL','LABORAL'));
ALTER TABLE schema_judicial.juzgado DROP CONSTRAINT juzgado_materia_check,
  ADD CONSTRAINT juzgado_materia_check CHECK (materia IN ('CIVIL','FAMILIAR','MERCANTIL','LABORAL'));
ALTER TABLE schema_judicial.juez_adscripcion DROP CONSTRAINT juez_adscripcion_especialidad_check,
  ADD CONSTRAINT juez_adscripcion_especialidad_check CHECK (especialidad IN ('CIVIL','FAMILIAR','MERCANTIL','LABORAL'));
ALTER TABLE schema_odr.mediador DROP CONSTRAINT mediador_especialidades_check,
  ADD CONSTRAINT mediador_especialidades_check
    CHECK (especialidades <@ ARRAY['CIVIL','FAMILIAR','MERCANTIL','LABORAL'] AND cardinality(especialidades) > 0);

COMMIT;
