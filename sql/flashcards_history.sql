CREATE TABLE IF NOT EXISTS flashcards_history(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    flashcard_id INTEGER NOT NULL,
    box_old INTEGER NOT NULL,
    due_old TIMESTAMP NOT NULL,
    box_new INTEGER NOT NULL,
    due_new TIMESTAMP NOT NULL,
    trigger_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY(flashcard_id) REFERENCES flashcards(id)
);
