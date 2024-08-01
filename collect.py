"""
@author: Luuk Kablan
@description: This file contains the collection class that is used to collect the data from the API.
@date: 31-7-2024
"""
import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd


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
        # Load environment variables
        load_dotenv()
        self.limit = int(os.getenv('LIMIT'))
        params = {
            'access_token': os.getenv('ACCESS_TOKEN'),
            'ad_reached_countries': 'ALL',
            'ad_type': 'ALL'
        }
        if self.state['after']:
            params['after'] = self.state['after']
        return params

    def collect(self):
        """
        This method sends requests to the API and collects the data in a JSON file in the output directory.
        :return: The collected ads.
        """
        self.load_state()  # Load the state
        params = self.load_params()  # Load the parameters
        ads = {}
        amount = 0
        while True:
            # Check if the limit is reached
            if 0 < self.limit <= amount:
                print(f'Limit of {self.limit} ads reached. Stopping the collection process..')
                break
            # Print progress
            if amount % 100 == 0:
                print(f'Collected {amount} ads')
            # Try to handle a request
            try:
                response = requests.get(self.ad_library_url, params=params)
                response.raise_for_status()
                data = response.json()
                # If there is data, label it with a timestamp
                if 'data' in data:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ads[timestamp] = data['data']
                # Handle pagination
                if 'paging' in data and 'next' in data['paging']:
                    params['after'] = data['paging']['cursors']['after']
                    self.state['after'] = params['after']
                    with open(self.state_file, 'w') as f:
                        json.dump(self.state, f)
                else:
                    break
                # Increment the amount of ads loaded
                amount += 1
            # Handle exceptions
            except requests.exceptions.HTTPError as http_err:
                print(f'HTTP error occurred: {http_err} \n Stopping the collection process..')
                break
            except Exception as err:
                print(f'Other error occurred: {err} \n Stopping the collection process..')
                break
        # Save ads to a JSON file
        date_str = datetime.now().strftime('%Y%m%d')
        output_file = os.path.join(self.output_dir, f'ads_{date_str}.csv')
        df = pd.DataFrame(ads)
        df.to_csv(output_file, index=False)
        # Return the ads for optional further processing
        return ads

