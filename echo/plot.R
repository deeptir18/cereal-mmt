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

specific_plot <- function(data) {
    print(data)
    data <- subset(data, data$latency == args[6])
    plot <- base_plot(data)
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
} else if (args[3] == "full") {
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

} else if (args[3] == "facet") {
    specific_size <- strtoi(args[4])
    specific_message <- args[5]
    specific_subset <- subset(gathered, gathered$size == specific_size)
    #specific_subset <- subset(specific_subset, specific_subset$message == specific_message)
    data_plot <- specific_plot(specific_subset)

}
ggsave(args[2], width=9, height=6)
