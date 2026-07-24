# Active restoration fosters better recovery of tropical rainforest birds than natural regeneration in degraded forest fragments

[https://doi.org/10.5061/dryad.rjdfn2zc3](https://doi.org/10.5061/dryad.rjdfn2zc3)

This dataset is from:

Hariharan, P., and Raman, T. R. S. (2022). Active restoration fosters better recovery of tropical rainforest birds than natural regeneration in degraded forest fragments. Journal of Applied Ecology 59: 274-285. [https://doi.org/10.1111/1365-2664.14052](https://doi.org/10.1111/1365-2664.14052)

### Data Set Owner(s):

AUTHOR #1

1\. Name: Priyanka Hariharan (Corresponding author)

2\. Work Address: Nature Conservation Foundation, 1311, 12th A Main, Vijayanagar 1st Stage, Mysuru 570017, Karnataka, India

3\. Current Work Address: Department of Wildlife Ecology and Conservation, University of Florida, Gainesville, Florida, U.S.A.

3\. Email address: [phariharan1@ufl.edu](mailto:phariharan1@ufl.edu), [priyanka.h615@gmail.com](mailto:priyanka.h615@gmail.com)

4\. ORCID: [https://orcid.org/0000-0002-1619-3519](https://orcid.org/0000-0002-1619-3519)

AUTHOR #2

1\. Name: T. R. Shankar Raman

2\. Work Address: Nature Conservation Foundation, 1311, 12th A Main, Vijayanagar 1st Stage, Mysuru 570017, Karnataka, India

3\. Work Phone: +91 821 2515601

4\. Email address: [trsr@ncf-india.org](mailto:trsr@ncf-india.org)

5\. Web page:  [http://ncf-india.org/people/t-r-shankar-raman](http://ncf-india.org/people/t-r-shankar-raman)

6\. ORCID: [https://orcid.org/0000-0002-1347-3953](https://orcid.org/0000-0002-1347-3953)

Keywords: bird community, bird conservation, ecological restoration, faunal recovery, forest structure, habitat fragmentation, Western Ghats, rainforest birds

### Geographic Coverage:

1\. Location/Study Area: Valparai Plateau, Tamil Nadu, India; Anamalai Tiger Reserve, Tamil Nadu, India

2\. GPS coordinates: Valparai Plateau (0°15′– 10°22′N, 76°52′–76°59′E); Anamalai Tiger Reserve (10°12′–10°35′N, 76°49′–77°24′E)

### Temporal Coverage:

1\. Begins: 2019-11-05 (Year, Month, Day)

2\. Ends: 2020-03-24 (Year, Month, Day)

### Project Info:

1\. Title: Active restoration fosters better recovery of tropical rainforest birds than natural regeneration in degraded forest fragments

2\. Funding: Financial support from Rohini Nilekani Philanthropies, A.M.M. Murugappa Chettiar Research Centre, Arvind Datar, and the Science and Engineering Board (SERB), India (Research grant: EMR/2016/007968).

## Description of the data and file structure

Dataset:

The dataset includes 1 text file of R code (analysis code in R statistical and programming environment: [http://r-project.org](http://r-project.org)) and 5 data files in comma-delimited format (CSV). Details of content of each CSV data file are provided below. The following files are included:

1\) Bird-restoration.Rmd (R markdown file with R code for analysis)

2\) data.csv (dataset with all bird and mammal detections in 460 point counts of 15 minute duration)

3\) habitat_data.csv (habitat structure data of study plots)

4\) latlong.csv (geographical locations of study plots)

5\) sphabt.csv (bird species list with habit and habitat categorisation)

6\) twentyplot.csv (20x20 m quadrat data for trees)

\*****

### FILE: Bird-restoration.Rmd

Description: Analysis code as a R markdown text file with the code used for analysis in the R statistical and programming environment ([http://r-project.org](http://r-project.org))

\*****

### FILE: data.csv

Description: This data file contains all bird and mammal detections (observations) during the entire survey. It contains the full untruncated bird dataset from 460 point counts of 15 minute duration.

Column headings and explanation, with codes:

* Date: Date of point count survey in Year-Month-Day format (9999-XXX-99)
* Site_ID: Unique Site identifier (last character indicative of Site_type)
* Site_type: Category of site: Restored (Active Restoration or AR in the manuscript), Unrestored (Naturally Regenerating or NR in the manuscript), and Benchmark (Benchmark reference site or BM in the manuscript).
* StartTime: Starting time of point count survey in morning hours (7.05 = 7:05 a.m., 7.4 = 7:40 a.m. and so on)
* TimeSeg: 1-3 indicating first to third 5-minute segment of 15 minute point count survey
* BirdMamm: Bird (Bird); Bird spuhs used when detection was not identified to species level (Birdsp.), or mammal (MAMMAL)
* Species: Species common name in English (India). Scientific names of species are available in the Appendix of published paper.
* Number: Number of individuals detected
* Distance: Radial distance from observer to detection in metres in the following distance classes (detections beyong 50 m were not recorded):
  * 0 = 0-5 m
  * 5 = 5-10 m
  * 10 = 10-15 m
  * 15 = 15-20 m
  * 20 = 20-30 m
  * 30 = 30-50 m.
* HSF: Code indicating whether the detection was by sound (H for heard), sight (S for seen), or of a bird in flight (F - flying)
* Remarks: Notes on observation if any

\*****

### FILE: habitat\_data.csv

Description: This data file contains habitat structure data of study plots

Column headings and explanation, with codes:

* Site_ID: Unique Site identifier (last character indicative of Site_type)
* Site_type: Category of site: Restored (Active Restoration or AR in the manuscript), Unrestored (Naturally Regenerating or NR in the manuscript), and Benchmark (Benchmark reference site or BM in the manuscript).
* LeafLitter: depth of leaf litter (in cm) measured near centre of plot to nearest 0.5 cm
* CanopyOverlap: Score for canopy overlap above the centroid of the plot categorised as 0=open sky overhead; 1=branches overhead but do not overlap; 2=overhead branches overlap with sky showing through; 3=overhead branches overlap with sky not visible
* FoliageScore: number of vertical layers with foliage present at the plot centroid calculated as sum of (presence) scores of next 8 columns
* 0=: scored presence (1) or absence (0) of foliage in the 0-1 m layer
* 1=: scored presence (1) or absence (0) of foliage in the 1-2 m layer
* 2=: scored presence (1) or absence (0) of foliage in the 2-4 m layer
* 4=: scored presence (1) or absence (0) of foliage in the 4-8 m layer
* 8=: scored presence (1) or absence (0) of foliage in the 8-16 m layer
* 16=: scored presence (1) or absence (0) of foliage in the 16-24 m layer
* 24=: scored presence (1) or absence (0) of foliage in the 24-32 m layer
* 32=: scored presence (1) or absence (0) of foliage in the >32 m layer
* Cane: scored presence (1) or absence (0) of cane in a 5 m radius
* Bamboo: scored presence (1) or absence (0) of bamboo in a 5 m radius
* CanCov: canopy cover measured using a spherical densiometer
* Year: Year of restoration planting for Restored sites; marked 0 for Unrestored sites and left blank for Benchmark sites.

\*****

### FILE: latlong.csv

Description: This data file contains geographical locations of study plots.

Column headings and explanation, with codes:

* Site_ID: Unique Site identifier (last character indicative of Site_type)
* lat: Latitude in decimal degrees North
* long: Longitude in decimal degrees East

\*****

### FILE: sphabt.csv

Description: This data file contains bird species list with habit and habitat categorisation.

Column headings and explanation, with codes:

* Species: Species common name in English (India). Scientific names of species are available in the Appendix of published paper.
* Habitat: Habitat affiliation categorised as Rainforest (RF) or Open-Country (OC)
* Habit: Habit based on primary foraging layer of bird species categorised as: AER = Aerial; AQU = aquatic; CAN = Canopy; MID = Mid-storey; SHR = Shrub layer or understorey; TER = Terrestrial or ground layer

\*****

### FILE: twentyplot.csv

Description: This data file contains data from 20x20 m quadrats for trees

Column headings and explanation, with codes:

* WeirdSiteID: Alternative SiteID used in earlier study
* PlotID: Alternative PlotID used in earlier study
* Plant.year: Year of restoration planting in Restored sites (same year is indicated against paired Unrestored sites although not planting was carried out); left blank for Benchmark rainforest sites
* Site_ID: Unique Site identifier (last character indicative of Site_type)
* Site_type: Category of site: Restored (Active Restoration or AR in the manuscript), Unrestored (Naturally Regenerating or NR in the manuscript), and Benchmark (Benchmark reference site or BM in the manuscript).
* treespecies: Scientific name of tree species (all trees ≥10 cm were identiﬁed and girth at breast height (gbh) of main stem and any additional stem measured--next 11 columns)
* gbh1: Main stem girth at breast height in cm measured using a tape measure at 1.3 m above the ground
* gbh2: Additional stem (if any) gbh in cm measured as above
* gbh3: Additional stem (if any) gbh in cm measured as above
* gbh4: Additional stem (if any) gbh in cm measured as above
* gbh5: Additional stem (if any) gbh in cm measured as above
* gbh6: Additional stem (if any) gbh in cm measured as above
* gbh7: Additional stem (if any) gbh in cm measured as above
* gbh8: Additional stem (if any) gbh in cm measured as above
* gbh9: Additional stem (if any) gbh in cm measured as above
* gbh10: Additional stem (if any) gbh in cm measured as above
* gbh11: Additional stem (if any) gbh in cm measured as above
* height: Tree height in metres measured using a Laser rangefinder (visually if less than 9 m)
* Notes: Remarks and notes on corrections if any

