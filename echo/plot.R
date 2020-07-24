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
                    mavg = mean(avg),
                    mp99 = mean(p99),
                    avgmedian = mean(median))
gathered <- gather(summarized, key="latency", value = "mmt", -system, -size, -message, -num_clients, -mtput)
base_plot <- function(data) {
    plot <- ggplot(data,
                   aes(x = mtput,
                       y = mmt,
                       color = system)) +
            geom_line() +
            #geom_point(size=.5) +
            labs(x = "Throughput (Requests/ms)", y = "Latency (microseconds)") +
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
            facet_grid(message ~ latency, scales="free_y")
    print(plot)
    return(plot)
}

full_plot <- function(data) {
    plot <- base_plot(data)
    plot <- plot +
        labs(x = "Throughput (Gbps)", y = "Latency (microseconds)") +
        facet_grid(size ~ latency)
    print(plot)
    return(plot)
}



if (args[3] == "size") {
    size_subset <- subset(gathered, gathered$size != 4096)
    data_plot <- size_plot(size_subset)
} else if (args[3] == "depth") {
    depth_subset <- subset(gathered, gathered$system != "baseline")
    depth_subset <- subset(depth_subset, depth_subset$size == 4096)
    data_plot <- depth_plot(depth_subset)
} else {
    # full graph
    sub <- subset(d, d$size != 4096)
    summary <- ddply(sub, c("system", "num_clients", "size",  "message"),
                    summarise,
                    mtput = mean(tputgbps),
                    mavg = mean(avg),
                    maxp99 = mean(p99),
                    avgmedian = mean(median))
    g <- gather(summary, key="latency", value = "mmt", -system, -message, -size, - num_clients, -mtput)
    data_plot <- full_plot(g)

}
ggsave(args[2], width=9, height=6)
