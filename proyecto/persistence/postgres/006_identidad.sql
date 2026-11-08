-- P1: alta de personal por administración, activación y cambio de contraseña. No modifica migraciones previas.
BEGIN;
-- El propio usuario actualiza su contraseña y su MFA (ya tiene UPDATE por 003; se limita por política).
-- Administración da de alta y desactiva personal institucional; nunca ve hashes ni secretos.
GRANT INSERT (id, correo, nombre, password_hash, cargo, debe_cambiar_password) ON nucleo_comun.usuario TO rol_app_admin;
GRANT UPDATE (activo) ON nucleo_comun.usuario TO rol_app_admin;
GRANT SELECT (id, nombre, correo, activo, mfa_habilitado, cargo, creado_en) ON nucleo_comun.usuario TO rol_app_admin;
GRANT INSERT ON nucleo_comun.usuario_rol TO rol_app_admin;
CREATE POLICY usuario_admin_alta ON nucleo_comun.usuario FOR INSERT TO rol_app_admin WITH CHECK (true);
CREATE POLICY usuario_admin_estado ON nucleo_comun.usuario FOR UPDATE TO rol_app_admin
USING (NOT EXISTS (SELECT 1 FROM nucleo_comun.usuario_rol r WHERE r.usuario_id = id AND r.rol = 'CIUDADANO'))
WITH CHECK (true);
CREATE POLICY roles_admin_alta ON nucleo_comun.usuario_rol FOR INSERT TO rol_app_admin
WITH CHECK (rol IN ('MEDIADOR','JUEZ','ADMINISTRADOR'));
COMMIT;
