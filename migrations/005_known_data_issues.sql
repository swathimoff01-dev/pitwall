SET search_path = pitwall, public;

-- Race-specific data problems, identified by season and race name (not race_id),
-- so this migration works on an empty database before any data is loaded.
CREATE TABLE known_data_issues (
  issue_id    SERIAL PRIMARY KEY,
  table_name  TEXT NOT NULL,
  season      INT  NOT NULL,
  race_name   TEXT NOT NULL,
  description TEXT NOT NULL
);

INSERT INTO known_data_issues (table_name, season, race_name, description) VALUES
('laps', 2025, 'Miami Grand Prix',
 'OpenF1 is missing roughly 23 to 24 laps in the middle of the race for every driver. Lap-level answers for this race are incomplete; results, pit stops, stints and race control are unaffected.');

UPDATE data_coverage
SET notes = notes || ' Where a car stopped, its final untimed lap is stored, so for laps completed use results.laps. Disqualified drivers have results.laps = 0 (Jolpica convention) while laps still holds the laps they drove. Race-specific gaps are listed in known_data_issues.'
WHERE table_name = 'laps';