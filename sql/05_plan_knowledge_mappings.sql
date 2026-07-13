CREATE TABLE IF NOT EXISTS plan_knowledge_mappings (
    id              BIGINT          PRIMARY KEY AUTO_INCREMENT,
    plan_id         BIGINT          NOT NULL,
    version_id      BIGINT          NOT NULL,
    user_id         VARCHAR(64)     NOT NULL,
    dataset_id      VARCHAR(100)    NOT NULL,
    document_id     VARCHAR(100)    NULL,
    document_name   VARCHAR(255)    NOT NULL,
    batch           VARCHAR(100)    NULL,
    humanized_text  TEXT            NOT NULL,
    indexing_status VARCHAR(50)     NOT NULL DEFAULT 'waiting',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_knowledge_plan
        FOREIGN KEY (plan_id) REFERENCES trip_plan_requests(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_knowledge_version
        FOREIGN KEY (version_id) REFERENCES trip_plan_versions(id)
        ON DELETE CASCADE
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
