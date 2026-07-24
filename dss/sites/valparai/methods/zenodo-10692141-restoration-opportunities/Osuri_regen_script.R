setwd("") # do not forget to specify the working directory
library(tidyverse)
library(readxl)
library(MASS)
library(vegan)
library(fmsb)
library(broom)
library(betareg)
library(effects)

RegDat <- read_csv("Osuri_regen_data.csv")
PlotInfo <- read_csv("Osuri_plotInfo.csv")

Regen_summary <- RegDat %>% filter(Habit == "Tree") %>% group_by(Site_ID) %>% 
  summarise(RDen = sum(Abun),
            RRic = n_distinct(Accept_name_WFO),
            WD = mean(Wden_final,na.rm = T))

#OG refers to "old-growth" or "late-successional" species
OG_regen_summary <- RegDat %>% filter(Habit == "Tree",
                                            habt_new == "Mature") %>% group_by(Site_ID) %>%
  summarise(OG_RDen = sum(Abun),
            OG_RRic = n_distinct(Accept_name_WFO))

#IN refers to "introduced" (non-native) species
IN_regen_summary <- RegDat %>% filter(Habit == "Tree",
                                            habt_new == "Int") %>% group_by(Site_ID) %>%
  summarise(IN_RDen = sum(Abun),
            IN_RRic = n_distinct(Accept_name_WFO))

#EN refers to "endemic and/or threatened" species
EN_regen_summary <- RegDat %>% filter(Habit == "Tree",
                                            Distribution == "Endemic"|
                                              IUCN_status == "CR"|
                                              IUCN_status == "EN"|
                                              IUCN_status == "VU") %>% group_by(Site_ID) %>%
  summarise(EN_RDen = sum(Abun),
            EN_RRic = n_distinct(Accept_name_WFO))

#LS refers to "medium- or large-seeded" species
LS_regen_summary <- RegDat %>% filter(Habit == "Tree",
                                            Distribution != "Introduced",
                                            disperser == "Bird"|
                                              disperser == "Mammal"|
                                              disperser == "Mammal_bird",
                                            seed_size == "L"|
                                              seed_size == "M") %>% group_by(Site_ID) %>%
  summarise(LS_RDen = sum(Abun),
            LS_RRic = n_distinct(Accept_name_WFO))

Regen_summary <- Regen_summary %>% left_join(OG_regen_summary, by = "Site_ID") %>%
  left_join(IN_regen_summary, by = "Site_ID") %>% 
  left_join(LS_regen_summary, by = "Site_ID") %>% 
  left_join(EN_regen_summary, by = "Site_ID") %>% 
  replace(is.na(.), 0)

PlotInfo_Full <- PlotInfo %>% left_join(Regen_summary, by = "Site_ID") %>% 
  drop_na(CanCover) %>%
  replace(is.na(.), 0) %>%
  dplyr::select(Site_ID, Treatment, CanCover, RDen:EN_RRic)

#Community dissimilarity

RegDat_ComDis <- RegDat %>% left_join(dplyr::select(PlotInfo_Full,Site_ID),by = "Site_ID") %>%
  filter(Habit == "Tree") %>% 
  dplyr::select(Site_ID, Treatment, Accept_name_WFO, Abun)

Regen_ComDis_summary <- RegDat_ComDis %>% group_by(Site_ID, Accept_name_WFO) %>% 
  summarise(Abun = sum(Abun))

ComDis_matrix_table <- Regen_ComDis_summary %>% pivot_wider(names_from = Accept_name_WFO, values_from = Abun)%>% 
  replace(is.na(.), 0)

ComDis_matrix <- as.matrix(ComDis_matrix_table[,2:ncol(ComDis_matrix_table)])
rownames(ComDis_matrix) <- ComDis_matrix_table$Site_ID


ComDis <- ComDis_matrix %>% vegdist(method="chao", diag = T) %>% as.matrix %>% as_tibble()
ComDis <- tibble(Site_ID = rownames(ComDis_matrix), ComDis)

ComDis_long <- ComDis %>% pivot_longer(cols = A01:VAR4_10U, names_to = "Site_ID2", values_to = "Dissimilarity") %>% 
  mutate(Similarity = 1-Dissimilarity)%>% 
  left_join(dplyr::select(PlotInfo_Full,Site_ID, Treatment),by = c("Site_ID2" = "Site_ID")) %>% 
  rename(Treatment2 = Treatment) %>% 
  filter(Treatment2 == "Benchmark")

ComDis_summary <- ComDis_long %>% group_by(Site_ID) %>% 
  summarise(Similarity = mean(Similarity))

PlotInfo_Full <- PlotInfo_Full %>% left_join(ComDis_summary, by = "Site_ID")

PlotInfo_Trim <- PlotInfo_Full %>% 
  filter(Treatment != "Benchmark") %>% 
  replace(is.na(.), 0)

#GLMs
Yvar <- c("RDen", "RRic", "OG_RRic", "LS_RRic", "EN_RRic")
YName <- c("Tree density", "Species density", "Old-growth species",
           "Large-seeded species", "Threatened or endemic species")
Int_mean <- numeric(length(Yvar))
Int_se <- numeric(length(Yvar))
Int_pval <- numeric(length(Yvar))
Slo_mean <- numeric(length(Yvar))
Slo_se <- numeric(length(Yvar))
Slo_pval <- numeric(length(Yvar))
Rsq <- numeric(length(Yvar))
Op_can_mean <- numeric(length(Yvar))
Op_can_lo <- numeric(length(Yvar))
Op_can_hi <- numeric(length(Yvar))
Cl_can_mean <- numeric(length(Yvar))
Cl_can_lo <- numeric(length(Yvar))
Cl_can_hi <- numeric(length(Yvar))
Input1 <- tibble (Yvar, YName,Int_mean,Int_se,Int_pval,Slo_mean,Slo_se,Slo_pval,Rsq,
                  Op_can_mean,Op_can_lo,Op_can_hi,Cl_can_mean,Cl_can_lo,Cl_can_hi)

for (i in 1:nrow(Input1)){
  Yvar <- Input1$Yvar[i]
  YName <- Input1$YName[i]
  Y <- PlotInfo_Trim %>% dplyr::select(starts_with(Yvar)) %>% pull()
  BM <-PlotInfo_Full %>% filter(Treatment == "Benchmark") %>% 
    dplyr::select(starts_with(Yvar)) %>% pull()
  X <- PlotInfo_Trim %>% pull(CanCover)
  m1 <- glm.nb(Y~X)
  m1_s <- tidy(m1)
  x <- tibble(X = seq(0, 100, 5))
  y <- predict(m1, newdata = x ,type = "response", se.fit = T)
  pred_table <-tibble(y_mean = y$fit, y_lo = y$fit-1.96*y$se.fit, y_hi = y$fit+1.96*y$se.fit)
  pred_table <-tibble(x, pred_table)
  bm <- mean(BM)
  
  Input1$Int_mean[i] <- m1_s$estimate[1]
  Input1$Int_se[i] <- m1_s$std.error[1]
  Input1$Int_pval[i] <- m1_s$p.value[1]
  Input1$Slo_mean[i] <- m1_s$estimate[2]
  Input1$Slo_se[i] <- m1_s$std.error[2]
  Input1$Slo_pval[i] <- m1_s$p.value[2]
  Input1$Rsq[i] <- NagelkerkeR2(m1)$R2
  Input1$Op_can_mean[i] <- pred_table %>% filter(X ==30) %>% dplyr::select(y_mean) %>% as.numeric()/bm
  Input1$Op_can_lo[i] <- pred_table %>% filter(X ==30) %>% dplyr::select(y_lo) %>% as.numeric()/bm
  Input1$Op_can_hi[i] <- pred_table %>% filter(X ==30) %>% dplyr::select(y_hi) %>% as.numeric()/bm
  Input1$Cl_can_mean[i] <- pred_table %>% filter(X ==75) %>% dplyr::select(y_mean) %>% as.numeric()/bm
  Input1$Cl_can_lo[i] <- pred_table %>% filter(X ==75) %>% dplyr::select(y_lo) %>% as.numeric()/bm
  Input1$Cl_can_hi[i] <- pred_table %>% filter(X ==75) %>% dplyr::select(y_hi) %>% as.numeric()/bm
  
  P1 <- ggplot() +
    geom_point(mapping = aes(x = X, y = Y)) +
    geom_line(data = pred_table, mapping = aes(x = X, y = y_mean), color = "#FF0000", lwd=2,
              lty = ifelse(m1_s$p.value[2]<0.05,1,2)) +
    geom_ribbon(data = pred_table, aes(x = X, ymin = y_lo, ymax = y_hi), fill = "#FF0000", alpha = 0.2)+
    ylab(YName)+
    xlab("Canopy cover (%)")+
    geom_hline(yintercept = bm, color = "#00008B", lwd = 1.5) +
    theme_classic(base_size = 20)
  ggsave(filename = paste("Figures/RE",Yvar,".png",sep=""), 
         device = "png",
         plot = P1,
         width = 6,
         height = 6,
         dpi = 300)   
}

#beta regression
Yvar <- c("Similarity")
YName <- c("Similarity to reference forest")
Int_mean <- numeric(length(Yvar))
Int_se <- numeric(length(Yvar))
Int_pval <- numeric(length(Yvar))
Slo_mean <- numeric(length(Yvar))
Slo_se <- numeric(length(Yvar))
Slo_pval <- numeric(length(Yvar))
Rsq <- numeric(length(Yvar))
Op_can_mean <- numeric(length(Yvar))
Op_can_lo <- numeric(length(Yvar))
Op_can_hi <- numeric(length(Yvar))
Cl_can_mean <- numeric(length(Yvar))
Cl_can_lo <- numeric(length(Yvar))
Cl_can_hi <- numeric(length(Yvar))
Input2 <- tibble (Yvar, YName,Int_mean,Int_se,Int_pval,Slo_mean,Slo_se,Slo_pval,Rsq,
                  Op_can_mean,Op_can_lo,Op_can_hi,Cl_can_mean,Cl_can_lo,Cl_can_hi)

for (i in 1:nrow(Input2)){
  Yvar <- Input2$Yvar[i]
  YName <- Input2$YName[i]
  Y <- PlotInfo_Trim %>% dplyr::select(starts_with(Yvar)) %>% pull()+0.00001
  BM <-PlotInfo_Full %>% filter(Treatment == "Benchmark") %>% 
    dplyr::select(starts_with(Yvar)) %>% pull()
  X <- PlotInfo_Trim %>% pull(CanCover)
  m1 <- betareg(Y~X)
  m1_s <- tidy(m1)
  x <- tibble(X = seq(0, 100, 5))
  y <- as.data.frame(predictorEffects(m1, focal.levels=21))$X
  pred_table <-tibble(y_mean = y$fit , y_lo = y$lower, y_hi = y$upper)
  pred_table <-tibble(x, pred_table)
  bm <- mean(BM)
  
  Input2$Int_mean[i] <- m1_s$estimate[1]
  Input2$Int_se[i] <- m1_s$std.error[1]
  Input2$Int_pval[i] <- m1_s$p.value[1]
  Input2$Slo_mean[i] <- m1_s$estimate[2]
  Input2$Slo_se[i] <- m1_s$std.error[2]
  Input2$Slo_pval[i] <- m1_s$p.value[2]
  Input2$Rsq[i] <- m1$pseudo.r.squared
  Input2$Op_can_mean[i] <- pred_table %>% filter(X ==30) %>% dplyr::select(y_mean) %>% as.numeric()/bm
  Input2$Op_can_lo[i] <- pred_table %>% filter(X ==30) %>% dplyr::select(y_lo) %>% as.numeric()/bm
  Input2$Op_can_hi[i] <- pred_table %>% filter(X ==30) %>% dplyr::select(y_hi) %>% as.numeric()/bm
  Input2$Cl_can_mean[i] <- pred_table %>% filter(X ==75) %>% dplyr::select(y_mean) %>% as.numeric()/bm
  Input2$Cl_can_lo[i] <- pred_table %>% filter(X ==75) %>% dplyr::select(y_lo) %>% as.numeric()/bm
  Input2$Cl_can_hi[i] <- pred_table %>% filter(X ==75) %>% dplyr::select(y_hi) %>% as.numeric()/bm
  
  P1 <- ggplot() +
    geom_point(mapping = aes(x = X, y = Y)) +
    geom_line(data = pred_table, mapping = aes(x = X, y = y_mean), color = "#FF0000", lwd=2,
              lty = ifelse(m1_s$p.value[2]<0.05,1,2)) +
    geom_ribbon(data = pred_table, aes(x = X, ymin = y_lo, ymax = y_hi), fill = "#FF0000", alpha = 0.2)+
    ylab(YName)+
    xlab("Canopy cover (%)")+
    geom_hline(yintercept = bm, color = "#00008B", lwd = 1.5) +
    theme_classic(base_size = 20)
  ggsave(filename = paste("Figures/RE",Yvar,".png",sep=""), 
         device = "png",
         plot = P1,
         width = 6,
         height = 6,
         dpi = 300)   
}


# LMs
Yvar <- c("WD")
YName <- c("Average wood density")
Int_mean <- numeric(length(Yvar))
Int_se <- numeric(length(Yvar))
Int_pval <- numeric(length(Yvar))
Slo_mean <- numeric(length(Yvar))
Slo_se <- numeric(length(Yvar))
Slo_pval <- numeric(length(Yvar))
Rsq <- numeric(length(Yvar))
Op_can_mean <- numeric(length(Yvar))
Op_can_lo <- numeric(length(Yvar))
Op_can_hi <- numeric(length(Yvar))
Cl_can_mean <- numeric(length(Yvar))
Cl_can_lo <- numeric(length(Yvar))
Cl_can_hi <- numeric(length(Yvar))
Input3 <- tibble (Yvar, YName,Int_mean,Int_se,Int_pval,Slo_mean,Slo_se,Slo_pval,Rsq,
                  Op_can_mean,Op_can_lo,Op_can_hi,Cl_can_mean,Cl_can_lo,Cl_can_hi)

for (i in 1:nrow(Input3)){
  Yvar <- Input3$Yvar[i]
  YName <- Input3$YName[i]
  Y <- PlotInfo_Trim %>% dplyr::select(starts_with(Yvar)) %>% pull()
  BM <-PlotInfo_Full %>% filter(Treatment == "Benchmark") %>% 
    dplyr::select(starts_with(Yvar)) %>% pull()
  X <- PlotInfo_Trim %>% pull(CanCover)
  m1 <- lm(Y~X)
  m1_s <- tidy(m1)
  x <- tibble(X = seq(0, 100, 5))
  y <- predict(m1, newdata = x ,type = "response", se.fit = T)
  pred_table <-tibble(y_mean = y$fit, y_lo = y$fit-1.96*y$se.fit, y_hi = y$fit+1.96*y$se.fit)
  pred_table <-tibble(x, pred_table)
  bm <- mean(BM)
  
  Input3$Int_mean[i] <- m1_s$estimate[1]
  Input3$Int_se[i] <- m1_s$std.error[1]
  Input3$Int_pval[i] <- m1_s$p.value[1]
  Input3$Slo_mean[i] <- m1_s$estimate[2]
  Input3$Slo_se[i] <- m1_s$std.error[2]
  Input3$Slo_pval[i] <- m1_s$p.value[2]
  Input3$Rsq[i] <- summary(m1)$adj.r.squared
  Input3$Op_can_mean[i] <- pred_table %>% filter(X ==30) %>% dplyr::select(y_mean) %>% as.numeric()/bm
  Input3$Op_can_lo[i] <- pred_table %>% filter(X ==30) %>% dplyr::select(y_lo) %>% as.numeric()/bm
  Input3$Op_can_hi[i] <- pred_table %>% filter(X ==30) %>% dplyr::select(y_hi) %>% as.numeric()/bm
  Input3$Cl_can_mean[i] <- pred_table %>% filter(X ==75) %>% dplyr::select(y_mean) %>% as.numeric()/bm
  Input3$Cl_can_lo[i] <- pred_table %>% filter(X ==75) %>% dplyr::select(y_lo) %>% as.numeric()/bm
  Input3$Cl_can_hi[i] <- pred_table %>% filter(X ==75) %>% dplyr::select(y_hi) %>% as.numeric()/bm
  
  P1 <- ggplot() +
    geom_point(mapping = aes(x = X, y = Y)) +
    geom_line(data = pred_table, mapping = aes(x = X, y = y_mean), color = "#FF0000", lwd=2,
              lty = ifelse(m1_s$p.value[2]<0.05,1,2)) +
    geom_ribbon(data = pred_table, aes(x = X, ymin = y_lo, ymax = y_hi), fill = "#FF0000", alpha = 0.2)+
    ylab(YName)+
    xlab("Canopy cover (%)")+
    geom_hline(yintercept = bm, color = "#00008B", lwd = 1.5) +
    theme_classic(base_size = 20)
ggsave(filename = paste("Figures/RE",Yvar,".png",sep=""), 
         device = "png",
         plot = P1,
         width = 6,
         height = 6,
         dpi = 300)   
}

Regen_table <-bind_rows(Input1,Input2,Input3) %>% dplyr::select(-YName)
Regen_pivot <- tibble ("Yvar" = rep(Regen_table$Yvar,2),
                       "Canopy" = c(rep("1.Open",nrow(Regen_table)),rep("2.Closed",nrow(Regen_table))),
                       "Perc_mean" = 100*c(Regen_table$Op_can_mean,Regen_table$Cl_can_mean),
                       "Perc_lo" = 100*c(Regen_table$Op_can_lo,Regen_table$Cl_can_lo),
                       "Perc_hi" = 100*c(Regen_table$Op_can_hi,Regen_table$Cl_can_hi))



P2 <- ggplot(data = Regen_pivot)+
  geom_bar(mapping = aes(x = Yvar, y = Perc_mean, fill = Canopy), color = 'black', stat = "identity", 
           position = position_dodge(.9))+
  geom_errorbar(mapping = aes(x = Yvar, y = Perc_mean, ymin = Perc_lo, ymax = Perc_hi, fill = Canopy), 
                position = position_dodge(.9),width = 0.2, lwd = 1.5)+
  scale_x_discrete(limits = c("RDen","RRic", "OG_RRic","LS_RRic","EN_RRic",
                              "Similarity", "WD"),
                   labels = c("RDen" = "DEN", "RRic" = "SPD", "OG_RRic" = "OGS",
                              "LS_RRic" = "LSS", "EN_RRic" = "ETS", "WD" = "WD",
                              "Similarity" = "SIM"))+
  ylim(0,100)+
  xlab("")+
  ylab("% reference rainforest value")+
  scale_fill_manual(values=c("#c9dfc8","#416d3e"), labels = c("Open (30%)", "Closed (75%)"))+
  theme_classic(base_size = 20)

ggsave(filename = "Figures/REPerc.png", 
       device = "png",
       plot = P2,
       width = 12,
       height = 6,
       dpi = 300)

#Treatment summary for simulations
Regen_treatments <- PlotInfo_Full %>%
  replace(is.na(.), 0) %>% 
  filter(Treatment == "Benchmark" | CanCover >= 50) %>% 
  group_by(Treatment) %>% 
  summarize(
    RDen = mean(RDen),
    RRic = mean(RRic),
    OG_RRic = mean(OG_RRic),
    LS_RRic = mean(LS_RRic),
    EN_RRic = mean(EN_RRic),
    WD = mean(WD),
    Similarity = mean(Similarity))
write_csv(Regen_treatments, "Regen_summary_closed_canopy.csv")
