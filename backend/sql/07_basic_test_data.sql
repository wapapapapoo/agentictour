-- ============================================================
-- AgenticTour 基础测试数据（MySQL 8.4）
--
-- 前置条件：请先依次执行以下建表脚本：
--   1. 01_user_tables.sql
--   2. 02_blog_tables.sql
--   3. 03_trip_plan_tables.sql
--   4. 03a_trips_table.sql
--   5. 04_accompany_tables.sql
--   6. 06_plan_knowledge_mappings.sql
--
-- 特性：
--   1. 使用 seed-user-001 / seed-user-002 标识测试数据；
--   2. 可重复执行，每次会重建这两个测试账号关联的业务数据；
--   3. 不会清理其他用户或业务数据。
-- ============================================================

SET NAMES utf8mb4;
SET time_zone = '+08:00';

START TRANSACTION;

-- ------------------------------------------------------------
-- 1. 测试用户
-- 密码哈希字段暂存 SHA-256 测试值；项目接入认证模块后应替换为认证模块使用的算法。
-- 两个测试账号的明文测试密码均为：Test@123456
-- ------------------------------------------------------------
INSERT INTO users (
    username, password_hash, nickname, phone, email, status, created_at, updated_at
) VALUES (
    'seed-user-001', SHA2('Test@123456', 256), '旅行体验官小林',
    '13800000001', 'seed-user-001@example.com', 'active',
    '2026-06-01 09:00:00', '2026-07-01 09:00:00'
)
ON DUPLICATE KEY UPDATE
    user_id = LAST_INSERT_ID(user_id),
    password_hash = VALUES(password_hash),
    nickname = VALUES(nickname),
    phone = VALUES(phone),
    email = VALUES(email),
    status = VALUES(status),
    updated_at = VALUES(updated_at);
SET @seed_user_1_id = LAST_INSERT_ID();

INSERT INTO users (
    username, password_hash, nickname, phone, email, status, created_at, updated_at
) VALUES (
    'seed-user-002', SHA2('Test@123456', 256), '慢游达人阿宁',
    '13800000002', 'seed-user-002@example.com', 'active',
    '2026-06-02 10:00:00', '2026-07-02 10:00:00'
)
ON DUPLICATE KEY UPDATE
    user_id = LAST_INSERT_ID(user_id),
    password_hash = VALUES(password_hash),
    nickname = VALUES(nickname),
    phone = VALUES(phone),
    email = VALUES(email),
    status = VALUES(status),
    updated_at = VALUES(updated_at);
SET @seed_user_2_id = LAST_INSERT_ID();

-- 清理上一次执行生成的业务数据。下级记录由外键 ON DELETE CASCADE 自动清理。
DELETE FROM blog_materials
WHERE user_id IN (@seed_user_1_id, @seed_user_2_id);

DELETE FROM trips
WHERE user_id IN (@seed_user_1_id, @seed_user_2_id);

DELETE FROM trip_plan_requests
WHERE user_id IN ('seed-user-001', 'seed-user-002');

-- ------------------------------------------------------------
-- 2. 旅行计划请求
-- ------------------------------------------------------------
INSERT INTO trip_plan_requests (
    user_id, action, origin_city, destination_city,
    start_date, end_date, people_count, budget_total,
    interests, hotel_level, transport_preference, pace,
    special_requirements, created_at, updated_at
) VALUES (
    'seed-user-001', 'create', '杭州', '上海',
    '2026-07-20', '2026-07-22', '2', '5000元',
    '城市漫步、历史建筑、本地美食、摄影', '舒适型', '高铁+地铁，必要时打车', '轻松',
    '同行者膝盖不适，单日步行尽量控制在8000步以内。',
    '2026-07-01 09:10:00', '2026-07-01 10:00:00'
);
SET @plan_request_1_id = LAST_INSERT_ID();

INSERT INTO trip_plan_requests (
    user_id, action, origin_city, destination_city,
    start_date, end_date, people_count, budget_total,
    interests, hotel_level, transport_preference, pace,
    special_requirements, created_at, updated_at
) VALUES (
    'seed-user-002', 'create', '南京', '苏州',
    '2026-08-08', '2026-08-10', '3', '4200元',
    '园林、昆曲、江南美食、亲子体验', '经济型/舒适型', '高铁+公共交通', '普通',
    '有一名8岁儿童，希望午后预留休息时间。',
    '2026-07-02 10:10:00', '2026-07-02 10:20:00'
);
SET @plan_request_2_id = LAST_INSERT_ID();

-- ------------------------------------------------------------
-- 3. 旅行计划版本
-- 第一条计划包含两个版本，可用于验证“获取最新版本”逻辑。
-- ------------------------------------------------------------
INSERT INTO trip_plan_versions (
    request_id, user_id, version_no, revision_request,
    workflow_run_id, task_id, plan_json, raw_response_json, created_at
) VALUES (
    @plan_request_1_id, 'seed-user-001', 1, NULL,
    'seed-workflow-shanghai-v1', 'seed-task-shanghai-v1',
    JSON_OBJECT(
        'title', '上海经典慢游 3 日计划（初版）',
        'summary', '从杭州出发，覆盖外滩、豫园、武康路等经典区域。',
        'days', JSON_ARRAY(
            JSON_OBJECT('day', 1, 'date', '2026-07-20', 'theme', '外滩与城市天际线'),
            JSON_OBJECT('day', 2, 'date', '2026-07-21', 'theme', '老城厢与海派文化'),
            JSON_OBJECT('day', 3, 'date', '2026-07-22', 'theme', '梧桐区慢生活')
        ),
        'budget', JSON_OBJECT('transport', 900, 'hotel', 1600, 'food', 1200, 'tickets', 400, 'other', 500, 'total', 4600),
        'warnings', JSON_ARRAY('暑期出行建议提前预约热门场馆。'),
        'route_summary', JSON_OBJECT('transport', '高铁+地铁', 'estimated_steps_per_day', '10000步')
    ),
    JSON_OBJECT('workflow_run_id', 'seed-workflow-shanghai-v1', 'status', 'succeeded', 'source', 'seed'),
    '2026-07-01 09:15:00'
), (
    @plan_request_1_id, 'seed-user-001', 2, '减少步行，增加休息点，并把每日步数控制在8000步以内。',
    'seed-workflow-shanghai-v2', 'seed-task-shanghai-v2',
    JSON_OBJECT(
        'title', '上海舒适慢游 3 日计划',
        'summary', '在初版基础上缩短步行距离，增加咖啡馆和酒店休息时段。',
        'days', JSON_ARRAY(
            JSON_OBJECT('day', 1, 'date', '2026-07-20', 'theme', '外滩轻松游', 'rest', '15:00 酒店休息'),
            JSON_OBJECT('day', 2, 'date', '2026-07-21', 'theme', '豫园与博物馆', 'rest', '14:30 茶馆休息'),
            JSON_OBJECT('day', 3, 'date', '2026-07-22', 'theme', '武康路短线漫步', 'rest', '午后返程')
        ),
        'budget', JSON_OBJECT('transport', 1100, 'hotel', 1600, 'food', 1200, 'tickets', 400, 'other', 500, 'total', 4800),
        'warnings', JSON_ARRAY('豫园建议避开周末上午客流高峰。', '如有不适可将步行路段改为打车。'),
        'route_summary', JSON_OBJECT('transport', '高铁+地铁+短途打车', 'estimated_steps_per_day', '6500-8000步')
    ),
    JSON_OBJECT('workflow_run_id', 'seed-workflow-shanghai-v2', 'status', 'succeeded', 'source', 'seed'),
    '2026-07-01 10:00:00'
), (
    @plan_request_2_id, 'seed-user-002', 1, NULL,
    'seed-workflow-suzhou-v1', 'seed-task-suzhou-v1',
    JSON_OBJECT(
        'title', '苏州园林亲子 3 日计划',
        'summary', '以园林、古城和亲子文化体验为主，午后安排休息。',
        'days', JSON_ARRAY(
            JSON_OBJECT('day', 1, 'date', '2026-08-08', 'theme', '拙政园与苏州博物馆'),
            JSON_OBJECT('day', 2, 'date', '2026-08-09', 'theme', '平江路与昆曲体验'),
            JSON_OBJECT('day', 3, 'date', '2026-08-10', 'theme', '虎丘与返程')
        ),
        'budget', JSON_OBJECT('transport', 700, 'hotel', 1200, 'food', 1000, 'tickets', 600, 'other', 400, 'total', 3900),
        'warnings', JSON_ARRAY('园林门票建议提前预约。', '高温天气注意儿童防晒补水。'),
        'route_summary', JSON_OBJECT('transport', '高铁+公交+步行', 'estimated_steps_per_day', '8000步')
    ),
    JSON_OBJECT('workflow_run_id', 'seed-workflow-suzhou-v1', 'status', 'succeeded', 'source', 'seed'),
    '2026-07-02 10:20:00'
);

-- ------------------------------------------------------------
-- 4. 旅行主记录
-- 与上面的计划测试数据表达同一旅行，但本脚本不建立数据库层关联。
-- ------------------------------------------------------------
INSERT INTO trips (
    user_id, title, origin_city, destination_city,
    start_date, end_date, timezone, status, created_at, updated_at
) VALUES (
    @seed_user_1_id, '上海舒适慢游 3 日计划', '杭州', '上海',
    '2026-07-20', '2026-07-22', 'Asia/Shanghai', 'planned',
    '2026-07-01 09:10:00', '2026-07-01 10:00:00'
);
SET @trip_1_id = LAST_INSERT_ID();

INSERT INTO trips (
    user_id, title, origin_city, destination_city,
    start_date, end_date, timezone, status, created_at, updated_at
) VALUES (
    @seed_user_2_id, '苏州园林亲子 3 日计划', '南京', '苏州',
    '2026-08-08', '2026-08-10', 'Asia/Shanghai', 'planned',
    '2026-07-02 10:10:00', '2026-07-02 10:20:00'
);
SET @trip_2_id = LAST_INSERT_ID();

-- ------------------------------------------------------------
-- 5. 行程项
-- ------------------------------------------------------------
INSERT INTO itinerary_items (
    trip_id, title, place_name, start_time, end_time, status, created_at, updated_at
) VALUES
(@trip_1_id, '抵达上海并办理入住', '上海虹桥站', '2026-07-20 10:00:00', '2026-07-20 11:30:00', 'done',      '2026-07-01 10:01:00', '2026-07-20 11:30:00'),
(@trip_1_id, '外滩观景',             '外滩',       '2026-07-20 16:30:00', '2026-07-20 18:30:00', 'pending',   '2026-07-01 10:01:00', '2026-07-01 10:01:00'),
(@trip_1_id, '豫园与老城厢',         '豫园',       '2026-07-21 09:30:00', '2026-07-21 12:00:00', 'pending',   '2026-07-01 10:01:00', '2026-07-01 10:01:00'),
(@trip_1_id, '武康路短线漫步',       '武康大楼',   '2026-07-22 09:30:00', '2026-07-22 11:30:00', 'pending',   '2026-07-01 10:01:00', '2026-07-01 10:01:00'),
(@trip_2_id, '参观拙政园',           '拙政园',     '2026-08-08 08:30:00', '2026-08-08 11:00:00', 'pending',   '2026-07-02 10:21:00', '2026-07-02 10:21:00'),
(@trip_2_id, '平江路文化体验',       '平江路',     '2026-08-09 09:30:00', '2026-08-09 12:00:00', 'pending',   '2026-07-02 10:21:00', '2026-07-02 10:21:00'),
(@trip_2_id, '原定夜游活动',         '山塘街',     '2026-08-09 19:00:00', '2026-08-09 21:00:00', 'cancelled', '2026-07-02 10:21:00', '2026-07-05 18:00:00');

-- ------------------------------------------------------------
-- 6. AI 建议与备忘录
-- ------------------------------------------------------------
INSERT INTO ai_advice (
    trip_id, reason_text, advice_text, result, created_at, updated_at
) VALUES
(@trip_1_id, '检测到同行者膝盖不适，原行程步行距离偏长。', '将田子坊替换为酒店休息，并在外滩行程后安排打车返回。', 'accepted', '2026-07-01 09:40:00', '2026-07-01 09:50:00'),
(@trip_1_id, '7月上海午后可能炎热。', '室外行程尽量安排在上午或傍晚，午后优先参观室内场馆。', 'pending', '2026-07-01 10:05:00', '2026-07-01 10:05:00'),
(@trip_2_id, '亲子出行且天气炎热。', '随身准备儿童防晒用品和饮用水，每日下午安排至少一小时休息。', 'accepted', '2026-07-02 10:25:00', '2026-07-02 10:30:00'),
(@trip_2_id, '山塘街夜间客流较大。', '可改为酒店附近散步，避免儿童过度疲劳。', 'rejected', '2026-07-02 10:26:00', '2026-07-05 18:00:00');

INSERT INTO memos (trip_id, memo_text, created_at, updated_at) VALUES
(@trip_1_id, '提前购买杭州东至上海虹桥往返高铁票。', '2026-07-01 10:10:00', '2026-07-01 10:10:00'),
(@trip_1_id, '携带护膝、常用药和轻便雨伞。',             '2026-07-01 10:11:00', '2026-07-01 10:11:00'),
(@trip_2_id, '预约拙政园与苏州博物馆上午场。',         '2026-07-02 10:31:00', '2026-07-02 10:31:00');

-- ------------------------------------------------------------
-- 7. 会话与消息
-- ------------------------------------------------------------
INSERT INTO chat_sessions (
    trip_id, user_id, title, status, last_message_at, created_at, updated_at
) VALUES (
    @trip_1_id, @seed_user_1_id, '上海慢游计划调整', 'active',
    '2026-07-01 10:00:00', '2026-07-01 09:30:00', '2026-07-01 10:00:00'
);
SET @session_1_id = LAST_INSERT_ID();

INSERT INTO chat_sessions (
    trip_id, user_id, title, status, last_message_at, created_at, updated_at
) VALUES (
    @trip_2_id, @seed_user_2_id, '苏州亲子行程咨询', 'closed',
    '2026-07-02 10:30:00', '2026-07-02 10:22:00', '2026-07-02 10:30:00'
);
SET @session_2_id = LAST_INSERT_ID();

INSERT INTO chat_messages (
    session_id, sender_type, content, message_order,
    audit_status, audit_reason, created_at, updated_at
) VALUES
(@session_1_id, 'system', '已基于您的需求生成上海3日行程。',                         1, 'pass',    NULL,                         '2026-07-01 09:30:00', '2026-07-01 09:30:00'),
(@session_1_id, 'user',   '同行者膝盖不太舒服，请减少步行并增加休息点。',             2, 'pass',    NULL,                         '2026-07-01 09:35:00', '2026-07-01 09:35:00'),
(@session_1_id, 'ai',     '好的，我会缩短步行路线，并增加酒店、茶馆等休息安排。',       3, 'pass',    NULL,                         '2026-07-01 09:36:00', '2026-07-01 09:36:00'),
(@session_1_id, 'user',   '预算尽量控制在5000元以内。',                               4, 'pass',    NULL,                         '2026-07-01 09:55:00', '2026-07-01 09:55:00'),
(@session_1_id, 'ai',     '调整后的预估总费用为4800元，并保留约200元机动预算。',         5, 'pass',    NULL,                         '2026-07-01 10:00:00', '2026-07-01 10:00:00'),
(@session_2_id, 'user',   '孩子不喜欢行程太赶，下午能安排休息吗？',                     1, 'pass',    NULL,                         '2026-07-02 10:22:00', '2026-07-02 10:22:00'),
(@session_2_id, 'ai',     '可以，三天行程均已在午后预留休息时间。',                     2, 'pass',    NULL,                         '2026-07-02 10:23:00', '2026-07-02 10:23:00'),
(@session_2_id, 'user',   '请帮我购买景区黄牛票。',                                   3, 'failed',  '请求涉及非官方票务渠道，存在风险。', '2026-07-02 10:28:00', '2026-07-02 10:28:00'),
(@session_2_id, 'ai',     '建议通过景区官方平台或正规旅行平台预约门票。',               4, 'pass',    NULL,                         '2026-07-02 10:30:00', '2026-07-02 10:30:00');

-- ------------------------------------------------------------
-- 8. 博客素材与生成结果
-- ------------------------------------------------------------
INSERT INTO blog_materials (
    user_id, title, destination, start_date, end_date, people_count,
    itinerary_text, food_text, photo_text, expense_text, feeling_text,
    created_at, updated_at
) VALUES (
    @seed_user_1_id, '上海周末慢游记录', '上海', '2026-06-20', '2026-06-22', 2,
    '第一天游览外滩和南京东路；第二天参观豫园与上海博物馆；第三天漫步武康路。',
    '尝试了生煎、小笼包和葱油拌面，最喜欢街边老店的生煎。',
    '外滩夜景、豫园屋檐细节、武康大楼和梧桐树下的街景。',
    '交通约600元，住宿1500元，餐饮900元，门票及其他约500元。',
    '节奏放慢后体验很好，公共交通方便，但热门景点周末游客较多。',
    '2026-06-23 09:00:00', '2026-06-23 09:30:00'
);
SET @material_1_id = LAST_INSERT_ID();

INSERT INTO blog_materials (
    user_id, title, destination, start_date, end_date, people_count,
    itinerary_text, food_text, photo_text, expense_text, feeling_text,
    created_at, updated_at
) VALUES (
    @seed_user_2_id, '带孩子逛苏州园林', '苏州', '2026-05-01', '2026-05-03', 3,
    '游览拙政园、苏州博物馆、平江路和虎丘，每天下午回酒店休息。',
    '吃了苏式汤面、松鼠桂鱼和海棠糕，孩子很喜欢海棠糕。',
    '园林漏窗、博物馆白墙倒影、平江路小桥和昆曲体验照片。',
    '三人总消费约3900元，其中住宿和餐饮占比最高。',
    '亲子行程不要安排太满，提前预约和午休让旅行轻松很多。',
    '2026-05-04 14:00:00', '2026-05-04 14:20:00'
);
SET @material_2_id = LAST_INSERT_ID();

INSERT INTO blog_generations (
    material_id, user_id, content_type, writing_style,
    generated_title, generated_content, tags, risk_note, created_at
) VALUES
(
    @material_1_id, @seed_user_1_id, 'blog', 'guide',
    '上海慢游三日攻略：经典地标与梧桐区路线',
    '# 上海慢游三日攻略\n\n这次用三天走访外滩、豫园和武康路。路线特意留出休息时间，适合希望轻松旅行的人。\n\n## 行程亮点\n傍晚看外滩夜景，上午逛老城厢，最后一天在梧桐区慢慢散步。\n\n## 实用建议\n热门场馆提前预约，周末尽量错峰出行。',
    '上海,三日游,城市漫步,美食,旅行攻略',
    '开放时间与票价可能变化，发布前请以景区官方信息为准。',
    '2026-06-23 09:35:00'
),
(
    @material_1_id, @seed_user_1_id, 'social_post', 'casual',
    '周末去上海，慢一点反而更好玩',
    '上海三天两晚轻松打卡完成！外滩夜景很惊喜，武康路也很适合散步拍照。没有把行程排满，累了就找家咖啡馆坐一会儿，旅行体验反而更好。',
    '上海旅行,周末去哪儿,城市漫步,轻松出行',
    NULL,
    '2026-06-23 09:40:00'
),
(
    @material_2_id, @seed_user_2_id, 'title_tags', 'promotion',
    '带孩子逛苏州：这份园林亲子路线请收好',
    '标题建议：\n1. 带孩子逛苏州园林，三天轻松不赶路\n2. 苏州亲子游实测：预约和午休真的很重要\n3. 园林、昆曲与苏式点心，一次孩子也喜欢的苏州行',
    '苏州,亲子游,园林,昆曲,江南旅行',
    '亲子体验因年龄和体力而异，请结合实际情况调整行程。',
    '2026-05-04 14:25:00'
);

-- Hikari Atlas UTC/reminder/advice-pair/notification seed extension.
UPDATE chat_sessions AS session
JOIN trips AS trip ON trip.id = session.trip_id
SET session.user_id = trip.user_id
WHERE session.trip_id IN (@trip_1_id, @trip_2_id);

UPDATE itinerary_items
SET itinerary_type = 'play', reminder_time = start_time,
    is_initial = 1, reminded_at = NULL
WHERE trip_id IN (@trip_1_id, @trip_2_id);

UPDATE itinerary_items AS current_item
JOIN itinerary_items AS previous_item
  ON previous_item.trip_id = current_item.trip_id
 AND DATE(previous_item.start_time) = DATE(current_item.start_time)
 AND previous_item.start_time < current_item.start_time
SET current_item.is_initial = 0,
    current_item.reminder_time = CASE
        WHEN TIMESTAMPDIFF(MINUTE, previous_item.start_time, previous_item.end_time) >= 20
            THEN DATE_SUB(previous_item.end_time, INTERVAL 20 MINUTE)
        WHEN TIMESTAMPDIFF(MINUTE, previous_item.start_time, previous_item.end_time) >= 5
            THEN DATE_SUB(previous_item.end_time, INTERVAL 5 MINUTE)
        ELSE previous_item.end_time
    END;

UPDATE ai_advice
SET advice_type = 'replan', input_text = reason_text,
    audit_status = 'pass', generation_stopped = (result = 'rejected')
WHERE trip_id IN (@trip_1_id, @trip_2_id);

UPDATE ai_advice AS revised
JOIN (
    SELECT trip_id, MIN(advice_id) AS original_advice_id
    FROM ai_advice
    WHERE trip_id IN (@trip_1_id, @trip_2_id)
    GROUP BY trip_id
) AS original ON original.trip_id = revised.trip_id
SET revised.parent_advice_id = original.original_advice_id,
    revised.input_text = CONCAT(
        '原输入：', revised.reason_text, '\n',
        '原建议：示例旧建议\n',
        '用户新要求：请进一步调整'
    )
WHERE revised.advice_id <> original.original_advice_id;

UPDATE memos
SET reminder_time = CASE memo_id % 2
    WHEN 0 THEN NULL
    ELSE '2026-07-20 00:30:00'
END,
reminded_at = NULL
WHERE trip_id IN (@trip_1_id, @trip_2_id);

INSERT INTO notifications (
    trip_id, user_id, advice_id, category, content, read_at, created_at
)
SELECT a.trip_id, trip.user_id, a.advice_id, 'replan', a.advice_text, NULL, a.created_at
FROM ai_advice AS a
JOIN trips AS trip ON trip.id = a.trip_id
WHERE a.trip_id IN (@trip_1_id, @trip_2_id);

INSERT INTO agent_job_states (job_name, last_run_at) VALUES
('hourly_itinerary_check', '2026-07-13 00:00:00'),
('three_hour_proactive', '2026-07-13 00:00:00');

INSERT INTO user_locations (
    user_id, latitude, longitude, city, place_name, location_context, updated_at
) VALUES
(@seed_user_1_id, 31.2400, 121.4900, '上海', '外滩', '前端最近一次上报位置', '2026-07-13 00:00:00'),
(@seed_user_2_id, 31.3240, 120.6290, '苏州', '平江路', '前端最近一次上报位置', '2026-07-13 00:00:00');

COMMIT;

-- ------------------------------------------------------------
-- 9. 执行结果概览
-- ------------------------------------------------------------
SELECT 'users' AS table_name, COUNT(*) AS seed_row_count
FROM users WHERE username IN ('seed-user-001', 'seed-user-002')
UNION ALL
SELECT 'trip_plan_requests', COUNT(*) FROM trip_plan_requests WHERE user_id IN ('seed-user-001', 'seed-user-002')
UNION ALL
SELECT 'trip_plan_versions', COUNT(*) FROM trip_plan_versions WHERE user_id IN ('seed-user-001', 'seed-user-002')
UNION ALL
SELECT 'trips', COUNT(*) FROM trips WHERE user_id IN (@seed_user_1_id, @seed_user_2_id)
UNION ALL
SELECT 'itinerary_items', COUNT(*) FROM itinerary_items WHERE trip_id IN (@trip_1_id, @trip_2_id)
UNION ALL
SELECT 'ai_advice', COUNT(*) FROM ai_advice WHERE trip_id IN (@trip_1_id, @trip_2_id)
UNION ALL
SELECT 'memos', COUNT(*) FROM memos WHERE trip_id IN (@trip_1_id, @trip_2_id)
UNION ALL
SELECT 'chat_sessions', COUNT(*) FROM chat_sessions WHERE trip_id IN (@trip_1_id, @trip_2_id)
UNION ALL
SELECT 'chat_messages', COUNT(*) FROM chat_messages WHERE session_id IN (@session_1_id, @session_2_id)
UNION ALL
SELECT 'blog_materials', COUNT(*) FROM blog_materials WHERE user_id IN (@seed_user_1_id, @seed_user_2_id)
UNION ALL
SELECT 'blog_generations', COUNT(*) FROM blog_generations WHERE user_id IN (@seed_user_1_id, @seed_user_2_id);
