-- upgrade --
ALTER TABLE "bot" ADD "enable_tags" BOOL NOT NULL  DEFAULT False;
-- downgrade --
ALTER TABLE "bot" DROP COLUMN "enable_tags";
