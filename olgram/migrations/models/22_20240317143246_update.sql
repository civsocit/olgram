-- upgrade --
ALTER TABLE "bot_start_message" ALTER COLUMN "locale" TYPE VARCHAR(15) USING "locale"::VARCHAR(15);
-- downgrade --
ALTER TABLE "bot_start_message" ALTER COLUMN "locale" TYPE VARCHAR(5) USING "locale"::VARCHAR(5);
