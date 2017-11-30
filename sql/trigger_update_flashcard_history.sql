CREATE TRIGGER IF NOT EXISTS update_flashcards_history
  AFTER UPDATE ON flashcards FOR EACH ROW
    BEGIN
      INSERT INTO flashcards_history
        (flashcard_id, box_old, due_old, box_new, due_new)
      VALUES (new.id, old.box, old.due, new.box, new.due);
    END;
