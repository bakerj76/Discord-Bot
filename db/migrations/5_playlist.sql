CREATE TABLE `playlists` (
	`id` INTEGER PRIMARY KEY AUTOINCREMENT,
	`youtube_id` TEXT NOT NULL,
	`title` TEXT NOT NULL,
	`description` TEXT DEFAULT NULL
);

CREATE INDEX `playlists_youtube_id` ON `playlists` (`youtube_id`);

CREATE TABLE `videos` (
	`id` INTEGER PRIMARY KEY AUTOINCREMENT,
	`youtube_id` TEXT NOT NULL,
	`playlist_id` INTEGER NOT NULL,
	`youtube_playlist_item_id` INTEGER NOT NULL,
	`title` TEXT NOT NULL,
	`description` TEXT NOT NULL,
	`position` INTEGER NOT NULL,
	FOREIGN KEY (`playlist_id`) REFERENCES `playlists` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
);