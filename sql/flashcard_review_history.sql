
CREATE TABLE IF NOT EXISTS flashcard_review_history(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    flashcard_id INTEGER NOT NULL,
    review_timestamp TIMESTAMP NOT NULL,
    result CHARACTER VARYING(2048) NOT NULL,
    trigger_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY(flashcard_id) REFERENCES flashcards(id)
);
