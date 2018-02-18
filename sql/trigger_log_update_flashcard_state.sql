CREATE TRIGGER IF NOT EXISTS log_update_flashcard_state
  AFTER UPDATE OF state ON flashcards FOR EACH ROW
    BEGIN
      INSERT INTO flashcard_states
        (flashcard_id, state, review_timestamp)
      VALUES (new.id, new.state, new.review_timestamp);
    END;
