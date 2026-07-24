setwd("") # do not forget to specify the working directory
library(tidyverse)
library(readxl)
library(MASS)
library(vegan)
library(fmsb)
library(broom)
library(betareg)
library(effects)

TreeDat <- read_csv("Osuri_tree_data.csv")
PlotInfo <- read_csv("Osuri_plotInfo.csv")



Adult_summary <- TreeDat %>% filter(Habit == "Tree") %>% group_by(Site_ID) %>% 
  summarise(TDen = n(),
            TRic = n_distinct(Accept_name_WFO),
            Basal = sum(Basal)*100*100/(20*20),
            Carbon = sum(Carbon)*100*100/(20*20),
            WD = mean(Wden_final,na.rm = T),
            Ht = mean(ad_ht, na.rm = T))

#OG refers to "old-growth" or "late-successional" species
OG_adult_summary <- TreeDat %>% filter(Habit == "Tree",
                                            habt_new == "Mature") %>% group_by(Site_ID) %>%
  summarise(OG_TDen = n(),
            OG_TRic = n_distinct(Accept_name_WFO))

#IN refers to "introduced" (non-native) species
IN_adult_summary <- TreeDat %>% filter(habt_new == "Int") %>% group_by(Site_ID) %>%
  summarise(IN_TDen = n(),
            IN_TRic = n_distinct(Accept_name_WFO))

#EN refers to "endemic and/or threatened" species
EN_adult_summary <- TreeDat %>% filter(Habit == "Tree",
                                            Distribution == "Endemic"|
                                              IUCN_status == "CR"|
                                              IUCN_status == "EN"|
                                              IUCN_status == "VU") %>% group_by(Site_ID) %>%
  summarise(EN_TDen = n(),
            EN_TRic = n_distinct(Accept_name_WFO))

#LS refers to "medium- or large-seeded" species
LS_adult_summary <- TreeDat %>% filter(Habit == "Tree",
                                            Distribution != "Introduced",
                                            disperser == "Bird"|
                                              disperser == "Mammal"|
                                              disperser == "Mammal_bird",
                                            seed_size == "L"|
                                              seed_size == "M") %>% group_by(Site_ID) %>%
  summarise(LS_TDen = n(),
            LS_TRic = n_distinct(Accept_name_WFO))

Adult_summary <- Adult_summary %>% left_join(OG_adult_summary, by = "Site_ID") %>%
  left_join(IN_adult_summary, by = "Site_ID") %>% 
  left_join(LS_adult_summary, by = "Site_ID") %>% 
  left_join(EN_adult_summary, by = "Site_ID") %>% 
  replace(is.na(.), 0)

PlotInfo_merge_full <- PlotInfo %>% left_join(Adult_summary, by = "Site_ID") %>% 
  drop_na(CanCover) %>% 
  mutate(CanCover = as.numeric(CanCover)) %>% 
  replace(is.na(.), 0)


# Community dissimilarity
TreeDat_ComDis <- TreeDat %>% left_join(dplyr::select(PlotInfo,Site_ID),by = "Site_ID") %>%
  filter(Habit == "Tree") %>% 
  dplyr::select(Site_ID, Treatment, Accept_name_WFO)

Adult_ComDis_summary <- TreeDat_ComDis %>% group_by(Site_ID, Accept_name_WFO) %>% 
  summarise(Abun = n())

ComDis_matrix_table <- Adult_ComDis_summary %>% pivot_wider(names_from = Accept_name_WFO, values_from = Abun)%>% 
  replace(is.na(.), 0)

ComDis_matrix <- as.matrix(ComDis_matrix_table[,2:ncol(ComDis_matrix_table)])
rownames(ComDis_matrix) <- ComDis_matrix_table$Site_ID


ComDis <- ComDis_matrix %>% vegdist(method="chao", diag = T) %>% as.matrix %>% as_tibble()
ComDis <- tibble(Site_ID = rownames(ComDis_matrix), ComDis)

ComDis_long <- ComDis %>% pivot_longer(cols = A01:VAR4_10U, names_to = "Site_ID2", values_to = "Dissimilarity") %>% 
  mutate(Similarity = 1-Dissimilarity)%>% 
  left_join(dplyr::select(PlotInfo,Site_ID, Treatment),by = c("Site_ID2" = "Site_ID")) %>% 
  rename(Treatment2 = Treatment) %>% 
  filter(Treatment2 == "Benchmark")

ComDis_summary <- ComDis_long %>% group_by(Site_ID) %>% 
  summarise(Similarity = mean(Similarity))

PlotInfo_merge_full <- PlotInfo_merge_full %>% left_join(ComDis_summary, by = "Site_ID") %>% 
  replace_na(list(Similarity=0))

PlotInfo_merge_sim <- PlotInfo_merge_full %>% 
  filter(Treatment != "Benchmark")

#GLMs
Yvar <- c("TDen", "TRic", "OG_TRic", "LS_TRic", "EN_TRic")
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
  Y <- PlotInfo_merge_sim %>% dplyr::select(starts_with(Yvar)) %>% pull()
  BM <-PlotInfo_merge_full %>% filter(Treatment == "Benchmark") %>% 
    dplyr::select(starts_with(Yvar)) %>% pull()
  X <- PlotInfo_merge_sim %>% pull(CanCover)
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

  
  
  ggsave(filename = paste("Figures/AD",Yvar,".png",sep=""), 
         device = "png",
         plot = P1,
         width = 6,
         height = 6,
         dpi = 300)   
}

# beta regression
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
  Y <- PlotInfo_merge_sim %>% dplyr::select(starts_with(Yvar)) %>% pull()+0.00001
  BM <-PlotInfo_merge_full %>% filter(Treatment == "Benchmark") %>% 
    dplyr::select(starts_with(Yvar)) %>% pull()
  X <- PlotInfo_merge_sim %>% pull(CanCover)
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
  Input2$Rsq[i] <- summary(m1)$pseudo.r.squared
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
  
  
  ggsave(filename = paste("Figures/AD",Yvar,".png",sep=""), 
         device = "png",
         plot = P1,
         width = 6,
         height = 6,
         dpi = 300)   
}


# LMs
Yvar <- c("Carbon", "WD")
YName <- c("Aboveground carbon (T/ha)", "Average wood density")
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
  Y <- PlotInfo_merge_sim %>% dplyr::select(starts_with(Yvar)) %>% pull()
  BM <-PlotInfo_merge_full %>% filter(Treatment == "Benchmark") %>% 
    dplyr::select(starts_with(Yvar)) %>% pull()
  X <- PlotInfo_merge_sim %>% pull(CanCover)
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
  
  ggsave(filename = paste("Figures/AD",Yvar,".png",sep=""), 
         device = "png",
         plot = P1,
         width = 6,
         height = 6,
         dpi = 300)   
}


Adult_table <-bind_rows(Input1,Input2,Input3) %>% dplyr::select(-YName)

Adult_pivot <- tibble ("Yvar" = rep(Adult_table$Yvar,2),
                       "Canopy" = c(rep("1.Open",nrow(Adult_table)),rep("2.Closed",nrow(Adult_table))),
                       "Perc_mean" = 100*c(Adult_table$Op_can_mean,Adult_table$Cl_can_mean),
                       "Perc_lo" = 100*c(Adult_table$Op_can_lo,Adult_table$Cl_can_lo),
                       "Perc_hi" = 100*c(Adult_table$Op_can_hi,Adult_table$Cl_can_hi))



P2 <- ggplot(data = Adult_pivot)+
  geom_bar(mapping = aes(x = Yvar, y = Perc_mean, fill = Canopy), col = 'black',stat = "identity", 
           position = position_dodge(.9),show.legend = F)+
  geom_errorbar(mapping = aes(x = Yvar, y = Perc_mean, ymin = Perc_lo, ymax = Perc_hi, fill = Canopy), 
                position = position_dodge(.9),width = 0.2, lwd = 1.5)+
  scale_fill_manual(values=c("#c9dfc8","#416d3e"))+
  scale_x_discrete(limits = c("TDen","TRic", "OG_TRic","LS_TRic","EN_TRic",
                              "Similarity", "WD", "Carbon"),
                   labels = c("TDen" = "DEN", "TRic" = "SPD", "OG_TRic" = "OGS",
                              "LS_TRic" = "LSS", "EN_TRic" = "ETS",
                              "Similarity" = "SIM", "WD" = "WD", "Carbon" = "ACS"))+
  ylim(0,100)+
  xlab("")+
  ylab("% reference rainforest value")+
  theme_classic(base_size = 20)
ggsave(filename = "Figures/ADPerc.png", 
       device = "png",
       plot = P2,
       width = 12,
      height = 6,
       dpi = 300)



