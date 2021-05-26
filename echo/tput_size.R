#!/usr/bin/env Rscript

library(ggplot2)
library(plyr)
library(tidyr)
library(extrafont)
library(showtext)
font_add_google("Fira Sans")
showtext_auto()

# args[1] =; data args[2] = pdf; args[3] = num_clients

args <- commandArgs(trailingOnly=TRUE)
d <- read.csv(args[1])
d <- subset(d, d$num_clients == args[3])
labels <- c("baseline" = "Copy-Out", "baseline_zero_copy" = "Zero-Copy")
summarized <- ddply(d, c("system", "size", "message", "num_clients"),
                    summarise,
                    mtput = mean(tputgbps),
                    mavg = mean(avg),
                    mp99 = mean(p99),
                    avgmedian = mean(median))
print(summarized)
ggplot(summarized,
               aes(x = size,
                   y = mtput,
                   color = system,
                   shape = system)) +
            expand_limits(x = 0, y = 0) +
            # geom_line(size = 1) +
            geom_point(size = 3, aes(shape=system)) +
            scale_x_continuous(trans = 'log2', breaks=c(64,128,256,512,1024,2048,4096,8192)) +
            scale_color_brewer(palette = 2, type = "qual", labels = labels) +
            scale_shape_discrete(labels = labels) +
            labs(x = "Request size (bytes)", y = "Achieved Throughput\n(Gbps)") +
            theme_light() +
            theme(legend.position = "top",
                  text = element_text(family="Fira Sans"),
                  legend.title = element_blank(),
                  legend.text=element_text(size=17),
                  axis.title=element_text(size=17,face="plain", colour="#000000"),
                  axis.text=element_text(size=17, colour="#000000"))

ggsave("tmp.pdf", width=6, height=3)
embed_fonts("tmp.pdf", outfile=args[2])

