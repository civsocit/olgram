-- upgrade --
ALTER TABLE "bot" ADD "enable_thread_interrupt" BOOL NOT NULL  DEFAULT True;
-- downgrade --
ALTER TABLE "bot" DROP COLUMN "enable_thread_interrupt";
