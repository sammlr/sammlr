CREATE TEMP TABLE lifecycle_shipping_down_guard(n INTEGER CHECK(n=0));
INSERT INTO lifecycle_shipping_down_guard SELECT COUNT(*) FROM lifecycle_shipping;
DROP TABLE lifecycle_shipping_down_guard;
DROP TRIGGER lifecycle_shipping_no_undo;
DROP TRIGGER lifecycle_shipping_no_cancel;
DROP TRIGGER lifecycle_shipping_delete;
DROP TRIGGER lifecycle_shipping_immutable;
DROP TRIGGER lifecycle_shipping_owner;
DROP TABLE lifecycle_shipping;
