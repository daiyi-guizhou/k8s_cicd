-- ============================================================
-- K8s Management Console — 数据库建表 SQL
-- 适用: MySQL 8.0+
-- 最后更新: 2026-07-11
-- ============================================================
-- 本文档记录所有生产环境所需的建库建表 SQL。
-- 每次表结构变动必须同步更新本文档。
-- ============================================================

-- 1. 创建数据库
CREATE DATABASE IF NOT EXISTS appdb
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE appdb;

-- ============================================================
-- 2. 用户表 (auth_app.User)
-- ============================================================
CREATE TABLE IF NOT EXISTS `user` (
    `id`            BIGINT          NOT NULL AUTO_INCREMENT,
    `username`      VARCHAR(150)    NOT NULL,
    `password`      VARCHAR(255)    NOT NULL COMMENT 'Django PBKDF2 hashed password',
    `role`          VARCHAR(20)     NOT NULL DEFAULT 'user' COMMENT 'admin / user',
    `is_active`     TINYINT(1)      NOT NULL DEFAULT 1,
    `created_at`    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    PRIMARY KEY (`id`),
    UNIQUE INDEX `idx_user_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 3. 密码重置 Token 表 (auth_app.PasswordResetToken)
-- ============================================================
CREATE TABLE IF NOT EXISTS `password_reset_token` (
    `id`            BIGINT          NOT NULL AUTO_INCREMENT,
    `user_id`       BIGINT          NOT NULL,
    `token`         VARCHAR(64)     NOT NULL,
    `expires_at`    DATETIME(6)     NOT NULL,
    `used`          TINYINT(1)      NOT NULL DEFAULT 0,

    PRIMARY KEY (`id`),
    INDEX `idx_pwd_reset_user` (`user_id`),
    INDEX `idx_pwd_reset_token` (`token`),
    CONSTRAINT `fk_pwd_reset_user`
        FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 4. 审计日志表 (audit.AuditLog)
--    v1.1 — 2026-07-11: 新增 cluster_name 列
-- ============================================================
CREATE TABLE IF NOT EXISTS `audit_log` (
    `id`              BIGINT          NOT NULL AUTO_INCREMENT,
    `user_id`         BIGINT          NULL,
    `action`          VARCHAR(50)     NOT NULL COMMENT 'scale / rollback / delete / apply / create_user / toggle_active / reset_password / change_password',
    `resource_type`   VARCHAR(50)     NOT NULL,
    `resource_name`   VARCHAR(255)    NOT NULL DEFAULT '',
    `namespace`       VARCHAR(100)    NOT NULL DEFAULT '',
    `cluster_name`    VARCHAR(128)    NOT NULL DEFAULT '' COMMENT '集群名称 (v1.1 新增)',
    `detail`          JSON            NOT NULL COMMENT 'JSON 格式操作详情',
    `result`          VARCHAR(20)     NOT NULL COMMENT 'success / fail',
    `error_msg`       TEXT            NOT NULL DEFAULT '' COMMENT '错误信息',
    `created_at`      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    PRIMARY KEY (`id`),
    INDEX `idx_audit_user`       (`user_id`),
    INDEX `idx_audit_action`     (`action`),
    INDEX `idx_audit_result`     (`result`),
    INDEX `idx_audit_created_at` (`created_at` DESC),
    INDEX `idx_audit_cluster`    (`cluster_name`),
    CONSTRAINT `fk_audit_log_user`
        FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 5. 集群配置表 (clusters.Cluster) — v1.1 新增
-- ============================================================
CREATE TABLE IF NOT EXISTS `cluster` (
    `id`                  BIGINT          NOT NULL AUTO_INCREMENT,
    `name`                VARCHAR(128)    NOT NULL COMMENT '集群名称',
    `description`         TEXT            NOT NULL DEFAULT '' COMMENT '描述',
    `kubeconfig_content`  TEXT            NOT NULL DEFAULT '' COMMENT 'kubeconfig YAML 内容; 留空则使用默认 ~/.kube/config',
    `enabled`             TINYINT(1)      NOT NULL DEFAULT 1 COMMENT '是否启用',
    `created_at`          DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at`          DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    PRIMARY KEY (`id`),
    UNIQUE INDEX `idx_cluster_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 6. Django migration 记录表（Django 框架自动维护）
-- ============================================================
CREATE TABLE IF NOT EXISTS `django_migrations` (
    `id`      BIGINT          NOT NULL AUTO_INCREMENT,
    `app`     VARCHAR(255)    NOT NULL,
    `name`    VARCHAR(255)    NOT NULL,
    `applied` DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 7. 初始管理员账号
--    默认密码: admin (PBKDF2 hashed)
--    首次登录后请立即修改
-- ============================================================
-- INSERT INTO `user` (`username`, `password`, `role`, `is_active`)
-- VALUES ('admin', '<pbkdf2_sha256$...>', 'admin', 1);


-- ============================================================
-- 变更记录
-- ============================================================
-- 2026-07-11  v1.0  初始版本: user, password_reset_token, audit_log, django_migrations
-- 2026-07-11  v1.1  新增 cluster 表; audit_log 新增 cluster_name 列
