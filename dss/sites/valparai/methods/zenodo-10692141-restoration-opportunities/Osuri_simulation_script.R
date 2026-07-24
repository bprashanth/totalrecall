setwd("") # do not forget to specify the working directory
library(tidyverse)
library(readxl)
library(MASS)
library(gridExtra)
library(vegan)
set.seed(10)

Regen_treatments <- read_csv("Regen_summary_closed_canopy.csv")
PlotInfo <- read_csv("Osuri_plotInfo.csv")
TreeDat <- read_csv("Osuri_tree_data.csv")
Tree_benchmark <- TreeDat %>% filter(Treatment == "Benchmark")
Tree_fragment <- TreeDat %>% filter(Treatment == "Fragment")

RegDat <- read_csv("Osuri_regen_data.csv")

Regen_uncount <- RegDat %>% uncount(Abun) %>% mutate(Abun = 1) %>% 
  dplyr::select(-Abun)

URPlots <- Regen_uncount %>% filter(Treatment == "Fragment")
BMPlots <- Regen_uncount %>% filter(Treatment == "Benchmark")
PlotList <-PlotInfo %>%
  filter(Treatment == "Fragment",
         CanCover >=50) %>% 
  pull(Site_ID) %>% unique()

Rest_frame <- tibble(OG_RRic = numeric(1000),
                     LS_RRic = numeric(1000),
                     EN_RRic = numeric(1000),
                     WD = numeric(1000),
                     Similarity = numeric(1000))

Unrest_frame <- tibble(OG_RRic = numeric(1000),
                       LS_RRic = numeric(1000),
                       EN_RRic = numeric(1000),
                       WD = numeric(1000),
                       Similarity = numeric(1000))

ComSim <- function(x){
  Name <- x$Site_ID[1]
  Comm_tibble <- x %>% bind_rows(BMPlots) %>% mutate(Abun = 1)
  Comm_tibble_summary <- Comm_tibble %>% group_by(Site_ID, Accept_name_WFO) %>% 
    summarise(Abun = sum(Abun))
  
  ComDis_matrix_table <- Comm_tibble_summary %>% pivot_wider(names_from = Accept_name_WFO, values_from = Abun)%>% 
    replace(is.na(.), 0)
  
  ComDis_matrix <- as.matrix(ComDis_matrix_table[,2:ncol(ComDis_matrix_table)])
  rownames(ComDis_matrix) <- ComDis_matrix_table$Site_ID
  
  
  ComDis <- ComDis_matrix %>% vegdist(method="chao", diag = T) %>% as.matrix %>% as_tibble()
  ComDis <- tibble(Site_ID = rownames(ComDis_matrix), ComDis)
  
  ComDis_value <- ComDis %>% filter(Site_ID == Name) %>% 
    dplyr::select(-matches(Name), -Site_ID) %>% as.numeric() %>% mean()
  Comsim_value <- 1 - ComDis_value
}

for (i in 1:1000){
  plotSelect <-sample(PlotList,1)
  iPlot <- URPlots %>% filter(Site_ID == plotSelect) %>% dplyr::select(-Site_ID)
  BM_sample <- Tree_benchmark %>% 
    filter(habt_new != "Int",
           Habit == "Tree") %>% 
    slice_sample(n = 20,replace = T) %>% 
    dplyr::select(-Site_ID)
  iRestPlot <- bind_rows(iPlot,BM_sample)
  iRestPlot <- tibble("Site_ID" = plotSelect,iRestPlot)
  Rest_RRic <- iRestPlot %>% pull(Accept_name_WFO) %>% n_distinct()
  Rest_frame$OG_RRic[i] <- iRestPlot %>% filter(habt_new == "Mature") %>% pull(Accept_name_WFO) %>% n_distinct()
  Rest_frame$LS_RRic[i] <- iRestPlot %>% filter(disperser == "Mammal" | disperser == "Bird" | disperser == "Mammal_bird",
                                                seed_size == "M" | seed_size == "L") %>% pull(Accept_name_WFO) %>% n_distinct()
  Rest_frame$EN_RRic[i] <- iRestPlot %>% filter(Accept_name_WFO !="Coffea canephora",
                                                Distribution == "Endemic" | 
                                                  IUCN_status == "CR" | IUCN_status == "EN" | IUCN_status == "VU") %>% pull(Accept_name_WFO) %>% n_distinct()
  Rest_frame$WD[i] <- mean(iRestPlot$Wden_final, na.rm = T)
  Rest_frame$Similarity[i] <- ComSim(iRestPlot)
  
  UR_sample <- Tree_fragment %>% filter(Site_ID == plotSelect) %>%
    slice_sample(n = 20,replace = T) %>% 
    dplyr::select(-Site_ID)
  iUnrestPlot <- bind_rows(iPlot,UR_sample)
  iUnrestPlot <- tibble("Site_ID" = plotSelect,iUnrestPlot)
  Unrest_RRic <- iUnrestPlot %>% pull(Accept_name_WFO) %>% n_distinct()
  Unrest_frame$OG_RRic[i] <- iUnrestPlot %>% filter(habt_new == "Mature") %>% pull(Accept_name_WFO) %>% n_distinct()
  Unrest_frame$LS_RRic[i] <- iUnrestPlot %>% filter(disperser == "Mammal" | disperser == "Bird" | disperser == "Mammal_bird",
                                                    seed_size == "M" | seed_size == "L") %>% pull(Accept_name_WFO) %>% n_distinct()
  Unrest_frame$EN_RRic[i] <- iUnrestPlot %>% filter(Accept_name_WFO !="Coffea canephora",
                                                    Distribution == "Endemic" | 
                                                      IUCN_status == "CR" | IUCN_status == "EN" | IUCN_status == "VU") %>% pull(Accept_name_WFO) %>% n_distinct()
  Unrest_frame$WD[i] <- mean(iUnrestPlot$Wden_final, na.rm = T)
  Unrest_frame$Similarity[i] <- ComSim(iUnrestPlot)
  print(i)
}

Rest_frame <- Rest_frame %>% mutate(Type = "Enrichment")
Unrest_frame <- Unrest_frame %>% mutate(Type = "Control")
Sim_frame <- bind_rows(Rest_frame, Unrest_frame)

Var <- c("OG_RRic","LS_RRic","EN_RRic", "WD",
         "Similarity")
Var_name <- c("Old-growth species", "Large-seeded species",
              "Threatened or endemic species", "Wood density",
              "Similarity to reference forest")
Dev_diff <- numeric(length(Var))
Recovery <- numeric(length(Var))
Labels <-tibble(Var, Var_name, Recovery, Dev_diff)

SD_calc <- function(Var){
  tib <- Sim_frame %>% dplyr::select(Type, starts_with(Var))
  names(tib) <- c("Type","response")
  tib_summ <- tib %>% 
    group_by(Type) %>%
    summarise(Mn = mean(response),
              Sd = sd(response))
  (tib_summ[2,2]-tib_summ[1,2])/tib_summ[1,3]
}


for (i in 1:nrow(Labels)){
  PlotLines <- Regen_treatments %>% dplyr::select(starts_with(Labels$Var[i])) %>% pull()
  DELine <- PlotLines[2]
  BMLine <- PlotLines[1]
  PlotFrame <- Sim_frame %>% dplyr::select(Type, starts_with(Labels$Var[i]))
  names(PlotFrame) <- c("Type","response")
  Labels$Recovery[i] <- PlotFrame %>% filter(Type == "Enrichment") %>% 
    summarise(mean(response))
  Labels$Dev_diff[i] <- as.numeric(SD_calc(Labels$Var[i]))
  
  
  S1 <- ggplot()+
    geom_hline(yintercept = BMLine, lwd = 1.5, lty = 2)+
    geom_hline(yintercept = DELine, lwd = 1.5, lty = 3)+
    geom_violin(data = PlotFrame, mapping = aes(x = Type, y = response, fill = Type),alpha = 0.6) +
    stat_summary(data = PlotFrame, mapping = aes(x = Type, y = response, fill = Type), fun = mean, geom="point", shape=23, size=3)+
    ylab(Labels$Var_name[i])+
    xlab("")+
    scale_fill_manual(values=c("#416d3e","#416d3e")) +
    theme_classic(base_size = 20)+
    theme(legend.position = "none")

    ggsave(filename = paste("Figures/SI",Labels$Var[i],".png",sep=""), 
         device = "png",
         plot = S1,
         width = 6,
         height = 6,
         dpi = 300)   
}