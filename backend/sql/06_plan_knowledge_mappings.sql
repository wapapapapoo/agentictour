CREATE TABLE IF NOT EXISTS plan_knowledge_mappings (
    id              BIGINT          PRIMARY KEY AUTO_INCREMENT,
    plan_id         BIGINT          NOT NULL,
    version_id      BIGINT          NOT NULL,
    user_id         BIGINT          NOT NULL COMMENT '用户ID，对应 users.user_id',
    dataset_id      VARCHAR(100)    NOT NULL,
    document_id     VARCHAR(100)    NULL,
    document_name   VARCHAR(255)    NOT NULL,
    batch           VARCHAR(100)    NULL,
    humanized_text  TEXT            NOT NULL,
    indexing_status VARCHAR(50)     NOT NULL DEFAULT 'waiting',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    KEY idx_plan_knowledge_user_id (user_id),
    CONSTRAINT fk_knowledge_plan
        FOREIGN KEY (plan_id) REFERENCES trip_plan_requests(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_knowledge_version
        FOREIGN KEY (version_id) REFERENCES trip_plan_versions(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_knowledge_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
