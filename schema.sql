CREATE TABLE `db_migrations` (
	`id` INTEGER PRIMARY KEY AUTOINCREMENT,
	`migration` TEXT NOT NULL
);

CREATE TABLE `suggestions` (
    `id` INTEGER PRIMARY KEY AUTOINCREMENT,
    `suggestion` TEXT NOT NULL,
	`user_id` INTEGER NOT NULL,
    `completed` INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE `questions` (
	`id` INTEGER PRIMARY KEY AUTOINCREMENT,
	`question` TEXT NOT NULL
);

CREATE TABLE `answers` (
	`id` INTEGER NOT NULL,
	`question_id` INTEGER NOT NULL,
	`answer` TEXT DEFAULT NULL,
	`emoji` TEXT NOT NULL UNIQUE,
	FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE `polls` (
	`id` INTEGER PRIMARY KEY AUTOINCREMENT,
	`question_id` INTEGER NOT NULL,
	`author` INT NOT NULL,
	`message_id` INT NOT NULL,
	FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE `poll_answers` (
	`poll_id` INTEGER NOT NULL,
	`user_id` INTEGER NOT NULL,
	`answer_id` INTEGER NOT NULL,
	PRIMARY KEY (`poll_id`, `user_id`),
	FOREIGN KEY (`answer_id`) REFERENCES `answers` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
);