-- SELECT name FROM sqlite_master WHERE type='table' AND name='flashcards';

CREATE TABLE IF NOT EXISTS flashcards(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    user_id INTEGER NOT NULL,
    side_a CHARACTER VARYING(2048) NOT NULL,
    side_b CHARACTER VARYING(2048) NOT NULL,
    phonetic_transcriptions TEXT,
    comments TEXT,
    explanation TEXT,
    examples TEXT,
    source CHARACTER VARYING(2048),
    box INTEGER NOT NULL,
    due TIMESTAMP NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
