# MAD - Misleading Ad Detection
#### By Luuk Kablan <br> Radboud University

## Introduction
This repository contains the code for the Misleading Ad Detection (MAD) project. 
The goal of this project is to detect misleading ads on the internet. 
The project is part of my Bachelor Thesis at Radboud University. 
The project is divided into two parts: 
the first part is about collecting data and the second part is about building a model to detect misleading ads.

## Data Collection
The data collection part is done by using the [adDownloader API](https://github.com/Paularossi/AdDownloader).
This API is used to download ads from the [Meta Ad Library API](https://www.facebook.com/ads/library/api?_rdr)
in the [Collector](collect.py) class.

## Data Analysis
This code also provides to use the [Analyzer](analyze.py) class to analyze the data. Which internally uses the 
`start_gui` and/or `run_analysis` function from the [adDownloader API](https://github.com/Paularossi/AdDownloader).
