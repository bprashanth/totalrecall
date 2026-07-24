setwd("") # do not forget to specify the working directory
library(ggpubr)
library(png)
library(grid)

#Figure 2
ADPerc <- rasterGrob(readPNG("Figures/ADPerc.png"), interpolate=TRUE)
REPerc <- rasterGrob(readPNG("Figures/REPerc.png"), interpolate=TRUE)
Perc_fig <- ggarrange(ADPerc,REPerc,ncol=1, labels = c("a.","b."),label.y = 1)
ggsave(filename = "Figures/Fig_2.png", 
       device = "png",
       plot = Perc_fig,
       width = 8,
       height = 8,
       dpi = 300)

#Figure 3
SIOG_RRic <- rasterGrob(readPNG("Figures/SIOG_RRic.png"), interpolate=TRUE)
SILS_RRic <- rasterGrob(readPNG("Figures/SILS_RRic.png"), interpolate=TRUE)
SIEN_RRic <- rasterGrob(readPNG("Figures/SIEN_RRic.png"), interpolate=TRUE)
SISimilarity <- rasterGrob(readPNG("Figures/SISimilarity.png"), interpolate=TRUE)
SIWD <- rasterGrob(readPNG("Figures/SIWD.png"), interpolate=TRUE)

Sim_fig <- ggarrange(SIOG_RRic,SILS_RRic,SIEN_RRic,SISimilarity,SIWD,
                     ncol=3, nrow=2,labels = c("a.","b.","c.","d.","e."),
                     label.y = 1, font.label = list(size=20))

ggsave(filename = "Figures/Fig_3.png", 
       device = "png",
       plot = Sim_fig,
       width = 18,
       height = 12,
       dpi = 300)

#Figure S3
ADTDen <- rasterGrob(readPNG("Figures/ADTDen.png"), interpolate=TRUE)
ADTRic <- rasterGrob(readPNG("Figures/ADTRic.png"), interpolate=TRUE)
ADOG_TRic <- rasterGrob(readPNG("Figures/ADOG_TRic.png"), interpolate=TRUE)
ADLS_TRic <- rasterGrob(readPNG("Figures/ADLS_TRic.png"), interpolate=TRUE)
ADEN_TRic <- rasterGrob(readPNG("Figures/ADEN_TRic.png"), interpolate=TRUE)
ADSimilarity <- rasterGrob(readPNG("Figures/ADSimilarity.png"), interpolate=TRUE)
ADWD <- rasterGrob(readPNG("Figures/ADWD.png"), interpolate=TRUE)
ADCarbon <- rasterGrob(readPNG("Figures/ADCarbon.png"), interpolate=TRUE)

Adult_fig <- ggarrange(ADTDen,ADTRic,ADOG_TRic,ADLS_TRic,
                       ADEN_TRic,ADSimilarity, ADWD, ADCarbon,ncol=4, nrow=2,
                       labels = c("a.","b.","c.","d.","e.", "f.","g.","h."),
                       label.y = 1)

ggsave(filename = "Figures/Fig_S3.png", 
       device = "png",
       plot = Adult_fig,
       width = 16,
       height = 8,
       dpi = 300)

#Figure S4
RERDen <- rasterGrob(readPNG("Figures/RERDen.png"), interpolate=TRUE)
RERRic <- rasterGrob(readPNG("Figures/RERRic.png"), interpolate=TRUE)
REOG_RRic <- rasterGrob(readPNG("Figures/REOG_RRic.png"), interpolate=TRUE)
RELS_RRic <- rasterGrob(readPNG("Figures/RELS_RRic.png"), interpolate=TRUE)
REEN_RRic <- rasterGrob(readPNG("Figures/REEN_RRic.png"), interpolate=TRUE)
RESimilarity <- rasterGrob(readPNG("Figures/RESimilarity.png"), interpolate=TRUE)
REWD <- rasterGrob(readPNG("Figures/REWD.png"), interpolate=TRUE)

Reg_fig <- ggarrange(RERDen,RERRic,REOG_RRic,RELS_RRic,
                     REEN_RRic,RESimilarity, REWD,ncol=4, nrow=2,
                     labels = c("a.","b.","c.","d.","e.", "f.","g."),
                     label.y = 1)

ggsave(filename = "Figures/Fig_S4.png", 
       device = "png",
       plot = Reg_fig,
       width = 16,
       height = 8,
       dpi = 300)

#Figure S5
# Rerun the scripts "Osuri_trees_script.R" and "Osuri_regen_script.R" after filtering
# out data rows from the Candura fragment. Steps: 
# 1. In "Osuri_trees_script.R", paste "%>% filter(FragmentName!="Candura")" at the end of line 98
# 2. In "Osuri_regen_script.R", paste "%>% filter(FragmentName!="Candura")" at the end of line 80
# 3. Run the Figure 2 lines above (lines 7-15)
# 4. To reinclude data from the Candura fragment, delete the inserted text from the respective scripts and rerun the code

