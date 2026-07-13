-- =========================
-- 1. 行程项表
-- =========================
CREATE TABLE IF NOT EXISTS itinerary_items (
    itinerary_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '行程ID',

    tour_id BIGINT NOT NULL COMMENT '旅行计划ID，对应 trip_plan_requests.id',

    title VARCHAR(100) NOT NULL COMMENT '行程标题',
    place_name VARCHAR(100) NOT NULL COMMENT '地点名称',

    start_time DATETIME DEFAULT NULL COMMENT '开始时间',
    end_time DATETIME DEFAULT NULL COMMENT '结束时间',

    status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '行程状态：pending/done/cancelled',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    KEY idx_itinerary_tour_id (tour_id),
    KEY idx_itinerary_time (tour_id, start_time),

    CONSTRAINT fk_itinerary_tour
        FOREIGN KEY (tour_id) REFERENCES trip_plan_requests(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='行程项表';



-- =========================
-- 2. AI建议表
-- =========================
CREATE TABLE IF NOT EXISTS ai_advice (
    advice_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'AI建议ID',

    tour_id BIGINT NOT NULL COMMENT '旅行计划ID，对应 trip_plan_requests.id',

    reason_text TEXT DEFAULT NULL COMMENT '建议原因',
    advice_text TEXT NOT NULL COMMENT 'AI建议内容',

    result VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '处理结果：pending/accepted/rejected/revising',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    KEY idx_ai_advice_tour_id (tour_id),

    CONSTRAINT fk_ai_advice_tour
        FOREIGN KEY (tour_id) REFERENCES trip_plan_requests(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI建议表';



-- =========================
-- 3. 备忘录表
-- =========================
CREATE TABLE IF NOT EXISTS memos (
    memo_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '备忘录ID',

    tour_id BIGINT NOT NULL COMMENT '旅行计划ID，对应 trip_plan_requests.id',

    memo_text TEXT NOT NULL COMMENT '备忘录内容',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    KEY idx_memos_tour_id (tour_id),

    CONSTRAINT fk_memo_tour
        FOREIGN KEY (tour_id) REFERENCES trip_plan_requests(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='备忘录表';



-- =========================
-- 4. 会话表
-- =========================
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '会话ID',

    tour_id BIGINT NOT NULL COMMENT '旅行计划ID，对应 trip_plan_requests.id',
    user_id BIGINT NOT NULL COMMENT '用户ID，对应 users.user_id',

    title VARCHAR(100) DEFAULT NULL COMMENT '会话标题',

    status VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT '会话状态：active/closed/deleted',

    last_message_at DATETIME DEFAULT NULL COMMENT '最后一条消息时间',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE KEY uk_chat_session_tour (tour_id),
    KEY idx_chat_sessions_user_id (user_id),

    CONSTRAINT fk_chat_session_tour
        FOREIGN KEY (tour_id) REFERENCES trip_plan_requests(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_chat_session_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
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