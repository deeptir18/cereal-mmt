#!/usr/bin/env Rscript

library(ggplot2)
library(plyr)
library(tidyr)
library(extrafont)
library(showtext)
font_add_google("Fira Sans")
showtext_auto()

args <- commandArgs(trailingOnly=TRUE)
d <- read.csv(args[1])
d <- subset(d, d$num_clients <= 48)
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
            expand_limits(x = 0, y = 0) +
            geom_line(size=0.5) +
            geom_point(size=1) +
            labs(x = "Throughput (Requests/ms)", y = "Latency (microseconds)") +
            theme_light() +
            theme(legend.position = "top",
                  text = element_text(family="Fira Sans"),
                  legend.title = element_blank())
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
    # print(data)
    y_label = "Avg Latency (microseconds)"
    if (args[6] == "avgmedian") {
        y_label = "Median Latency (microseconds)"
    } else if (args[6] == "mp99") {
        y_label = "P99 Latency (microseconds)"
    }
    data <- subset(data, data$latency == args[6])
    plot <- base_plot(data) +
            labs(x = "Throughput (Gbps)", y = y_label) +
            theme(legend.position = "top",
                  legend.text=element_text(size=17),
                  axis.title=element_text(size=27,face="plain", colour="#000000"),
                  axis.text=element_text(size=27, colour="#000000"))

    print(plot)
    return(plot)
}



if (args[3] == "size") {
    # size_subset <- subset(gathered, gathered$size != 4096)
    data_plot <- size_plot(gathered)
} else if (args[3] == "depth") {
    depth_subset <- subset(gathered, gathered$system != "baseline")
    depth_subset <- subset(depth_subset, depth_subset$size == 4096)
    data_plot <- depth_plot(depth_subset)
} else if (args[3] == "full") {
    # full graph
    summary <- ddply(d, c("system", "num_clients", "size",  "message"),
                    summarise,
                    mtput = mean(tputgbps),
                    mavg = mean(avg),
                    mp99 = mean(p99),
                    avgmedian = mean(median))
    g <- gather(summary, key="latency", value = "mmt", -system, -message, -size, - num_clients, -mtput)
    data_plot <- full_plot(g)

} else if (args[3] == "facet") {
    specific_size <- strtoi(args[4])
    summary <- ddply(d, c("system", "num_clients", "size",  "message"),
                    summarise,
                    mtput = mean(tputgbps),
                    mavg = mean(avg),
                    mp99 = mean(p99),
                    avgmedian = mean(median))
    g <- gather(summary, key="latency", value = "mmt", -system, -message, -size, - num_clients, -mtput)
    specific_subset <- subset(g, g$size == specific_size)
    specific_plot(specific_subset)


}
ggsave("tmp.pdf", width=9, height=6)
embed_fonts("tmp.pdf", outfile=args[2])
