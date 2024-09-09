"""
@author: Luuk Kablan
@description: This file contains the collection class that is used to collect the data from the API.
@date: 31-7-2024
"""
import jsonlines
import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv


class Collector:
    """
    This class is used to collect the data from the Meta API.
    """

    def __init__(self):
        self.ad_library_url = 'https://graph.facebook.com/v20.0/ads_archive'
        self.state_file = 'state.json'
        self.output_dir = 'out'
        self.state = {}
        self.limit = -1

    def load_state(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        # Load state from json file
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                self.state = json.load(f)
        else:
            self.state = {'after': None}

    def load_params(self):
        self.limit = os.getenv('LIMIT') or -1
        params = {
            'access_token': self.get_token(),
            'ad_reached_countries': 'US,CA,GB,AU,NZ,DE,FR,IT,ES,NL,SE,NO,DK,FI,IE,BE,AT,CH,PL,CZ,PT,GR,HU,RO,BG,SI,HR,SK,LV,LT,EE,IS,MT,CY,RU,CN,JP,KR,IN,ID,MY,TH,SG,PH,VN,HK,TW,BR,MX,AR,CL,CO,PE,VE,UY,BO,PY,EC,ZA,EG,NG,KE,MA,DZ,TN,GH,CI,AE,SA,QA,KW,OM,BH,IL,TR',
            'ad_type': 'ALL',
            'search_terms': ('cryptocurrency,bitcoin,giveaway')
        }
        if self.state['after']:
            params['after'] = self.state['after']
        return params

    def get_token(self):
        """
        This method uses the app secret and app id to get an access token from the API.
        :return: The access token.
        """
        # Load environment variables
        load_dotenv()
        if os.getenv('ACCESS_TOKEN'):
            return os.getenv('ACCESS_TOKEN')
        # It appears that below method is not working anymore. It is better to use the access token from the .env file.
        app_id = os.getenv('APP_ID')
        app_secret = os.getenv('APP_SECRET')
        url = f'https://graph.facebook.com/oauth/access_token?client_id={app_id}&client_secret={app_secret}&grant_type=client_credentials'
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            print(f'Access token received successfully from {response.url}')
            return data['access_token']
        except requests.exceptions.HTTPError as http_err:
            print(f'1. HTTP error occurred: {http_err} \n Stopping the collection process..')

    def collect(self):
        """
        This method sends requests to the API and collects the data in a JSON file in the output directory.
        :return: The collected ads.
        """
        self.load_state()  # Load the state
        params = self.load_params()  # Load the parameters
        amount = 0
        date_str = datetime.now().strftime('%Y%m%d')
        output_file = os.path.join(self.output_dir, f'ads_{date_str}.jsonl')
        with jsonlines.open(output_file, mode='a') as writer:
            while True:
                if 0 < self.limit <= amount:
                    print(f'Limit of {self.limit} ads reached. Stopping the collection process..')
                    break
                try:
                    response = requests.get(self.ad_library_url, params=params)
                    if amount % 100 == 0:
                        print(f'Collected {amount} ads from {response.url}')
                    response.raise_for_status()
                    data = response.json()
                    if 'data' in data:
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        for ad in data['data']:
                            ad['timestamp'] = timestamp
                            writer.write(ad)
                    if 'paging' in data and 'next' in data['paging']:
                        params['after'] = data['paging']['cursors']['after']
                        self.state['after'] = params['after']
                        with open(self.state_file, 'w') as f:
                            json.dump(self.state, f)
                    else:
                        break
                    amount += 1
                except requests.exceptions.HTTPError as http_err:
                    print(f'2. HTTP error occurred: {http_err} \n Stopping the collection process..')
                    break
                except Exception as err:
                    print(f'3. Other error occurred: {err} \n Stopping the collection process..')
                    break
        return output_file

