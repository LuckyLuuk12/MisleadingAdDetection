# MAD - Misleading Ad Detection
#### By Luuk Kablan <br> Radboud University

## Introduction
This repository contains the code for the Misleading Ad Detection (MAD) project. 
The goal of this project is to detect misleading ads on the internet. 
The project is part of my Bachelor Thesis at Radboud University. 
The project is divided into two parts: 
the first part is about collecting data and the second part is about building a model to detect misleading ads.

## Data Collection
The data collection part is done by using the [Meta Ad Library API](https://www.facebook.com/ads/library/api?_rdr) in the [Collector](collect.py) class.
Data gets collected over multiple files using a state to continue where we left of in case we hit the rate limit.
The data is stored in CSV files.
As a result, we have a dataset with advertisements from Facebook. 
The dataset contains the following columns: `ad_id`, `ad_creation_time`, `ad_creative_body`, `ad_creative_link_caption`, 
`ad_creative_link_description`, `ad_creative_link_title`, `ad_creative_link_url`, `ad_creative_body`, 
`ad_creative_title`, `ad_creative_type`, `ad_delivery_start_time`, `ad_delivery_stop_time`, `ad_snapshot_url`, 
`currency`, `demographic_distribution`, `funding_entity`, `impressions`, `page_id`, `page_name`, `region_distribution`, 
`spend`, `ad_targeting`.

## Data Analysis
The data analysis part is done by using the [Pandas](https://pandas.pydata.org/) library in the 
[Analyzer](analyze.py) class. 
