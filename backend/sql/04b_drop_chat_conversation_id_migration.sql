-- Remove obsolete local/Dify conversation identifiers.
-- db_init.py logs and skips an ALTER statement when that legacy column is absent.
ALTER TABLE chat_sessions
    DROP COLUMN conversation_id;

ALTER TABLE chat_sessions
    DROP COLUMN dify_conversation_id;
