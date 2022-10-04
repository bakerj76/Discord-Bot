ALTER TABLE `answers` RENAME TO `_answers_old`;

CREATE TABLE `answers` (
	`id` INTEGER PRIMARY KEY AUTOINCREMENT,
	`question_id` INTEGER NOT NULL,
	`answer` TEXT DEFAULT NULL,
	`emoji` TEXT NOT NULL,
	FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
);

DROP TABLE `_answers_old`;
