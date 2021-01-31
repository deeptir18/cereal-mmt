#!/usr/bin/env Rscript

library(ggplot2)
library(plyr)
library(tidyr)
library(extrafont)
library(ggforce)
library(showtext)
font_add_google("Fira Sans")
showtext_auto()
labels <- c("protobuf" = "Protobuf", "protobytes" ="Protobytes", "capnproto" = "Capnproto", "flatbuffers" = "Flatbuffers", "baseline" = "No Serialization", "baseline_zero_copy" = "Optimal")

args <- commandArgs(trailingOnly=TRUE)
d <- read.csv(args[1])
#d <- subset(d, d$num_clients <= 10)
#d <- subset(d, d$num_clients != 8)
d <- subset(d, d$num_clients != 12 & d$num_clients != 14)
WIDTH <- 0.90
d$system <- factor(d$system, levels = c('protobuf', 'protobytes', 'capnproto', 'flatbuffers', 'baseline', 'baseline_zero_copy'))
shape_values <- c('protobuf' = 7, 'protobytes' = 4, 'capnproto' = 18, 'flatbuffers' = 17, 'baseline' = 15, 'baseline_zero_copy' = 16)
summarized <- ddply(d, c("system", "size", "message", "num_clients"),
                    summarise,
                    mtput = median(tput),
                    mavg = median(avg),
                    mp99 = median(p99),
                    avgmedian = median(median))
gathered <- gather(summarized, key="latency", value = "mmt", -system, -size, -message, -num_clients, -mtput)
base_plot <- function(data) {
    data$ymin <- data$mmt - data$mp99_sd
    data$ymax <- data$mmt - data$mp99_sd

    plot <- ggplot(data,
                   aes(x = mtput,
                       y = mmt,
                       color = system,
                       # fill = system,
                       shape = system,
                       # xmin = mtput - mtput_sd,
                       # xmax = mtput - mtput_sd,
                       ymin = ymin,
                       ymax = ymax)) +
            expand_limits(x = 0, y = 0) +
            geom_point(size=4) +
            #geom_ribbon(alpha = 0.3) +
            geom_line(size = 1, aes(color=system)) +
            labs(x = "Throughput (Requests/ms)", y = "Latency (µs)") +
            scale_shape_manual(values = shape_values, labels = labels) +
            scale_color_brewer(direction = -1, palette = 2, type = "qual",labels = labels) +
            theme_light() +
            theme(legend.position = "top",
                  text = element_text(family="Fira Sans"),
                  legend.title = element_blank(),
                  legend.key.size = unit(10, 'mm'),
                  legend.spacing.x = unit(0.1, 'cm'))
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
    y_label = "Avg Latency (µs)"
    if (args[6] == "avgmedian") {
        y_label = "Median Latency (µs)"
    } else if (args[6] == "mp99") {
        y_label = "p99 Latency (µs)"
    }
    data <- subset(data, data$latency == args[6])
    plot <- base_plot(data) +
            labs(x = "Throughput (Gbps)", y = y_label) +
            theme(legend.position = "top",
                  legend.text=element_text(size=20),
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
                    mtput = median(tputgbps),
                    mavg = median(avg),
                    mp99 = median(p99),
                    avgmedian = median(median))
    g <- gather(summary, key="latency", value = "mmt", -system, -message, -size, - num_clients, -mtput)
    data_plot <- full_plot(g)

} else if (args[3] == "facet") {
    specific_size <- strtoi(args[4])
    summary <- ddply(d, c("system", "num_clients", "size",  "message"),
                    summarise,
                    mtput = mean(tputgbps),
                    mavg = mean(avg),
                    mp99 = mean(p99),
                    mtput_sd = sd(tputgbps),
                    mp99_sd = sd(p99),
                    avgmedian = mean(median))
    g <- gather(summary, key="latency", value = "mmt", -system, -message, -size, - num_clients, -mtput, -mtput_sd, -mp99_sd)
    print(summary)
    specific_subset <- subset(g, g$size == specific_size)
    specific_plot(specific_subset)


}
ggsave("tmp.pdf", width=9, height=6)
embed_fonts("tmp.pdf", outfile=args[2])
