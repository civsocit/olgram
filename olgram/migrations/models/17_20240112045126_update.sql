-- upgrade --
CREATE TABLE IF NOT EXISTS "bot_second_message" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "locale" VARCHAR(5) NOT NULL,
    "text" TEXT NOT NULL,
    "bot_id" INT NOT NULL REFERENCES "bot" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_bot_second__bot_id_432892" UNIQUE ("bot_id", "locale")
);
-- downgrade --
DROP TABLE IF EXISTS "bot_second_message";
