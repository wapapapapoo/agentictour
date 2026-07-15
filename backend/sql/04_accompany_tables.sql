-- =========================
-- 1. 行程项表
-- =========================
CREATE TABLE IF NOT EXISTS itinerary_items (
    itinerary_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '行程ID',

    trip_id BIGINT NOT NULL COMMENT '旅行ID，对应 trips.id',

    title VARCHAR(100) NOT NULL COMMENT '行程标题',
    place_name VARCHAR(100) NOT NULL COMMENT '地点名称',

    start_time DATETIME NOT NULL COMMENT '开始时间',
    end_time DATETIME NOT NULL COMMENT '结束时间',

    itinerary_type VARCHAR(20) NOT NULL DEFAULT 'play' COMMENT '行程类型：transit/play',
    reminder_time DATETIME DEFAULT NULL COMMENT '提醒时间',
    is_initial TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否为当天初始行程',
    reminded_at DATETIME DEFAULT NULL COMMENT '实际提醒时间',

    status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '行程状态：pending/done/cancelled',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    KEY idx_itinerary_trip_id (trip_id),
    KEY idx_itinerary_trip_time (trip_id, start_time),

    CONSTRAINT fk_itinerary_trip
        FOREIGN KEY (trip_id) REFERENCES trips(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='行程项表';



-- =========================
-- 2. AI建议表
-- =========================
CREATE TABLE IF NOT EXISTS ai_advice (
    advice_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'AI建议ID',

    trip_id BIGINT NOT NULL COMMENT '旅行ID，对应 trips.id',

    reason_text TEXT DEFAULT NULL COMMENT '建议原因',
    advice_text TEXT NOT NULL COMMENT 'AI建议内容',

    advice_type VARCHAR(30) NOT NULL DEFAULT 'recommendation' COMMENT '建议类别',
    parent_advice_id BIGINT DEFAULT NULL COMMENT '上一版推荐ID',
    input_text TEXT DEFAULT NULL COMMENT '生成本建议时的输入',
    proposed_itinerary_json LONGTEXT DEFAULT NULL COMMENT '待用户确认的行程JSON',

    result VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '处理结果：pending/accepted/rejected/revising',
    audit_status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '审核状态',
    audit_reason TEXT DEFAULT NULL COMMENT '审核说明',
    generation_stopped TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否停止继续生成',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    KEY idx_ai_advice_trip_id (trip_id),
    KEY idx_ai_advice_parent (parent_advice_id),

    CONSTRAINT fk_ai_advice_trip
        FOREIGN KEY (trip_id) REFERENCES trips(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_ai_advice_parent
        FOREIGN KEY (parent_advice_id) REFERENCES ai_advice(advice_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI建议表';



-- =========================
-- 3. 备忘录表
-- =========================
CREATE TABLE IF NOT EXISTS memos (
    memo_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '备忘录ID',

    trip_id BIGINT NOT NULL COMMENT '旅行ID，对应 trips.id',

    memo_text TEXT NOT NULL COMMENT '备忘录内容',

    reminder_time DATETIME DEFAULT NULL COMMENT '用户设置的提醒时间',
    reminded_at DATETIME DEFAULT NULL COMMENT '实际提醒时间',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    KEY idx_memos_trip_id (trip_id),

    CONSTRAINT fk_memo_trip
        FOREIGN KEY (trip_id) REFERENCES trips(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='备忘录表';



-- =========================
-- 4. 会话表
-- =========================
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '会话ID',

    trip_id BIGINT NOT NULL COMMENT '旅行ID，对应 trips.id',
    user_id BIGINT NOT NULL COMMENT '用户ID，对应 users.user_id',

    title VARCHAR(100) DEFAULT NULL COMMENT '会话标题',

    status VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT '会话状态：active/closed/deleted',

    last_message_at DATETIME DEFAULT NULL COMMENT '最后一条消息时间',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE KEY uk_chat_session_trip (trip_id),
    KEY idx_chat_sessions_user_id (user_id),

    CONSTRAINT fk_chat_session_trip
        FOREIGN KEY (trip_id) REFERENCES trips(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_chat_session_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='会话表';



-- =========================
-- 5. 对话内容表
-- =========================
CREATE TABLE IF NOT EXISTS chat_messages (
    message_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '消息ID',

    session_id BIGINT NOT NULL COMMENT '会话ID，对应 chat_sessions.session_id',

    sender_type VARCHAR(20) NOT NULL COMMENT '发送方类型：user/ai/system',

    content TEXT NOT NULL COMMENT '消息内容',

    message_order INT NOT NULL COMMENT '消息顺序，用于保证同一会话内消息排序',

    audit_status VARCHAR(20) DEFAULT 'pass' COMMENT '审核状态：pass/failed/pending',
    audit_reason TEXT DEFAULT NULL COMMENT '审核说明或失败原因',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    KEY idx_chat_messages_session_id (session_id),
    KEY idx_chat_messages_created_at (created_at),
    UNIQUE KEY uk_chat_message_order (session_id, message_order),

    CONSTRAINT fk_chat_message_session
        FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='对话内容表';

CREATE TABLE IF NOT EXISTS notifications (
    notification_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    trip_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL COMMENT '用户ID，对应 users.user_id',
    advice_id BIGINT DEFAULT NULL,
    category VARCHAR(30) NOT NULL,
    content TEXT NOT NULL,
    read_at DATETIME DEFAULT NULL COMMENT 'UTC',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'UTC',
    KEY idx_notifications_unread (user_id, read_at, created_at),
    CONSTRAINT fk_notification_trip FOREIGN KEY (trip_id)
        REFERENCES trips(id) ON DELETE CASCADE,
    CONSTRAINT fk_notification_user FOREIGN KEY (user_id)
        REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_notification_advice FOREIGN KEY (advice_id)
        REFERENCES ai_advice(advice_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户通知表';

CREATE TABLE IF NOT EXISTS agent_job_states (
    job_name VARCHAR(50) PRIMARY KEY,
    last_run_at DATETIME DEFAULT NULL COMMENT 'UTC'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Agent周期任务状态';

CREATE TABLE IF NOT EXISTS user_locations (
    user_id BIGINT PRIMARY KEY COMMENT '用户ID，对应 users.user_id',
    latitude DOUBLE NOT NULL,
    longitude DOUBLE NOT NULL,
    city VARCHAR(100) DEFAULT NULL,
    place_name VARCHAR(200) DEFAULT NULL,
    location_context TEXT DEFAULT NULL,
    updated_at DATETIME NOT NULL COMMENT 'UTC',
    KEY idx_user_locations_updated (updated_at),
    CONSTRAINT fk_user_location_user FOREIGN KEY (user_id)
        REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户最新位置';
