-- ============================================================
-- Migration 0004: Hematology sample questions for 民國 100 年
--
-- The original 0002 seeded off-topic 內科/感染科 board questions.
-- Wipe those and replace with 10 hematology-flavored samples
-- under year=100 (= 2011 CE) — a year that will NEVER appear in
-- the real dataset (104..114), so sample rows can be cleared by
-- a one-liner before real import:
--     DELETE FROM questions WHERE year = 100;
-- ============================================================

DELETE FROM explanation_history;
DELETE FROM explanations;
DELETE FROM question_tags;
DELETE FROM questions;

-- hsct-2026 fork (2026-10-08): the 10 hematology sample rows that used to be
-- inserted here are gone. This bank's real questions come from
-- years/hsct/hsct-<年>.csv via scripts/import-questions.ts (see CLAUDE.md
-- 「題庫來源」), and seeding off-topic hema samples into a fresh production DB
-- would just be rows someone has to remember to delete. The 0002 wipe above is
-- kept so a DB that already ran 0002 ends up empty.
