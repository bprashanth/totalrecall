# Fieldnote · Valparai

Fieldnote is a visual-first ecological analysis studio over the Valparai site pack. It opens with
the landscape rather than an empty chat box, keeps survey effort beside occurrence records, and
explains every figure in plain language. The same interface can read a paper method, compare its
requirements with the admitted site data, and ask an R sidecar for a reproducible first-look
figure.

For the product model, current deployment modes, verified flows and known integration boundaries,
read [PLATFORM_GUIDE.md](./PLATFORM_GUIDE.md).
For the source-to-visual path, current skills and the ingestion roadmap, read
[DATA_PIPELINE.md](./DATA_PIPELINE.md).

## Runtime shape

```text
browser
  -> Fieldnote Next/Vinext UI on :7300
       -> existing Valparai bridge on host :7012
            -> Codex CLI in the existing Hermes container
            -> typed site capabilities and immutable idli-result/1 payloads
       -> R sidecar on :7331
            -> ggplot2/svglite figure over bounded structured rows
```

The bridge remains the only path from conversation to Codex and the admitted Valparai data. The
browser never receives its token. The R service receives only the bounded rows needed for the
chosen plot and does not query the source index directly.

The public Sites build has no access to the private local bridge. It therefore acts as an
aggregate field atlas and labels its answers as previews. A local installation automatically
changes to audited live results when the 7012 token and bridge are available.

## Start

The Valparai bridge must already be healthy:

```bash
curl -fsS http://172.17.0.1:7012/health
```

Then:

```bash
cd /home/beeps/src/github.com/bprashanth/totalrecall/ux
docker compose up -d --build
```

Open `http://127.0.0.1:7300`.

Status:

```bash
docker compose ps
curl -fsS http://127.0.0.1:7331/health
curl -fsS http://127.0.0.1:7300/api/status
```

Stop only this studio:

```bash
docker compose down
```

These commands do not start, stop or modify the existing Hermes, Idlisseus, 7011, 7012 or 7013
services.

## Development without containers

```bash
cp .env.example .env.local
npm install
npm run export:demo
npm run dev
```

R is optional during front-end development. When it is offline, the browser visual remains
available and the interface says that the R rendering was not produced.

## Data and claim boundaries

- The bundled public atlas contains aggregate cells, not exact occurrence coordinates.
- A record-density map is not an abundance or absence map.
- Satellite greenness is a landscape surface, not proof of recruitment, flowering or recovery.
- Acoustic-space use is not a species count.
- Plot-class differences remain descriptive unless an admitted study design supports inference.
- A paper's method is not local evidence. “First-look analogue” and “replication” remain distinct.

Rebuild the aggregate preview after the Valparai serving index changes:

```bash
npm run export:demo
```

## Paper intake

The method workbench accepts a PDF or plain-text file up to 25 MB, or an article DOI. A DOI lookup
uses Crossref for the article record and DataCite for registered related datasets. A PDF can also
surface dataset DOIs mentioned in its text; those are labelled separately because a citation does
not prove that the dataset is this paper's supplement. This means a publisher page blocked by a
login or bot check does not prevent method and dataset candidates from being identified.

Reading and admission are deliberately separate:

```text
paper or DOI
  -> method reading + linked dataset discovery
  -> "Queue for source review"
  -> immutable acquisition, profiling, adapter proposal and review
  -> admitted source + rebuilt site index
```

The queue is written under `../runs/fieldnote-paper-intake/` by the local Docker deployment. A
queued record is only an intake request; it does not change any source, fact or visual. The public
Sites deployment can prepare the same candidate but does not claim to persist or admit it.
