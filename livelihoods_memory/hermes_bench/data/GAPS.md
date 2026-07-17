# GAPS — what could not be sourced (Erode livelihoods data pack)

Each line: what's missing, and why it did not make it into the pack this session.

- **Current informal dyeing/powerloom-unit daily wages (per-worker).** No fetchable current wage table
  found. The one unit-level number we do have (Brindha & Sundareswaran 2019, JETIR) reports a
  *unit's* monthly labour-wage bill (Rs 10,000-30,000/month across an unstated number of workers per
  unit), not a per-worker daily/monthly wage — not the same statistic, so it stays flagged here rather
  than being repurposed as a per-worker figure.

- **MGNREGA person-days generated for Erode district (any recent year).** The official MIS report
  pages (nregastrep.nic.in/netnrega/homedist.aspx, mnregaweb4.nic.in report endpoints) returned
  HTTP 503 (service unavailable) or session-tokenized "Digest" 403/blocked pages on every attempt —
  these ASP.NET report URLs appear to require a live browser session token, not just a GET. We only
  got a *snapshot* (households-employed / registered-households / wage-rate) from the Erode DRDA's
  own public scheme datasheet, not a persondays total for any specific year.

- **Village/ward-level dairy incomes or milk-collection volumes for Erode.** The DIC/MSME industrial
  profile lists "Milk and Milk Products" only under section 3.14, "Potential areas for new MSMEs" —
  i.e. it is recorded as an *aspirational* investment opportunity, not an existing measured industry.
  No existing dairy-unit count, employment figure, or farmer-income figure was found this session.

- **Rice-mill and oil-mill unit counts/employment specifically.** The DIC profile names "Rice Mill"
  (Kangeyam) and "Oil Mill" (Kangeyam, Vellakovil) as identified industrial clusters but gives no unit
  count or employment number for either; both are folded into the aggregate NIC-15 "Food Products and
  Beverages" count (3,539 units) with no further breakdown available in the source document.

- **Powerloom vs handloom unit counts as separate categories.** The DIC profile groups both under
  NIC-17 "Textiles" (4,406 units) and NIC-18 "Weaving Apparel; Dressing and Dyeing" (3,659 units)
  without isolating powerloom from handloom counts.

- **Real-time/current-season turmeric arrivals and price series specifically for Erode from
  agmarknet.gov.in.** agmarknet's own price/arrival reports are dynamic, form-submission-driven pages
  that could not be fetched as static content this session (consistent with the framework note that
  agmarknet is hard to scrape). We substituted a market-news aggregator (Agro Spectrum India, dated
  arrivals/price for 13 Apr 2026) and a mandi-price mirror site (commoditymarketlive.com, dated 14 Jun
  2024) instead — both single-day/point-in-time snapshots, not a continuous series.

- **Rural/urban split for the combined (main+marginal) worker sub-categories** (cultivators,
  agricultural labourers, household-industry workers, other workers). The Census handbook's
  "Category of Workers (Main & Marginal)" table gives only district-total figures; the rural/urban
  split we *do* have (in census2011_workers.json) is for the main-workers-only sub-table, which is a
  different (smaller) base than main+marginal.

- **Grace Carswell's Tiruppur labour-market paper, full text.** The Wiley-hosted article returned
  HTTP 402 (Payment Required); only the publisher's abstract (via a web search snippet) could be
  retrieved, so the papers.json excerpt for this paper is a paraphrase of the abstract, not the full
  article body.
