-- =====================================================================
-- Lab 2: Login & To-Do Application
-- DDL script for the "registration" database.
-- Re-runnable: it drops and rebuilds the database every time. No data.
-- =====================================================================

DROP DATABASE IF EXISTS registration;
CREATE DATABASE registration;
USE registration;

-- ---------------------------------------------------------------------
-- users: one row per registered account
-- ---------------------------------------------------------------------
CREATE TABLE users (
    user_id           INT          NOT NULL AUTO_INCREMENT,
    email             VARCHAR(255) NOT NULL,
    name              VARCHAR(100) NOT NULL,
    password_hash     VARCHAR(255) NOT NULL,
    registration_date TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    UNIQUE (email)
);

-- ---------------------------------------------------------------------
-- todos: every to-do belongs to exactly one user (foreign key)
-- Created after users, because a table can only reference an
-- existing table.
-- ---------------------------------------------------------------------
CREATE TABLE todos (
    todo_id    INT          NOT NULL AUTO_INCREMENT,
    user_id    INT          NOT NULL,
    title      VARCHAR(200) NOT NULL,
    is_done    TINYINT(1)   NOT NULL DEFAULT 0,
    created_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (todo_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
