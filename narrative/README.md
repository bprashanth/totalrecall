# narrative site

`index.html` is the Why deck (field notes from Insight Out + benchmark findings).
Source of truth for the content lives in heartwood:
`docs/architecture/memory/narrative/why/why-slides.html`. Copy it here when it changes:

    cp ../../heartwood/docs/architecture/memory/narrative/why/why-slides.html index.html

## Serve locally
Static single file, no build step:

    cd narrative && python3 -m http.server 8080     # then open http://localhost:8080

## Deploy
Netlify config is at the repo root (`netlify.toml`, publish dir = `narrative`).
Drag-and-drop this folder on app.netlify.com/drop also works.
