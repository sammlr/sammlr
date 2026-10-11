-- Additive V1 completion metadata; ratings remain in the shared trade_ratings table.
CREATE TABLE lifecycle_direction_resolutions (
 trade_id INTEGER NOT NULL,
 from_user_id INTEGER NOT NULL,
 revision_id INTEGER NOT NULL REFERENCES lifecycle_revisions(id),
 receiver_id INTEGER NOT NULL REFERENCES users(id),
 kind TEXT NOT NULL CHECK(kind IN ('complete','problem_accepted','after_wait')),
 problem_id INTEGER REFERENCES lifecycle_delivery_problems(id),
 resolved_at TEXT NOT NULL,
 PRIMARY KEY(trade_id,from_user_id),
 FOREIGN KEY(trade_id,from_user_id) REFERENCES lifecycle_directions(trade_id,from_user_id),
 CHECK((kind='complete')=(problem_id IS NULL))
);
CREATE TABLE lifecycle_completions (
 trade_id INTEGER PRIMARY KEY REFERENCES lifecycle_contracts(trade_id),
 revision_id INTEGER NOT NULL REFERENCES lifecycle_revisions(id),
 outcome TEXT NOT NULL CHECK(outcome IN ('completed','closed_with_problem')),
 completed_at TEXT NOT NULL
);
CREATE TABLE lifecycle_rating_eligibility (
 trade_id INTEGER NOT NULL REFERENCES lifecycle_contracts(trade_id),
 user_id INTEGER NOT NULL REFERENCES users(id),
 eligible_at TEXT NOT NULL,
 PRIMARY KEY(trade_id,user_id)
);
CREATE TABLE lifecycle_rating_details (
 rating_id INTEGER PRIMARY KEY REFERENCES trade_ratings(id),
 tags_json TEXT NOT NULL CHECK(json_valid(tags_json) AND json_type(tags_json)='array')
);
CREATE TABLE lifecycle_rating_publications (
 rating_id INTEGER PRIMARY KEY REFERENCES trade_ratings(id),
 revealed_at TEXT NOT NULL
);
CREATE TRIGGER lifecycle_resolution_identity BEFORE INSERT ON lifecycle_direction_resolutions
WHEN EXISTS(SELECT 1 FROM lifecycle_direction_resolutions WHERE trade_id=NEW.trade_id AND from_user_id=NEW.from_user_id)
 OR NOT EXISTS(SELECT 1 FROM lifecycle_contracts c JOIN lifecycle_directions d ON d.trade_id=c.trade_id
 WHERE c.trade_id=NEW.trade_id AND c.state='accepted' AND c.accepted_revision_id=NEW.revision_id
 AND d.from_user_id=NEW.from_user_id AND d.to_user_id=NEW.receiver_id)
 OR (NEW.kind='complete' AND NOT EXISTS(SELECT 1 FROM lifecycle_receipts WHERE trade_id=NEW.trade_id AND from_user_id=NEW.from_user_id AND has_problem=0))
 OR (NEW.kind<>'complete' AND NOT EXISTS(SELECT 1 FROM lifecycle_delivery_problems WHERE id=NEW.problem_id AND trade_id=NEW.trade_id AND from_user_id=NEW.from_user_id AND revision_id=NEW.revision_id))
BEGIN SELECT RAISE(ABORT,'Invalid direction resolution'); END;
CREATE TRIGGER lifecycle_completion_identity BEFORE INSERT ON lifecycle_completions
WHEN EXISTS(SELECT 1 FROM lifecycle_completions WHERE trade_id=NEW.trade_id)
 OR NOT EXISTS(SELECT 1 FROM lifecycle_contracts WHERE trade_id=NEW.trade_id AND state='accepted' AND accepted_revision_id=NEW.revision_id)
 OR (SELECT COUNT(*) FROM lifecycle_direction_resolutions WHERE trade_id=NEW.trade_id)<>2
 OR (NEW.outcome='completed')<>(NOT EXISTS(SELECT 1 FROM lifecycle_direction_resolutions WHERE trade_id=NEW.trade_id AND kind<>'complete') AND NOT EXISTS(SELECT 1 FROM lifecycle_delivery_problems WHERE trade_id=NEW.trade_id))
BEGIN SELECT RAISE(ABORT,'Both directions must be resolved'); END;
CREATE TRIGGER lifecycle_eligibility_identity BEFORE INSERT ON lifecycle_rating_eligibility
WHEN EXISTS(SELECT 1 FROM lifecycle_rating_eligibility WHERE trade_id=NEW.trade_id AND user_id=NEW.user_id)
 OR NOT EXISTS(SELECT 1 FROM lifecycle_receipts WHERE trade_id=NEW.trade_id AND receiver_id=NEW.user_id AND received_at=NEW.eligible_at
 UNION ALL SELECT 1 FROM lifecycle_direction_resolutions WHERE trade_id=NEW.trade_id AND receiver_id=NEW.user_id AND kind='after_wait' AND resolved_at=NEW.eligible_at)
BEGIN SELECT RAISE(ABORT,'Rating requires authoritative eligibility'); END;
CREATE TRIGGER lifecycle_rating_identity BEFORE INSERT ON trade_ratings
WHEN EXISTS(SELECT 1 FROM lifecycle_contracts WHERE trade_id=NEW.trade_id)
 AND (EXISTS(SELECT 1 FROM trade_ratings WHERE id=NEW.id OR (trade_id=NEW.trade_id AND rater_user_id=NEW.rater_user_id))
 OR typeof(NEW.stars)<>'integer'
 OR NOT EXISTS(SELECT 1 FROM lifecycle_directions d JOIN lifecycle_rating_eligibility e ON e.trade_id=d.trade_id AND e.user_id=d.to_user_id
 WHERE d.trade_id=NEW.trade_id AND d.to_user_id=NEW.rater_user_id AND d.from_user_id=NEW.rated_user_id))
BEGIN SELECT RAISE(ABORT,'Invalid V1 rating identity'); END;
CREATE TRIGGER lifecycle_rating_details_identity BEFORE INSERT ON lifecycle_rating_details
WHEN EXISTS(SELECT 1 FROM lifecycle_rating_details WHERE rating_id=NEW.rating_id)
 OR NOT EXISTS(SELECT 1 FROM trade_ratings r JOIN lifecycle_contracts c ON c.trade_id=r.trade_id WHERE r.id=NEW.rating_id)
BEGIN SELECT RAISE(ABORT,'Invalid V1 rating details'); END;
CREATE TRIGGER lifecycle_rating_publication_identity BEFORE INSERT ON lifecycle_rating_publications
WHEN EXISTS(SELECT 1 FROM lifecycle_rating_publications WHERE rating_id=NEW.rating_id)
 OR NOT EXISTS(SELECT 1 FROM lifecycle_rating_details WHERE rating_id=NEW.rating_id)
BEGIN SELECT RAISE(ABORT,'Invalid rating publication'); END;
CREATE TRIGGER lifecycle_completed_no_reopen BEFORE UPDATE ON lifecycle_contracts
WHEN EXISTS(SELECT 1 FROM lifecycle_completions WHERE trade_id=OLD.trade_id)
 AND (NEW.state<>'ended' OR NEW.accepted_revision_id<>OLD.accepted_revision_id OR NEW.current_revision_id<>OLD.current_revision_id)
BEGIN SELECT RAISE(ABORT,'Completed contract is final'); END;
CREATE TRIGGER lifecycle_resolved_no_receipt BEFORE INSERT ON lifecycle_receipts
WHEN EXISTS(SELECT 1 FROM lifecycle_direction_resolutions WHERE trade_id=NEW.trade_id AND from_user_id=NEW.from_user_id)
BEGIN SELECT RAISE(ABORT,'Resolved direction cannot receive again'); END;
CREATE TRIGGER lifecycle_direction_resolutions_update BEFORE UPDATE ON lifecycle_direction_resolutions
BEGIN SELECT RAISE(ABORT,'Completion evidence is immutable'); END;
CREATE TRIGGER lifecycle_direction_resolutions_delete BEFORE DELETE ON lifecycle_direction_resolutions
BEGIN SELECT RAISE(ABORT,'Completion evidence is immutable'); END;
CREATE TRIGGER lifecycle_completions_update BEFORE UPDATE ON lifecycle_completions
BEGIN SELECT RAISE(ABORT,'Completion evidence is immutable'); END;
CREATE TRIGGER lifecycle_completions_delete BEFORE DELETE ON lifecycle_completions
BEGIN SELECT RAISE(ABORT,'Completion evidence is immutable'); END;
CREATE TRIGGER lifecycle_rating_eligibility_update BEFORE UPDATE ON lifecycle_rating_eligibility
BEGIN SELECT RAISE(ABORT,'Completion evidence is immutable'); END;
CREATE TRIGGER lifecycle_rating_eligibility_delete BEFORE DELETE ON lifecycle_rating_eligibility
BEGIN SELECT RAISE(ABORT,'Completion evidence is immutable'); END;
CREATE TRIGGER lifecycle_rating_details_update BEFORE UPDATE ON lifecycle_rating_details
BEGIN SELECT RAISE(ABORT,'Completion evidence is immutable'); END;
CREATE TRIGGER lifecycle_rating_details_delete BEFORE DELETE ON lifecycle_rating_details
BEGIN SELECT RAISE(ABORT,'Completion evidence is immutable'); END;
CREATE TRIGGER lifecycle_rating_publications_update BEFORE UPDATE ON lifecycle_rating_publications
BEGIN SELECT RAISE(ABORT,'Completion evidence is immutable'); END;
CREATE TRIGGER lifecycle_rating_publications_delete BEFORE DELETE ON lifecycle_rating_publications
BEGIN SELECT RAISE(ABORT,'Completion evidence is immutable'); END;
CREATE TRIGGER lifecycle_completion_event_update BEFORE UPDATE ON trade_events
WHEN OLD.event_type IN ('DirectionResolvedComplete','DirectionResolvedProblemAccepted','DirectionResolvedAfterWait','TradeCompletedSuccessfully','TradeCompletedWithProblem','RatingSubmitted','RatingRevealed') AND EXISTS(SELECT 1 FROM lifecycle_contracts WHERE trade_id=OLD.trade_id)
BEGIN SELECT RAISE(ABORT,'Completion history is immutable'); END;
CREATE TRIGGER lifecycle_completion_event_delete BEFORE DELETE ON trade_events
WHEN OLD.event_type IN ('DirectionResolvedComplete','DirectionResolvedProblemAccepted','DirectionResolvedAfterWait','TradeCompletedSuccessfully','TradeCompletedWithProblem','RatingSubmitted','RatingRevealed') AND EXISTS(SELECT 1 FROM lifecycle_contracts WHERE trade_id=OLD.trade_id)
BEGIN SELECT RAISE(ABORT,'Completion history is immutable'); END;
CREATE TRIGGER lifecycle_completion_event_replace BEFORE INSERT ON trade_events
WHEN EXISTS(SELECT 1 FROM trade_events e JOIN lifecycle_contracts c ON c.trade_id=e.trade_id WHERE e.id=NEW.id AND e.event_type IN ('DirectionResolvedComplete','DirectionResolvedProblemAccepted','DirectionResolvedAfterWait','TradeCompletedSuccessfully','TradeCompletedWithProblem','RatingSubmitted','RatingRevealed'))
BEGIN SELECT RAISE(ABORT,'Completion history is immutable'); END;

-- Preserve the shipping guard, except for an evidenced final completion.
DROP TRIGGER lifecycle_shipping_no_cancel;
CREATE TRIGGER lifecycle_shipping_no_cancel BEFORE UPDATE OF state,accepted_revision_id ON lifecycle_contracts
WHEN EXISTS(SELECT 1 FROM lifecycle_shipping WHERE trade_id=OLD.trade_id)
 AND (NEW.state<>OLD.state OR NEW.accepted_revision_id<>OLD.accepted_revision_id)
 AND NOT (OLD.state='accepted' AND NEW.state='ended'
 AND NEW.accepted_revision_id=OLD.accepted_revision_id
 AND EXISTS(SELECT 1 FROM lifecycle_completions WHERE trade_id=OLD.trade_id AND revision_id=OLD.accepted_revision_id))
BEGIN SELECT RAISE(ABORT,'Physical shipping forbids normal cancellation or amendment'); END;
