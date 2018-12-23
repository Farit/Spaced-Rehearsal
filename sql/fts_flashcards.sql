CREATE VIRTUAL TABLE fts_flashcards
USING fts4(answer, question, content='flashcards');

-- Triggers to keep the FTS index up to date.
CREATE TRIGGER IF NOT EXISTS fts_flashcards_before_delete
    BEFORE DELETE ON flashcards
BEGIN
    DELETE FROM fts_flashcards WHERE docid=old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS fts_flashcards_after_insert
    AFTER INSERT ON flashcards
BEGIN
    INSERT INTO fts_flashcards(docid, answer, question)
    VALUES(new.rowid, new.answer, new.question);
END;

CREATE TRIGGER IF NOT EXISTS fts_flashcards_before_update
    BEFORE UPDATE OF answer, question ON flashcards
BEGIN
    DELETE FROM fts_flashcards WHERE docid=old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS fts_flashcards_after_update
    AFTER UPDATE OF answer, question  ON flashcards
BEGIN
    INSERT INTO fts_flashcards(docid, answer, question)
    VALUES(new.rowid, new.answer, new.question);
END;

