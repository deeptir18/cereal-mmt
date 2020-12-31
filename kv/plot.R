#!/usr/bin/env Rscript
library(ggplot2)
library(plyr)
library(tidyr)
args <- commandArgs(trailingOnly=TRUE)
d <- read.csv(args[1])
WIDTH <- 0.90
summarized <- ddply(d, c("system", "workload", "num_clients"),
                    summarise,
                    mtput = mean(tput),
                    mavg = mean(avg),
                    mp99 = mean(p99),
                    avgmedian = mean(median))
gathered <- gather(summarized, key="latency", value = "mmt", -system, -workload, -num_clients, -mtput)
base_plot <- function(data) {
    plot <- ggplot(data,
                   aes(x = mtput,
                       y = mmt,
                       color = system)) +
            geom_line() +
            labs(x = "Throughput (Requests/ms)", y = "Latency (microseconds)") +
            theme_light() +
            theme(legend.position = "top")
    return(plot)
}
workload_plot <- function(data) {
    plot <- base_plot(data)
    plot <- plot + 
            facet_grid(workload ~ latency)
    print(plot)
    return(plot)
}

sub <- subset(gathered, gathered$workload != "workloadb")
data_plot <- workload_plot(sub)
ggsave(args[2], width=9, height=6)
