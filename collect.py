"""
@author: Luuk Kablan
@description: This file contains the collection class that is used to collect the data from the API.
@date: 31-7-2024
"""
import datetime

from AdDownloader import adlib_api
from AdDownloader.media_download import start_media_download
import os
from dotenv import load_dotenv
import requests
from tqdm import tqdm

class Collector:
    """
    This class is used to collect the data from the Meta API.
    """

    def __init__(self):
        load_dotenv()
        self.limit = 0 if os.getenv('LIMIT') is None else int(os.getenv('LIMIT'))
        self.countries = 'US' if os.getenv('COUNTRIES') is None else os.getenv('COUNTRIES')
        self.start_date = '2024-05-01' if os.getenv('START_DATE') is None else os.getenv('START_DATE')
        self.search_terms = 'crypto' if os.getenv('SEARCH_TERMS') is None else os.getenv('SEARCH_TERMS')
        self.access_token = None
        self.project_name = 'ads' if os.getenv('PROJECT_NAME') is None else os.getenv('PROJECT_NAME')
        self.fields = os.getenv('FIELDS')
        self.api = None

    def get_token(self):
        """
        This method gets the access token from the .env file.
        It asks the user to enter the token if it is not found or expired.
        :return: The access token.
        """
        # Load environment variables from .env file or ask the user to enter them
        if os.getenv('ACCESS_TOKEN') and not self.is_token_expired(os.getenv('ACCESS_TOKEN')):
            return os.getenv('ACCESS_TOKEN')
        else:
            print('» Get your token from: https://developers.facebook.com/tools/explorer/')
            return input('Enter your access token: ')

    def is_token_expired(self, token=None):
        """
        This method checks if the token is expired.
        :param token: The token to check. Falls back to the default token.
        :return: True if the token is expired, False otherwise.
        """
        if token is None:
            token = self.access_token
        if token is None:
            return True
        # Check if the token is expired
        url = f'https://graph.facebook.com/me?access_token={token}'
        response = requests.get(url)
        # If the status code is 400, the token is expired
        if response.status_code == 400:
            return True
        return False

    def collect(self, project_name=None):
        """
        This method collects the data from the API. It splits the search terms and collects the data for each term.
        :param project_name: The name of the project. If None, the default (.env) project name is used.
                             Falls back to 'ads'.
        :return: The collected ads.
        """
        start_time = datetime.datetime.now()
        print(f'» [{start_time.strftime("%H:%M")}] Starting data collection...')
        # Split the search terms and collect the data for each term
        for term in tqdm(self.search_terms.split(';'), desc='Collecting ads'):
            print(f'» [{datetime.datetime.now().strftime("%H:%M")}] Starting data collection for `{term}`...')
            using_project = self.project_name if project_name is None else project_name
            using_project = f'{using_project}_{term}'
            # If the token is expired, get a new token from the user
            if self.is_token_expired():
                self.access_token = self.get_token()
            self.api = adlib_api.AdLibAPI(self.access_token, project_name=using_project)
            self.api.add_parameters(fields=self.fields,
                                    ad_reached_countries=self.countries,
                                    ad_delivery_date_min=self.start_date,
                                    search_terms=term)
            self.api.get_parameters()
            # Start the download of the data
            data = self.api.start_download()
            if data is None or len(data) == 0:
                print(f'» [{datetime.datetime.now().strftime("%H:%M")}] No data found for `{term}`...')
                continue
            # Start the media download
            print(f'» [{datetime.datetime.now().strftime("%H:%M")}] Starting download for `{term}`... ({len(data)})')
            start_media_download(project_name=using_project, nr_ads=self.limit, data=data)
            print(f'» [{datetime.datetime.now().strftime("%H:%M")}] Finished download for `{term}`!')
        end_time = datetime.datetime.now()
        total_time = (end_time - start_time).seconds / 60
        print(f'\n» [{end_time.strftime("%H:%M")}] Finished data collection! ({total_time:.2f} minutes)')
