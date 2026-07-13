# Livelihoods data census — 2026-07-12

## Why

The benchmark must be grounded in sources that return real rows before questions are written.
Livelihoods is especially vulnerable to plausible-looking but semantically weak proxies: a market
point is not an income, and a labor indicator at country grain is not a city statistic.

## What I did

I queried eight OSM tag shapes across Bengaluru, Nairobi, and Accra, and nine World Bank labor
indicator codes across India, Kenya, and Ghana. Requests used the harness cache. I recorded the
coverage matrix and source grain in `FINDINGS.md`.

## What I found

Markets, banks/ATMs, coworking offices, and craft businesses are real cross-city record axes.
Employment-agency and training tags are too sparse for ordinary gold questions and will remain
honest data gaps. All nine selected labor codes have 35–36 annual points in all three countries.
The census also exposed an algebra-level evidence issue: several retrieved series are explicitly
modeled ILO estimates, but the frozen label rule equates every connector leaf with `observed`.
That issue will be proposed with a concrete execution trace; the frozen spec remains untouched.
