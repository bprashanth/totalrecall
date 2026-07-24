# Restoration opportunities beyond highly degraded tropical forests: insights from India’s Western Ghats

[https://doi.org/10.5061/dryad.8kprr4xvb](https://doi.org/10.5061/dryad.8kprr4xvb)

This document describes the data and scripts associated with Osuri et al. 2024: Restoration opportunities beyond highly degraded tropical forests: insights from India’s Western Ghats

The upload contains three data files and four R scripts.

## Description of the data and file structure

1\. **Osuri_tree_data.csv** contains data from 132 tree (GBH >=30 cm) inventory plots (20m x 20m) in rainforest fragments and reference rainforests. 124 plots were analyzed, while 8 plots lacking canopy cover data were excluded. The data columns are:

DateTime: Date/timestamp

Treatment: Forest fragmentation status -- Fragment OR Benchmark (reference)

Site_ID: Unique site code for each plot

Species_name: Species name as recorded

Height: Tree height (m)

GBH1: Girth at breast height (cm) of single-stemmed trees

GBH1 - GBH12: Girth at breast height (cm) of multi-stemmed trees

Remarks: Remarks

Accept_name_WFO: World Flora Online accepted species names

Habit: Growth form -- Tree OR Shrub

Distribution: Distributional range and origin -- Endemic OR Native OR Introduced

IUCN_status: IUCN redlist category -- CR or EN or VU or NT or LC or DD, or NA (unknown)

wden_sps: Species-level wood density (g cm-3)

Wden_final: Wood density (g cm-3) used in biomass estimation, species level is available, else genus level

seed_size: Categorical -- S (Small; length <1 cm), M (Medium; length 1-3 cm), L (Large; length >3 cm), or NA (Unknown)

disperser: Seed dispersal mechanism -- Bird, Mammal, Mammal_bird (mammal and bird), Gravity, Wind, or Unknown

habt_new: Habitat affinity category: Mature (mature forest), Secondary (secondary or disturbed forest), NA (unknown/Introduced species)

ad_ht: Species maximum adult height (m)

DBH: Effective diameter (cm). Calculated as (d1^2 + d2^2 +...dn^2)^0.5, where d1 = GBH1/pi, and so on

Basal: Tree basal area (m2)

Carbon: Tree aboveground carbon stock (Mg)

2\. **Osuri_regen_data.csv** contains data from 132 seedling (height >= 10 cm and GBH < 10 cm) plots (20m x 20m) in rainforest fragments and reference rainforests. 124 plots were analyzed, while 8 plots lacking canopy cover data were excluded. The data columns are:

Date: Date/timestamp

Site_ID: Unique site code for each plot

Treatment: Forest fragmentation status -- Fragment OR Benchmark (reference)

Species_name: Species name as recorded

Abun: No. of individuals counted

Accept_name_WFO: World Flora Online accepted species names

Habit: Growth form -- Tree OR Shrub

Distribution: Distributional range and origin -- Endemic OR Native OR Introduced

IUCN_status: IUCN redlist category -- CR or EN or VU or NT or LC or DD, or NA (unknown)

wden_sps: Species-level wood density (g cm-3)

Wden_final: Wood density (g cm-3) used in biomass estimation, species level is available, else genus level

seed_size: Categorical -- S (Small; length <1 cm), M (Medium; length 1-3 cm), L (Large; length >3 cm), or NA (Unknown)

disperser: Seed dispersal mechanism -- Bird, Mammal, Mammal_bird (mammal and bird), Gravity, Wind, or Unknown

habt_new: Habitat affinity category: Mature (mature forest), Secondary (secondary or disturbed forest), NA (unknown/Introduced species)

ad_ht: Species maximum adult height (m)

**3. Osuri_plotInfo.csv** contains site details of 132 plots, 124 of which were included in the analysis. The data columns are:

S_No.: Serial number

Site_name: Site name

Site_ID: Unique site code for each plot

Treatment: Forest fragmentation status -- Fragment OR Benchmark (reference)

Lat_final: Latitude of plot centroid (degree-decimal)

Long_final: Longitude of plot centroid (degree-decimal)

dist_PA: Distance from protected area (m)

CanCover: Canopy cover (%)

## Sharing/Access information

For tree functional trait data and sources, see Osuri et. al. (2024) Fruit, seed dispersal, and life history traits of tropical rainforest trees of the Anamalai Hills, Western Ghats, India

## Code/Software

1\. Osuri_tree_script.R contains R scripts for computing summaries, performing regression models, and creating graphs from the adult tree dataset (outputs: Fig. 2, Fig. S3, Fig. S5, Table S2)

2\. Osuri_regen_script.R contains R scripts for computing summaries, performing regression models, and creating graphs from the regeneration dataset (outputs: Fig. 2, Fig. S4, Fig. S5, Table S3)

3\. Osuri_simulation_script.R contains R scripts for performing the restoration simulations using the tree and regeneration datasets, and generating Fig. 3

4\. Osuri_figure_composites.R contains R scripts for formatting Figs. 2, 3, S3, S4, and S5 as depicted in the manuscript
