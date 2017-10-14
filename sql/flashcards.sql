-- SELECT name FROM sqlite_master WHERE type='table' AND name='flashcards';

CREATE TABLE IF NOT EXISTS flashcards(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    user_id INTEGER NOT NULL,
    side_a CHARACTER VARYING(2048) NOT NULL,
    side_b CHARACTER VARYING(2048) NOT NULL,
    phonetic_transcriptions TEXT,
    comments TEXT,
    source CHARACTER VARYING(2048),
    box INTEGER NOT NULL,
    due TIMESTAMP NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

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

CREATE TRIGGER IF NOT EXISTS update_flashcards_history
  AFTER UPDATE ON flashcards FOR EACH ROW
    BEGIN
      INSERT INTO flashcards_history
        (flashcard_id, box_old, due_old, box_new, due_new)
      VALUES (new.id, old.box, old.due, new.box, new.due);
    END;
