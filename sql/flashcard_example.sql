
CREATE TABLE IF NOT EXISTS flashcard_example(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    flashcard_id INTEGER NOT NULL,
    example TEXT,
    FOREIGN KEY(flashcard_id) REFERENCES flashcards(id)
);
