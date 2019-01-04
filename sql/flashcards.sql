-- SELECT name FROM sqlite_master WHERE type='table' AND name='flashcards';

CREATE TABLE IF NOT EXISTS flashcards(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    flashcard_type CHARACTER VARYING(2048) NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    phonetic_transcription TEXT,
    source TEXT,
    explanation TEXT,
    user_id INTEGER NOT NULL,
    review_timestamp TIMESTAMP NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
