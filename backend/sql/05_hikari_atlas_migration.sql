-- Run after 04_accompany_tables.sql to upgrade an existing Hikari Atlas database.
-- All DATETIME values use UTC.
ALTER TABLE memos
    ADD COLUMN reminder_time DATETIME NULL AFTER memo_text,
    ADD COLUMN reminded_at DATETIME NULL AFTER reminder_time,
    ADD KEY idx_memos_reminder (reminder_time, reminded_at);

ALTER TABLE itinerary_items
    MODIFY start_time DATETIME NOT NULL,
    MODIFY end_time DATETIME NOT NULL,
    ADD COLUMN itinerary_type VARCHAR(20) NOT NULL DEFAULT 'play' AFTER end_time,
    ADD COLUMN reminder_time DATETIME NULL AFTER itinerary_type,
    ADD COLUMN is_initial TINYINT(1) NOT NULL DEFAULT 0 AFTER reminder_time,
    ADD COLUMN reminded_at DATETIME NULL AFTER is_initial,
    ADD KEY idx_itinerary_reminder (reminder_time, reminded_at),
    ADD CONSTRAINT chk_itinerary_type CHECK (itinerary_type IN ('transit', 'play')),
    ADD CONSTRAINT chk_transit_reminder CHECK (itinerary_type <> 'transit' OR reminder_time IS NOT NULL),
    ADD CONSTRAINT chk_initial_reminder CHECK (is_initial = 0 OR reminder_time = start_time);

ALTER TABLE ai_advice
    ADD COLUMN advice_type VARCHAR(30) NOT NULL DEFAULT 'recommendation' AFTER tour_id,
    ADD COLUMN parent_advice_id BIGINT NULL AFTER advice_type,
    ADD COLUMN input_text TEXT NULL AFTER parent_advice_id,
    ADD COLUMN proposed_itinerary_json LONGTEXT NULL AFTER advice_text,
    ADD COLUMN audit_status VARCHAR(20) NOT NULL DEFAULT 'pending' AFTER result,
    ADD COLUMN audit_reason TEXT NULL AFTER audit_status,
    ADD COLUMN generation_stopped TINYINT(1) NOT NULL DEFAULT 0 AFTER audit_reason,
    ADD KEY idx_ai_advice_parent (parent_advice_id),
    ADD CONSTRAINT fk_ai_advice_parent FOREIGN KEY (parent_advice_id)
        REFERENCES ai_advice(advice_id) ON DELETE SET NULL;

ALTER TABLE chat_sessions
    DROP FOREIGN KEY fk_chat_session_user;

ALTER TABLE chat_sessions
    MODIFY user_id VARCHAR(64) NOT NULL,
    ADD COLUMN dify_conversation_id VARCHAR(100) NULL AFTER status;

CREATE TABLE IF NOT EXISTS notifications (
    notification_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tour_id BIGINT NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    advice_id BIGINT NULL,
    category VARCHAR(30) NOT NULL,
    content TEXT NOT NULL,
    read_at DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    KEY idx_notifications_unread (user_id, read_at, created_at),
    CONSTRAINT fk_notification_tour FOREIGN KEY (tour_id)
        REFERENCES trip_plan_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_notification_advice FOREIGN KEY (advice_id)
        REFERENCES ai_advice(advice_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS agent_job_states (
    job_name VARCHAR(50) PRIMARY KEY,
    last_run_at DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_locations (
    user_id VARCHAR(64) PRIMARY KEY,
    latitude DOUBLE NOT NULL,
    longitude DOUBLE NOT NULL,
    city VARCHAR(100) NULL,
    place_name VARCHAR(200) NULL,
    location_context TEXT NULL,
    updated_at DATETIME NOT NULL,
    KEY idx_user_locations_updated (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
