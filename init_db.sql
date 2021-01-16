PRAGMA foreign_keys = ON;
BEGIN DEFERRED TRANSACTION;
CREATE TABLE images
(
    name          CHAR(128) UNIQUE NOT NULL,
    hash          INTEGER PRIMARY KEY,
    uploaded_by   INTEGER,
    time_uploaded DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE mosaic_bot
(
    requesting_message_id INTEGER PRIMARY KEY,
    requested_by          INTEGER NOT NULL,
    channel               INTEGER NOT NULL,
    image_requested       INTEGER NOT NULL,
    time_requested        DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (image_requested) REFERENCES images (hash)
);
COMMIT;
