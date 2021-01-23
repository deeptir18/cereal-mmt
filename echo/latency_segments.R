#!/usr/bin/env Rscript

library(ggplot2)
library(plyr)
library(tidyr)
library(extrafont)
library(showtext)
font_add_google("Fira Sans")
showtext_auto()

# args[1] = data; args[2] = pdf; args[3] = num_clients

args <- commandArgs(trailingOnly = TRUE)
d <- read.csv(args[1])
d <- subset(d, d$num_clients == args[3])
d <- subset(d, d$size != 4096)

summarized <- ddply(d, c("system", "size", "message", "num_clients", "segments"),
                    summarise,
                    mtput = mean(tputgbps),
                    mavg = mean(avg),
                    mp99 = mean(p99),
                    avgmedian = mean(median))

ggplot(summarized,
       aes(x = segments,
           y = mp99,
           color = size,
           shape = size)) +
            geom_line(size = 0.75) +
            geom_point(size = 2) +
            labs(x = "Number of segments", y = "p99 latency") +
            theme_light() +
            theme(legend.position = "top",
                  text = element_text(family="Fira Sans"),
                  legend.title = element_blank(),
                  legend.text=element_text(size=17),
                  axis.title=element_text(size=27,face="plain", colour="#000000"),
                  axis.text=element_text(size=27, colour="#000000"))

ggsave("tmp.pdf", width=9, height=6)
embed_fonts("tmp.pdf", outfile=args[2])

