# MAD - Misleading Ad Detection
#### By Luuk Kablan @ Radboud University
##### Supervised by Dr. M.G.C. Acar

## Introduction
This repository contains the code for the Misleading Ad Detection (MAD) project. 
The goal of this project is to detect misleading ads on the internet. 
The project is part of my Bachelor Thesis at Radboud University. 
The project is divided into two parts: 
the first part is about collecting data and the second part is about building a model to detect misleading ads.

## Written Report
The written report can be found in the root of this repository.
It was written using these `.env` parameters:
```dotenv
ACCESS_TOKEN=<YOUR_ACCESS_TOKEN_HERE>
LIMIT=300
# As we hit the rate limit within approximatly 3 search terms, we need to manually swap the comments below
SEARCH_TERMS=crypto;bitcoin;ethereum;scam
#SEARCH_TERMS=giveaway;profit;invest
#SEARCH_TERMS=airdrop;elon;musk

COUNTRIES=US,CA,GB,AU,NZ,DE,FR,IT,ES,NL,SE,NO,DK,FI,IE,BE,AT,CH,PL,CZ,PT,GR,HU,RO,BG,SI,HR,SK,LV,LT,EE,IS,MT,CY,RU,CN,JP,KR,IN,ID,MY,TH,SG,PH,VN,HK,TW,BR,MX,AR,CL,CO,PE,VE,UY,BO,PY,EC,ZA,EG,NG,KE,MA,DZ,TN,GH,CI,AE,SA,QA,KW,OM,BH,IL,TR
FIELDS=id,ad_creation_time,ad_creative_bodies,ad_creative_link_captions,ad_creative_link_descriptions,ad_creative_link_titles,ad_delivery_start_time,ad_delivery_stop_time,ad_snapshot_url,age_country_gender_reach_breakdown,beneficiary_payers,br_total_reach,bylines,currency,delivery_region,demographic_distribution,estimated_audience_size,eu_total_reach,impressions,languages,page_id,page_name,publisher_platforms,spend,target_ages,target_gender,target_locations
START_DATE=2024-05-01
MAX_OLLAMA_HISTORY=2
TOP_K=1
TOP_P=0.2
TEMPERATURE=0.1
MAX_VIDEO_LENGTH=150
```
