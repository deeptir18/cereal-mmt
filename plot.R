#!/usr/bin/env Rscript

library(ggplot2)
library(plyr)
library(tidyr)
args <- commandArgs(trailingOnly=TRUE)
d <- read.csv(args[1])
WIDTH <- 0.90
summarized <- ddply(d, c("system", "size", "message", "num_clients"),
                    summarise,
                    mtput = mean(tput),
                    maxp99 = max(p99),
                    avgmedian = mean(median))
gathered <- gather(summarized, key="latency", value = "mmt", -system, -size, -message, -num_clients, -mtput)
base_plot <- function(data) {
    plot <- ggplot(data,
                   aes(x = mtput,
                       y = mmt,
                       color = system)) +
            geom_line() +
            labs(x = "Throughput (Requests/ms)", y = "Latency (nanoseconds)") +
            theme_light() +
            theme(legend.position = "top")
    return(plot)
}
size_plot <- function(data) {
    plot <- base_plot(data)
    plot <- plot + 
            facet_grid(size ~ latency)
    print(plot)
    return(plot)
}

depth_plot <- function(data) {
    plot <- base_plot(data)
    print(max(data$latency))
    plot <- plot + 
            facet_grid(message ~ latency)
    print(plot)
    return(plot)
}



if (args[3] == "size") {
    size_subset <- subset(gathered, gathered$size != 4096)
    data_plot <- size_plot(size_subset)
} else {
    depth_subset <- subset(gathered, gathered$system != "baseline")
    depth_subset <- subset(depth_subset, depth_subset$size == 4096)
    data_plot <- depth_plot(depth_subset)
}
ggsave(args[2], width=6, height=6)
