CREATE VIRTUAL TABLE fts_flashcards
USING fts4(side_answer, side_question, content='flashcards');

-- Triggers to keep the FTS index up to date.
CREATE TRIGGER IF NOT EXISTS fts_flashcards_before_delete
    BEFORE DELETE ON flashcards
BEGIN
    DELETE FROM fts_flashcards WHERE docid=old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS fts_flashcards_after_insert
    AFTER INSERT ON flashcards
BEGIN
    INSERT INTO fts_flashcards(docid, side_answer, side_question)
    VALUES(new.rowid, new.side_answer, new.side_question);
END;

CREATE TRIGGER IF NOT EXISTS fts_flashcards_before_update
    BEFORE UPDATE OF side_answer, side_question ON flashcards
BEGIN
    DELETE FROM fts_flashcards WHERE docid=old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS fts_flashcards_after_update
    AFTER UPDATE OF side_answer, side_question  ON flashcards
BEGIN
    INSERT INTO fts_flashcards(docid, side_answer, side_question)
    VALUES(new.rowid, new.side_answer, new.side_question);
END;

