SET search_path = pitwall, public;

ALTER TABLE laps ADD COLUMN is_pit_out_lap BOOLEAN;
ALTER TABLE stints ADD COLUMN tyre_age_at_start INT;
ALTER TABLE race_control_messages
  ADD COLUMN scope TEXT,
  ADD COLUMN sector INT,
  ADD COLUMN driver_id TEXT REFERENCES drivers;

INSERT INTO data_coverage (table_name, first_season, source, reason, notes) VALUES
('laps', 2023, 'OpenF1 (free public API)',
 'The free OpenF1 archive starts in 2023. Before that, lap-level data exists only in F1''s own live-timing service, which now requires a paid F1 TV subscription whose terms restrict automated bulk access, so this project does not include it.',
 'Race sessions only (no practice, qualifying or sprint). compound, stint_no and tyre_life are derived from stint data. position and is_accurate are not provided by this source and are NULL.'),
('stints', 2023, 'OpenF1 (free public API)',
 'Same as laps: the free source starts in 2023; earlier tyre data is not available to this project.',
 'Race sessions only. tyre_age_at_start is the age of the tyre set, in laps, when the stint began.'),
('race_control_messages', 2023, 'OpenF1 (free public API)',
 'Same as laps: the free source starts in 2023; earlier race control messages are not available to this project.',
 'Race sessions only. driver_id is NULL for messages that are not about one driver.');