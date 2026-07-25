FROM rocker/r-ver:4.5.1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    libfontconfig1-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libsodium-dev \
    && rm -rf /var/lib/apt/lists/*

RUN R -e "packages <- c('plumber','jsonlite','ggplot2','svglite','scales'); install.packages(packages, repos='https://cloud.r-project.org', Ncpus=2); stopifnot(all(vapply(packages, requireNamespace, logical(1), quietly=TRUE)))"

WORKDIR /app
COPY plumber.R /app/plumber.R

EXPOSE 7331
CMD ["R", "-e", "pr <- plumber::plumb('/app/plumber.R'); pr$run(host='0.0.0.0', port=7331)"]
