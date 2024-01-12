-- upgrade --
ALTER TABLE "bot_start_message" ADD "text" TEXT NOT NULL;
-- downgrade --
ALTER TABLE "bot_start_message" DROP COLUMN "text";
