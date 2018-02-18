-- SELECT name FROM sqlite_master WHERE type='table' AND name='flashcards';

CREATE TABLE IF NOT EXISTS flashcards(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    side_question TEXT NOT NULL,
    side_answer TEXT NOT NULL,
    phonetic_transcriptions TEXT,
    source TEXT,
    explanation TEXT,
    examples TEXT,
    user_id INTEGER NOT NULL,
    review_timestamp TIMESTAMP NOT NULL,
    state CHARACTER VARYING(2048) NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
