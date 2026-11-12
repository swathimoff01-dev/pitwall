SET search_path = pitwall, public;

ALTER TABLE regulation_articles
  ADD COLUMN season       INT  NOT NULL,
  ADD COLUMN issue        INT  NOT NULL,
  ADD COLUMN published_on DATE NOT NULL,
  ADD COLUMN source_file  TEXT;

-- one row per sub-article per season
CREATE UNIQUE INDEX ON regulation_articles (season, article_no);

INSERT INTO data_coverage (table_name, first_season, source, reason, notes) VALUES
('regulation_articles', 2023, 'FIA Formula 1 Sporting Regulations (PDF)',
 'Loaded to match the seasons with detailed race data (2023 onward). One issue per season: the last one published before that season''s final race.',
 'One row per sub-article (e.g. 54.2); title is the parent article title. 2026 uses a renumbered format (Section B) and is planned in Step 16.');