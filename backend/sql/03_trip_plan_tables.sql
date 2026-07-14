CREATE TABLE IF NOT EXISTS trip_plan_requests (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '行前计划请求ID',
    trip_id BIGINT NOT NULL COMMENT '关联旅行ID，对应 trips.id',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    action VARCHAR(20) NOT NULL DEFAULT 'create' COMMENT '动作：create/revise',

    origin_city VARCHAR(100) NOT NULL COMMENT '出发城市',
    destination_city VARCHAR(100) NOT NULL COMMENT '目的地城市',
    start_date VARCHAR(20) NOT NULL COMMENT '开始日期，按Dify字符串输入保存',
    end_date VARCHAR(20) NOT NULL COMMENT '结束日期，按Dify字符串输入保存',
    people_count VARCHAR(20) NOT NULL COMMENT '人数，按Dify字符串输入保存',
    budget_total VARCHAR(50) NOT NULL COMMENT '总预算，按Dify字符串输入保存',
    interests TEXT NOT NULL COMMENT '兴趣偏好',
    hotel_level VARCHAR(100) NOT NULL COMMENT '住宿标准',
    transport_preference VARCHAR(100) NOT NULL COMMENT '出行方案偏好',
    pace VARCHAR(50) NOT NULL COMMENT '行程节奏',
    special_requirements TEXT NULL COMMENT '特殊要求',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE KEY uk_trip_plan_request_trip (trip_id),
    CONSTRAINT fk_trip_plan_request_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON UPDATE CASCADE,
    CONSTRAINT fk_trip_plan_request_trip
        FOREIGN KEY (trip_id) REFERENCES trips(id)
        ON DELETE CASCADE
) COMMENT='行前旅行计划请求表';

CREATE TABLE IF NOT EXISTS trip_plan_versions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '行前计划版本ID',
    request_id BIGINT NOT NULL COMMENT '关联计划请求ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    version_no INT NOT NULL COMMENT '版本号',
    revision_request TEXT NULL COMMENT '本次修改要求',

    workflow_run_id VARCHAR(100) NULL COMMENT 'Dify workflow_run_id',
    task_id VARCHAR(100) NULL COMMENT 'Dify task_id',
    plan_json LONGTEXT NOT NULL COMMENT '结构化行程计划JSON',
    raw_response_json LONGTEXT NULL COMMENT 'Dify原始返回',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    UNIQUE KEY uk_trip_plan_version (request_id, version_no),
    CONSTRAINT fk_trip_plan_version_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON UPDATE CASCADE,
    CONSTRAINT fk_trip_plan_version_request
        FOREIGN KEY (request_id) REFERENCES trip_plan_requests(id)
        ON DELETE CASCADE
) COMMENT='行前旅行计划版本表';
