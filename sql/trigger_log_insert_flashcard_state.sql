CREATE TRIGGER IF NOT EXISTS log_insert_flashcard_state
  AFTER INSERT ON flashcards FOR EACH ROW
    BEGIN
      INSERT INTO flashcard_states
        (flashcard_id, state, review_timestamp)
      VALUES (new.id, new.state, new.review_timestamp);
    END;
