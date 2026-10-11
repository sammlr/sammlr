CREATE TEMP TABLE lifecycle_completion_down_guard(n INTEGER CHECK(n=0));
INSERT INTO lifecycle_completion_down_guard SELECT COUNT(*) FROM lifecycle_direction_resolutions;
INSERT INTO lifecycle_completion_down_guard SELECT COUNT(*) FROM lifecycle_completions;
INSERT INTO lifecycle_completion_down_guard SELECT COUNT(*) FROM lifecycle_rating_eligibility;
INSERT INTO lifecycle_completion_down_guard SELECT COUNT(*) FROM lifecycle_rating_details;
INSERT INTO lifecycle_completion_down_guard SELECT COUNT(*) FROM lifecycle_rating_publications;
DROP TABLE lifecycle_completion_down_guard;
DROP TRIGGER lifecycle_shipping_no_cancel;
CREATE TRIGGER lifecycle_shipping_no_cancel BEFORE UPDATE OF state,accepted_revision_id ON lifecycle_contracts
WHEN EXISTS(SELECT 1 FROM lifecycle_shipping WHERE trade_id=OLD.trade_id)
 AND (NEW.state<>OLD.state OR NEW.accepted_revision_id<>OLD.accepted_revision_id)
BEGIN SELECT RAISE(ABORT,'Physical shipping forbids normal cancellation or amendment'); END;

DROP TRIGGER lifecycle_completion_event_replace;
DROP TRIGGER lifecycle_completion_event_delete;
DROP TRIGGER lifecycle_completion_event_update;
DROP TRIGGER lifecycle_rating_publications_delete;
DROP TRIGGER lifecycle_rating_publications_update;
DROP TRIGGER lifecycle_rating_details_delete;
DROP TRIGGER lifecycle_rating_details_update;
DROP TRIGGER lifecycle_rating_eligibility_delete;
DROP TRIGGER lifecycle_rating_eligibility_update;
DROP TRIGGER lifecycle_completions_delete;
DROP TRIGGER lifecycle_completions_update;
DROP TRIGGER lifecycle_direction_resolutions_delete;
DROP TRIGGER lifecycle_direction_resolutions_update;
DROP TRIGGER lifecycle_resolved_no_receipt;
DROP TRIGGER lifecycle_completed_no_reopen;
DROP TRIGGER lifecycle_rating_publication_identity;
DROP TRIGGER lifecycle_rating_details_identity;
DROP TRIGGER lifecycle_rating_identity;
DROP TRIGGER lifecycle_eligibility_identity;
DROP TRIGGER lifecycle_completion_identity;
DROP TRIGGER lifecycle_resolution_identity;
DROP TABLE lifecycle_rating_publications;
DROP TABLE lifecycle_rating_details;
DROP TABLE lifecycle_rating_eligibility;
DROP TABLE lifecycle_completions;
DROP TABLE lifecycle_direction_resolutions;
