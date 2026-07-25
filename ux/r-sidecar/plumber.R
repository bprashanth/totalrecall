library(plumber)
library(jsonlite)
library(ggplot2)
library(svglite)
library(scales)

`%||%` <- function(value, fallback) {
  if (is.null(value) || length(value) == 0) fallback else value
}

fieldnote_theme <- function() {
  theme_minimal(base_family = "sans", base_size = 11) +
    theme(
      plot.background = element_rect(fill = "#faf8f1", colour = NA),
      panel.background = element_rect(fill = "#faf8f1", colour = NA),
      plot.title = element_text(family = "serif", face = "plain", size = 21, colour = "#17231e"),
      plot.subtitle = element_text(size = 10, colour = "#536159", margin = margin(b = 14)),
      axis.title = element_text(size = 9, colour = "#536159"),
      axis.text = element_text(size = 8, colour = "#69736d"),
      panel.grid.major = element_line(colour = "#ded8ca", linewidth = 0.35),
      panel.grid.minor = element_blank(),
      legend.position = "bottom",
      legend.title = element_blank(),
      plot.margin = margin(20, 20, 18, 18)
    )
}

svg_result <- function(plot, width = 8.6, height = 4.8, note = "") {
  target <- tempfile(fileext = ".svg")
  svglite(target, width = width, height = height, bg = "#faf8f1")
  print(plot)
  dev.off()
  svg <- paste(readLines(target, warn = FALSE), collapse = "\n")
  unlink(target)
  list(
    svg = svg,
    note = note,
    engine = "R + ggplot2",
    session = paste("R", getRversion(), "ggplot2", packageVersion("ggplot2"))
  )
}

rows_frame <- function(rows) {
  do.call(
    rbind,
    lapply(rows, function(row) as.data.frame(row, stringsAsFactors = FALSE))
  )
}

plot_seasonal <- function(rows) {
  d <- rows_frame(rows)
  for (name in c("month", "median", "p10", "p90", "cells")) d[[name]] <- as.numeric(d[[name]])
  d$month_label <- factor(month.abb[d$month], levels = month.abb)
  p <- ggplot(d, aes(month)) +
    geom_ribbon(aes(ymin = p10, ymax = p90), fill = "#9dbda0", alpha = 0.34, na.rm = TRUE) +
    geom_line(aes(y = median, group = 1), colour = "#17473b", linewidth = 1.05, na.rm = TRUE) +
    geom_point(aes(y = median, size = cells), shape = 21, fill = "#faf8f1",
               colour = "#17473b", stroke = 0.8, na.rm = TRUE) +
    scale_x_continuous(breaks = 1:12, labels = month.abb) +
    scale_y_continuous(limits = c(0.3, 0.9), labels = number_format(accuracy = 0.1)) +
    scale_size_continuous(range = c(1.5, 4.5), guide = "none") +
    labs(
      title = "A year of greenness",
      subtitle = "Median across available cells; ribbon shows the 10th–90th percentile",
      x = NULL, y = "Greenness"
    ) +
    fieldnote_theme()
  svg_result(
    p,
    note = "July has no usable cells. This is a one-year seasonal profile, not a trend."
  )
}

plot_restoration <- function(rows) {
  d <- rows_frame(rows)
  d$value <- as.numeric(d$value)
  d$comparison_class <- factor(d$comparison_class)
  colours <- c(Benchmark = "#6d8f9d", Fragment = "#315c4c", Restoration = "#d58b57",
               Reference = "#6d8f9d", Plantation = "#9c7c58")
  p <- ggplot(d, aes(comparison_class, value, colour = comparison_class)) +
    geom_violin(fill = NA, linewidth = 0.6, alpha = 0.75, na.rm = TRUE) +
    geom_jitter(width = 0.13, height = 0, alpha = 0.42, size = 1.4, na.rm = TRUE) +
    stat_summary(fun = median, geom = "point", shape = 95, size = 8, linewidth = 1.2) +
    scale_colour_manual(values = colours, na.value = "#7a8179") +
    labs(
      title = "Young-tree richness across plots",
      subtitle = "Each point is one source-linked plot; the heavy mark is the median",
      x = NULL, y = "Tree species richness"
    ) +
    fieldnote_theme() +
    theme(legend.position = "none")
  svg_result(
    p,
    note = "Source-reported comparison classes are descriptive; this plot does not estimate an intervention effect."
  )
}

plot_acoustic <- function(rows) {
  d <- rows_frame(rows)
  d$value <- as.numeric(d$value)
  d$frequency_band <- as.numeric(d$frequency_band)
  d$hour_number <- as.numeric(sub("^([0-9]+).*$", "\\1", d$hour))
  p <- ggplot(d, aes(hour_number, frequency_band, fill = value)) +
    geom_tile() +
    scale_fill_gradientn(colours = c("#f1ead9", "#87aa93", "#173e34"), labels = number_format(accuracy = 0.01)) +
    scale_x_continuous(breaks = seq(0, 21, 3), labels = function(x) sprintf("%02dh", x)) +
    labs(
      title = "A day heard across frequencies",
      subtitle = "Mean acoustic-space use across recorder sites",
      x = "Hour", y = "Frequency band · kHz", fill = "Space use"
    ) +
    fieldnote_theme()
  svg_result(
    p,
    note = "Acoustic-space use is not a species count; identified calls are needed before naming species."
  )
}

#* @apiTitle Fieldnote R figure sidecar
#* @apiDescription Reproducible ggplot2 figures over structured, admitted rows.

#* Health
#* @serializer unboxedJSON
#* @get /health
function() {
  list(status = "ok", engine = "R + ggplot2", version = as.character(getRversion()))
}

#* Render one declared figure family.
#* @serializer unboxedJSON
#* @post /plot
function(req, res) {
  payload <- fromJSON(req$postBody, simplifyVector = FALSE)
  kind <- payload$kind %||% ""
  rows <- payload$data %||% list()
  if (!length(rows)) {
    res$status <- 400
    return(list(error = "No rows supplied."))
  }
  tryCatch(
    switch(
      kind,
      seasonal = plot_seasonal(rows),
      restoration = plot_restoration(rows),
      acoustic = plot_acoustic(rows),
      {
        res$status <- 400
        list(error = "Unknown plot family.")
      }
    ),
    error = function(error) {
      res$status <- 422
      list(error = conditionMessage(error))
    }
  )
}
