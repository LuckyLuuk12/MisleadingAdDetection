import datetime
import json
import os


class Filter:
    """
    This class filters the ads by keeping only crypto-related ads that contain at least one of the following criteria:
    - free_crypto: True
    - giveaway: True
    This way, we can reduce the number of ads to analyze and focus on the most relevant ones.
    """
    def __init__(self):
        self.keys = ['about_crypto', 'free_crypto', 'giveaway', 'unrealistic', 'bio_link', 'limited_time']
        self.data = []

    def filter(self):
        """
        This method takes all JSON files from the output folder and filters them by only keeping the ads that contain at
        least one of the following criteria, assigned by the Classifier class:
        - about_crypto: True
        - free_crypto: True
        - giveaway: True
        :return:
        """
        start_time = datetime.datetime.now()
        print(f'[{start_time.strftime("%H:%M")}] » Filtering the ads...')
        for term in os.listdir('output'):
            for file in os.listdir(f'output/{term}/json'):
                with open(f'output/{term}/json/{file}', 'r') as f:
                    ads = json.load(f)['data']
                    ads = [ad for ad in ads if self.keep(ad)]
                    for ad in ads:
                        ad['search_term'] = term
                    self.data.extend(ads)
        self.data.sort(key=self.count, reverse=True)
        print(f'» Found {len(self.data)} crypto-related ads.')
        with open('output/filtered.json', 'w') as f:
            json.dump({"data": self.data}, f, indent=4)

    def keep(self, ad):
        """
        This method checks if an ad contains at least one of the criteria in the 'classification' dictionary.
        :param ad: The ad to check.
        :return: True if the about_crypto criterion is True AND either the free_crypto or giveaway criterion is True.
        """
        return ('classification' in ad and ad['classification'].get('about_crypto', False) and
                any(ad['classification'].get(key, False) for key in ['free_crypto', 'giveaway']))

    def count(self, ad):
        """
        This method counts the number of criteria that are True in the 'classification' dictionary.
        :param ad: The ad to count.
        :return: The number of criteria that are True.
        """
        # TODO: We might want to count only the criteria != about_crypto, free_crypto, and giveaway.
        return sum([ad['classification'][key] for key in ad['classification'] if key in self.keys])
