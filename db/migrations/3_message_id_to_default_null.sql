ALTER TABLE `polls` RENAME TO `_polls_old`;

CREATE TABLE `polls` (
	`id` INTEGER PRIMARY KEY AUTOINCREMENT,
	`question_id` INTEGER NOT NULL,
	`author` INT NOT NULL,
	`message_id` INT DEFAULT NULL,
	FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
);

DROP TABLE `_polls_old`;
