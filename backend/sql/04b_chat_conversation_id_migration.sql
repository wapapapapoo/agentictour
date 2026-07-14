-- Rename legacy Dify-owned conversation ids to locally owned conversation ids.
-- db_init.py logs and skips ALTER/INDEX statements that were already applied.
ALTER TABLE chat_sessions
    CHANGE COLUMN dify_conversation_id conversation_id VARCHAR(100) NULL
    COMMENT '本地会话ID';

UPDATE chat_sessions
SET conversation_id = UUID()
WHERE conversation_id IS NULL OR conversation_id = '';

ALTER TABLE chat_sessions
    MODIFY COLUMN conversation_id VARCHAR(100) NOT NULL DEFAULT (UUID())
    COMMENT '本地会话ID';

CREATE UNIQUE INDEX uk_chat_session_conversation_id
    ON chat_sessions (conversation_id);
