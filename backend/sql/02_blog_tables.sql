CREATE TABLE IF NOT EXISTS blog_materials (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '素材ID',
    user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
    title VARCHAR(255) NOT NULL COMMENT '素材标题',
    destination VARCHAR(100) NOT NULL COMMENT '目的地',
    start_date DATE NULL COMMENT '旅行开始日期',
    end_date DATE NULL COMMENT '旅行结束日期',
    people_count INT NULL COMMENT '同行人数',

    itinerary_text TEXT NOT NULL COMMENT '行程记录',
    food_text TEXT NULL COMMENT '美食记录',
    photo_text TEXT NULL COMMENT '照片描述',
    expense_text TEXT NULL COMMENT '消费摘要',
    feeling_text TEXT NULL COMMENT '个人感受',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    KEY idx_blog_materials_user_id (user_id)
) COMMENT='旅游博客素材表';

CREATE TABLE IF NOT EXISTS blog_generations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '生成记录ID',
    material_id BIGINT NOT NULL COMMENT '关联素材ID',
    user_id VARCHAR(64) NOT NULL COMMENT '用户ID',

    content_type VARCHAR(50) NOT NULL COMMENT '生成类型：blog/social_post/title_tags',
    writing_style VARCHAR(50) NOT NULL COMMENT '写作风格：guide/story/casual/promotion',

    generated_title VARCHAR(255) NULL COMMENT '生成标题',
    generated_content TEXT NOT NULL COMMENT '生成正文',
    tags TEXT NULL COMMENT '标签',
    risk_note TEXT NULL COMMENT '风险提示',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    CONSTRAINT fk_blog_generation_material
        FOREIGN KEY (material_id) REFERENCES blog_materials(id)
        ON DELETE CASCADE,

    KEY idx_blog_generations_material_id (material_id),
    KEY idx_blog_generations_user_id (user_id),
    KEY idx_blog_generations_created_at (created_at)
) COMMENT='旅游博客生成结果表';

CREATE TABLE IF NOT EXISTS blog_photos (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '图片ID',
    material_id BIGINT NOT NULL COMMENT '关联素材ID',
    user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
    original_filename VARCHAR(255) NOT NULL COMMENT '原始文件名',
    stored_filename VARCHAR(255) NOT NULL COMMENT '服务器文件名',
    content_type VARCHAR(50) NOT NULL COMMENT '图片类型',
    file_size INT NOT NULL COMMENT '文件大小（字节）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',

    CONSTRAINT fk_blog_photo_material
        FOREIGN KEY (material_id) REFERENCES blog_materials(id)
        ON DELETE CASCADE,

    UNIQUE KEY uk_blog_photos_stored_filename (stored_filename),
    KEY idx_blog_photos_material_id (material_id),
    KEY idx_blog_photos_user_id (user_id)
) COMMENT='旅游博客素材图片表';
