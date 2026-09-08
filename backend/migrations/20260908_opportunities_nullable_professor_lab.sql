-- Make opportunity professor and lab references nullable so university-wide
-- (and lab-only) opportunities can be stored without fabricating a professor.
-- DROP NOT NULL is a no-op if the column is already nullable.

ALTER TABLE opportunities
  ALTER COLUMN professor_id DROP NOT NULL;

ALTER TABLE opportunities
  ALTER COLUMN lab_id DROP NOT NULL;
