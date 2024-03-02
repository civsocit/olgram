-- upgrade --
CREATE TABLE IF NOT EXISTS "mailinguser" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "telegram_id" BIGINT NOT NULL,
    "bot_id" INT NOT NULL REFERENCES "bot" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_mailinguser_bot_id_906a76" UNIQUE ("bot_id", "telegram_id")
);
CREATE INDEX IF NOT EXISTS "idx_mailinguser_telegra_55de60" ON "mailinguser" ("telegram_id");
-- downgrade --
DROP TABLE IF EXISTS "mailinguser";
