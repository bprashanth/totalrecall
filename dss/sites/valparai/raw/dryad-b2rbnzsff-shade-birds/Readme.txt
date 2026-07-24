This dataset is from:

Raman, T. R. S., Gonsalves, C., Jeganathan, P. and Mudappa, D.  (2021) Native shade trees aid bird conservation in tea plantations in southern India. Current Science 121(2): 294-305. 
doi: 10.18520/cs/v121/i2/294-305.
URL: https://doi.org/10.18520/cs/v121/i2/294-305
Supplementary Table 1 (Table S1) URL: https://www.currentscience.ac.in/Volumes/121/02/0294-suppl.pdf)

Data Set Owner(s):

AUTHOR #1
1. Name: T. R. Shankar Raman (Corresponding author)
2. Work Address: Nature Conservation Foundation, Gokulam Park, Mysore, Karnataka, India
3. Work Phone: +91 821 2515601
4. email address: trsr@ncf-india.org, trsraman@yahoo.com
5. Web page:  http://ncf-india.org/people/t-r-shankar-raman

AUTHOR #2
1. Name: Chayant Gonsalves
2. Present Address: C-01, Good Earth Malhar Footprints, Kambipura Taluk, Kengeri Hobli, Bangalore - 560074, Karnataka, India
3. Work Phone: +91 974 0197015
4. email address: me@chayant.net, chayant.g@gmail.com

AUTHOR #3
1. Name: P. Jeganathan
2. Work Address: Nature Conservation Foundation, Gokulam Park, Mysore, Karnataka, India
3. Work Phone: +91 948 7020110
4. email address: jegan@ncf-india.org
5. Web page:  https://www.ncf-india.org/people/p-jeganathan

AUTHOR #4
1. Name: Divya Mudappa
2. Work Address: Nature Conservation Foundation, Gokulam Park, Mysore, Karnataka, India
3. Work Phone: +91 944 3215215
4. email address: divya@ncf-india.org
5. Web page:  https://www.ncf-india.org/people/divya-mudappa


Key words: monoculture plantations, land use change, shade trees, bird community structure, indicator species, tropical rainforest


Geographic Coverage:

1. Location/Study Area: Valparai, Tamil Nadu, India

2. GPS coordinates 
Valparai Plateau (10°15′ – 10°22′ N, 76°52′ – 76°59′ E)

Temporal Coverage:

1. Begin: 2016-02-09 (Year, Month, Day)
2. End: 2016-03-09 (Year, Month, Day)


Project Info:

1. Title: Native shade trees aid bird conservation in tea plantations in southern India
2. Funding: Financial support from Rohini Nilekani Philanthropies, A.M.M. Murugappa Chettiar Research Centre, Arvind Datar, and the Science and Engineering Board (SERB), India (Research grant:  EMR/2016/007968).

Dataset:
The dataset includes 3 data files in comma-delimited format (CSV) and 2 text files of R code (analysis code in R statistical and programming environment: http://r-project.org). 

Details of content of each CSV data file are provided below:
1) teabirds.csv (bird dataset)
2) sphabt.csv (bird species list with habit and habitat categorisation)
3) dat_with_guilds.csv (bird dataset with dietary guild categorisation)
4) teabirdsanalysis.Rmd (bird data analysis R code)
5) guildanalysis.R (guild data analysis R code)

*****
FILE: teabirds.csv

Description: This data file contains all bird and mammal detections (observations) during the entire survey. It contains the full untruncated bird dataset.

Column headings and explanation, with codes: 

Stratum	Stratum type, with the following stratum codes
			A_Con Tea = Conventionally-managed tea estate
			B_Org Tea = Organic tea estate
			C_Shade Tea = Tea grown under multi-species native trees
			D_Fragment = Rainforest fragment
			E_Rainforest = Contiguous rainforest within Anamalai Tiger Reserve
Replicate	Replicate ID (for corresponding Stratum)
SurveyID	ID for route of 15 points spaced 100 m apart surveyed on same day
Point		Point count ID (for corresponding SurveyID)
Time		Time of survey in the morning (hh:mm)
BirdMamm	Whether bird or mammal 
		BirdMamm Codes
			Bird = Bird
			Mammal = Mammal
Habitat		Open-country (OC) or rainforest (RF) associated (birds only). Unidentified birds and mammals are given NA (not available).
Species		Name of the species detected (sighted/ heard)
Number		Number of individuals detected (sighted/ heard)
Distance	Radial distance interval in metres
		Distance Codes:	
			0 = 0-5 m
			5 = 5-10 m
			10 = 10-15 m
			15 = 15-20 m
			20 = 20-30 m
			30 = 30-50 m
			50 = 50-100 m
			100 = <100 m
 
HSF		Heard, Seen, or Flying
Remarks		General notes about the morphology, habit, call etc

*****
FILE: sphabt.csv

Description: This data file is a bird species list with corresponding habitat (open-country / rainforest association) and habit (foraging layer) attributes as derived from: 
Raman, T. R. S., 2006, Effects of Habitat Structure and Adjacent Habitats on Birds in Tropical Rainforest Fragments and Shaded Plantations in the Western Ghats, India, Biodiversity and Conservation 15, 1577–1607, DOI: 10.1007/s10531-005-2352-5 
(and) Ali, S. and Ripley, S. D., Handbook of the Birds of India and Pakistan Compact edition. Oxford University Press, Delhi, 1983.
Bird English common names follow the 2020 eBird/Clements checklist as implemented in eBird (http://ebird.org)

Column headings and explanation, with codes: 

No		Sl. number
Species		Bird species name
Habitat 	Habitat preference
		Habitat Codes:
			OC = Open Country
			RF = Rainforest
Habit		Foraging level preference
		Habit Codes
			AER = Aerial foraging
			AQU = Aquatic foraging
			CAN = Canopy foraging
			MID = Mid-storey foraging
			SHR = Under-storey / shrub foraging
			TER = Terrestrial foraging

*****
FILE: dat_with_guilds.csv

Description: This data file is a modified version of teabirds.csv, containing only bird detections during the survey period, along with dietary guild categorisation based on:
Wilman, H., Belmaker, J., Simpson, J., de la Rosa, C., Rivadeneira, M. M., and Jetz, W, 2014, EltonTraits 1.0: Species-level foraging attributes of the world’s birds and mammals. Ecology 95: 2027–2027. DOI: 10.1890/13-1917.1 
Records are reordered alphabetically according to scientific names following the 2020 eBird/Clements checklist (http://www.birds.cornell.edu/clementschecklist/) as implemented in eBird (http://ebird.org). All unidentified records and mammal detections are omitted in this file.

Column headings and explanation, with codes: 

Scientific	Latin binomial of the bird species as of 2020 eBird checklist
Species		Name of the bird species detected (sighted/ heard)
Diet.5Cat	5-level categorisation of dietary guild
		Diet Codes
			FruiNect = Frugivores and nectarivores
			Invertebrate = Insectivores
			Omnivore = Omnivores
			PlantSeed = Granivores / seminivores
			VertFishScav = Raptors
Stratum	Stratum type
		Stratum Codes
			A_Con Tea = Conventionally-managed tea estate
			B_Org Tea = Organic tea estate
			C_Shade Tea = Tea grown under multi-species native trees
			D_Fragment = Rainforest fragment
			E_Rainforest = Contiguous rainforest within Anamalai Tiger Reserve
Replicate	Replicate ID (for corresponding Stratum)
SurveyID	ID for route of 15 points spaced 100 m apart surveyed on same day
Point		Point count ID (for corresponding SurveyID)
Time		Time of day in the morning (hh:mm)
Number		Number of individuals detected
Distance	Radial distance interval in metres
		Distance Codes:	
			0 = 0-5 m
			5 = 5-10 m
			10 = 10-15 m
			15 = 15-20 m
			20 = 20-30 m
			30 = 30-50 m
			50 = 50-100 m
			100 = >100 m
HSF		Heard, Seen, or Flying
Remarks		General notes about the morphology, habit, call etc

*****
FILE: teabirdsanalysis.Rmd

Description: This R code file comprises a majority of the analysis presented in our manuscript. Code is annotated where necessary.

*****
FILE: guildanalysis.R

Description: This R code file deals with only analysis of the birds as grouped by specific dietary guilds, along with the relevant plot (Fig 5 in manuscript). Code is annotated where necessary.
