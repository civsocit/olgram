-- upgrade --
ALTER TABLE "bot" ADD "enable_mailing" BOOL NOT NULL  DEFAULT False;
ALTER TABLE "bot" ADD "last_mailing_at" TIMESTAMPTZ;
-- downgrade --
ALTER TABLE "bot" DROP COLUMN "enable_mailing";
ALTER TABLE "bot" DROP COLUMN "last_mailing_at";
