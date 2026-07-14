# Trips aggregate change

- `trips` is the aggregate root for travel-companion data.
- One travel plan conceptually corresponds to one `trips` row.
- This change deliberately does not connect `trips` to `trip_plan_requests` or `trip_plan_versions`.
- Companion foreign keys target `trips.id`; public payload field names remain `tour_id` for compatibility unless tests show an established `trip_id` contract.
- Existing user-owned deletion of `backend/sql/05_hikari_atlas_migration.sql` is preserved.
