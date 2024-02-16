-- upgrade --
ALTER TABLE "bot" ADD "enable_always_second_message" BOOL NOT NULL  DEFAULT False;
-- downgrade --
ALTER TABLE "bot" DROP COLUMN "enable_always_second_message";
