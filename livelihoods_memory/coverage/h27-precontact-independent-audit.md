# H27 Precontact Independent Audit

Reviewed: 100 rows.

Scope: natural-language/gold semantic agreement under frozen IR v2.1, using only the bounded audit allowlist. Representation and direct execution were treated as already checked; this pass focused on whether the gold preserves the question's requested semantics.

## Suspect rows

- `h27-081`: The question asks for "Current job vacancies posted by firms in Kigali." The gold entity is only `job vacancies` with `time: null`, which drops both the fixed "current" constraint and the "posted by firms" qualifier. This is a source-gap row, not an ambiguity hole, but the unsupported leaf should still preserve the requested meaning. Safe repair: keep `expect: data_request` and `must_hole: false`, but use a more exact leaf such as entity `current firm-posted job vacancies` for Kigali, or otherwise encode the current constraint if the frozen time literal conventions admit it.

- `h27-084`: The question asks whether Nairobi traders prefer markets near bus stations and explicitly requests a proxy. The gold uses only `?proxy_for_trader_preference`, which is too broad and drops the object of the preference: markets near bus stations. Safe repair: keep the forced proxy DataRequest, but make the hole role exact, e.g. `?proxy_for_trader_preference_for_markets_near_bus_stations`, or exclude if the proxy-only behavior encoding is considered unable to preserve that object.

- `h27-085`: The question asks why Lagos workers choose coworking spaces and asks for the motive proxy. The gold uses `?proxy_for_worker_motive`, which drops the fixed choice object, coworking spaces. Safe repair: keep the forced proxy DataRequest, but use an exact hole such as `?proxy_for_worker_motive_for_coworking_space_choice`.

- `h27-086`: The question asks whether new metro stations caused shop incomes to rise in Chennai and requests the causal proxy. The gold hole `?proxy_for_metro_income_causality` is directionally close, but it drops "new", "shop", and "to rise" from the causal proxy role. Safe repair: keep the forced proxy DataRequest, but use a precise hole such as `?proxy_for_new_metro_station_shop_income_rise_causality`.

- `h27-087`: The question asks for a ratio of coworking spaces near metro stations to metro stations near coworking spaces in Guayaquil, but it never states a numeric threshold. The gold silently inserts `threshold_km: 1` on both `within` relations, changing an unstated "near" into an exact 1 km predicate. Safe repair: either change the question wording to say "within 1 km" on both sides, or make the threshold an explicit hole / remove the numeric threshold if unthresholded `within` is the intended frozen-IR representation.

## Accepted count

Accepted as-is: 95 rows.
