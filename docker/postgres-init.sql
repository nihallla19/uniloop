-- Local development roles mirroring spec section 5.7. Dev-only passwords.
CREATE ROLE baton_migrator LOGIN PASSWORD 'migrator';
CREATE ROLE baton_app LOGIN PASSWORD 'app';

CREATE DATABASE baton OWNER baton_migrator;
CREATE DATABASE baton_test OWNER baton_migrator;
