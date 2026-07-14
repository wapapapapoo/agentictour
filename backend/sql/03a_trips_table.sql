CREATE TABLE IF NOT EXISTS trips (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '旅行ID',
    user_id BIGINT NOT NULL COMMENT '旅行所属用户ID，对应 users.user_id',
    title VARCHAR(100) NOT NULL COMMENT '旅行标题',
    origin_city VARCHAR(100) NOT NULL COMMENT '出发城市',
    destination_city VARCHAR(100) NOT NULL COMMENT '目的地城市',
    start_date DATE NOT NULL COMMENT '旅行开始日期',
    end_date DATE NOT NULL COMMENT '旅行结束日期',
    timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Shanghai' COMMENT '旅行时区',
    status VARCHAR(20) NOT NULL DEFAULT 'planned'
        COMMENT '旅行状态：planned/ongoing/completed/cancelled',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间（UTC）',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间（UTC）',

    KEY idx_trips_user_status (user_id, status),
    KEY idx_trips_dates (start_date, end_date),
    CONSTRAINT chk_trip_date_range CHECK (end_date >= start_date),
    CONSTRAINT chk_trip_status
        CHECK (status IN ('planned', 'ongoing', 'completed', 'cancelled'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='旅行主表';
