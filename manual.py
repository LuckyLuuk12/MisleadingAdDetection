import datetime
import json
import os
import webbrowser
import random
from collections import defaultdict

from ai import AIToolBox
from tqdm import tqdm

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

class Inspector:
    """
    This class offers a manual labeling tool to inspect the ads and label them as scams or not scams.
    And it also provides statistics about the data which is available after the manual labeling.
    """
    def __init__(self, path='output/filtered.json', sample_path='output/samples.json'):
        self.data = []
        self.samples = []
        self.unique_data = []
        self.labeled_unique_data = []
        if os.path.exists(path):
            with open(path, 'r') as f:
                self.data = json.load(f)['data']
        if os.path.exists(sample_path):
            self.samples = json.load(open(sample_path, 'r'))['data']
        if os.path.exists('output/filtered-unique.json'):
            self.unique_data = json.load(open('output/filtered-unique.json', 'r'))['data']
        body_set = set()
        if not os.path.exists('output/filtered-unique.json'):
            for ad in self.data:
                b = ad.get('ad_creative_bodies', [None])[0]
                if b not in body_set:
                    self.unique_data.append(ad)
                    body_set.add(b)
            with open('output/filtered-unique.json', 'w') as f:
                json.dump({"data": self.unique_data}, f, indent=4)
        self.unique_data = [ad for ad in self.unique_data if ad['id'] not in [s['id'] for s in self.samples]]
        self.labeled_unique_data = [ad for ad in self.unique_data if 'manual_label' in ad]

    def inspect(self):
        """
        Opens the manual labeling tool to inspect the ads and label them.
        """
        start_time = datetime.datetime.now()
        print(f'[{start_time.strftime("%H:%M")}] » Opening the manual labeling tool...')
        self.samples = self.get_samples() if not self.samples else self.samples
        for i, ad in enumerate(self.samples):
            if 'manual_label' in ad and 'scam' in ad['manual_label']:
                continue
            self.open_ad_in_browser(ad, i, len(self.samples))
            ad['manual_label'] = {
                'scam': input(f'[{datetime.datetime.now().strftime("%H:%M")}] » Is ad {i + 1} a scam? (y/n): ').lower() == 'y'
            }
            with open('output/samples.json', 'w') as f:
                json.dump({"data": self.samples}, f, indent=4)
        self.print_stats()

    def get_samples(self, n=100, amount_with_transcription=50):
        """
        Returns a sample of n random ads or the data in output/samples.json if it exists.
        :param n: The number of ads to return.
        :param amount_with_transcription: The number of ads with video transcription to include in the sample.
        :return: A list of n ads.
        """
        if os.path.exists('output/samples.json'):
            with open('output/samples.json', 'r') as f:
                return json.load(f)['data']
        result = []
        print(f'[{datetime.datetime.now().strftime("%H:%M")}] » Sampling {n} random ads...')
        ads_with_transcription = [ad for ad in self.data if 'video_transcription' in ad]
        ads_without = [ad for ad in self.data if 'video_transcription' not in ad]
        dup_check = set() # To avoid duplicates using the first element of the ad body
        # first gather ads with video transcription
        max_amount = len(ads_with_transcription) if len(ads_with_transcription) < amount_with_transcription else amount_with_transcription
        for i in range(max_amount):
            r = random.randint(0, len(ads_with_transcription) - 1)
            body = ads_with_transcription[r]['ad_creative_bodies'][0] if 'ad_creative_bodies' in ads_with_transcription[r] else None
            if body and body not in dup_check:
                result.append(ads_with_transcription[r])
                dup_check.add(ads_with_transcription[r]['ad_creative_bodies'][0])
        count = 0 # To avoid infinite loop
        while len(result) < n and len(result) < len(self.data) and count < len(ads_without)*len(ads_without):
            count += 1
            i = random.randint(0, len(ads_without)- 1)
            ad = ads_without[i]
            # find at least 40% labeled as scam before adding not-scam ads to sampled data
            if len(result) < n * 0.4 and not self.get_label(ad, False):
                continue
            body = ad['ad_creative_bodies'][0] if 'ad_creative_bodies' in ad else None
            if body and body not in dup_check:
                result.append(ad)
                dup_check.add(ad['ad_creative_bodies'][0])
        print(f'{datetime.datetime.now().strftime("%H:%M")} » Sampled {len(result)} unique ads.')
        with open('output/samples.json', 'w') as f:
            json.dump({"data": result}, f, indent=4)
        return result

    def print_stats(self):
        """
        Prints the statistics of the data.
        """
        start_time = datetime.datetime.now()
        print(f'''[{start_time.strftime("%H:%M")}] » Filtered data statistics:
            - #ads:                    {len(self.data)}
            - #ads from 'airdrop':     {len([ad for ad in self.data if 'airdrop' in ad['search_term']])}
            - #ads from 'bitcoin':     {len([ad for ad in self.data if 'bitcoin' in ad['search_term']])}
            - #ads from 'crypto':      {len([ad for ad in self.data if 'crypto' in ad['search_term']])}
            - #ads from 'elon':        {len([ad for ad in self.data if 'elon' in ad['search_term']])}
            - #ads from 'ethereum':    {len([ad for ad in self.data if 'ethereum' in ad['search_term']])}
            - #ads from 'giveaway':    {len([ad for ad in self.data if 'giveaway' in ad['search_term']])}
            - #ads from 'invest':      {len([ad for ad in self.data if 'invest' in ad['search_term']])}
            - #ads from 'musk':        {len([ad for ad in self.data if 'musk' in ad['search_term']])}
            - #ads from 'profit':      {len([ad for ad in self.data if 'profit' in ad['search_term']])}
            - #ads from 'scam':        {len([ad for ad in self.data if 'scam' in ad['search_term']])}
            - #ads with about crypto:  {len([ad for ad in self.data if ad['classification'].get('about_crypto', False)])}
            - #ads with free crypto:   {len([ad for ad in self.data if ad['classification'].get('free_crypto', False)])}
            - #ads with giveaway:      {len([ad for ad in self.data if ad['classification'].get('giveaway', False)])}
            - #ads with bio link:      {len([ad for ad in self.data if ad['classification'].get('bio_link', False)])}
            - #ads with limited time:  {len([ad for ad in self.data if ad['classification'].get('limited_time', False)])}
            - #ads with unrealistic:   {len([ad for ad in self.data if ad['classification'].get('unrealistic', False)])}
            - #ads Scam by AI:         {len([ad for ad in self.data if self.get_label(ad, False)])}
            - #ads Not-Scam by AI:     {len([ad for ad in self.data if not self.get_label(ad, False)])}
            
            Sample statistics:
            - #ads from 'airdrop':     {len([ad for ad in self.samples if 'airdrop' in ad['search_term']])}
            - #ads from 'bitcoin':     {len([ad for ad in self.samples if 'bitcoin' in ad['search_term']])}
            - #ads from 'crypto':      {len([ad for ad in self.samples if 'crypto' in ad['search_term']])}
            - #ads from 'elon':        {len([ad for ad in self.samples if 'elon' in ad['search_term']])}
            - #ads from 'ethereum':    {len([ad for ad in self.samples if 'ethereum' in ad['search_term']])}
            - #ads from 'giveaway':    {len([ad for ad in self.samples if 'giveaway' in ad['search_term']])}
            - #ads from 'invest':      {len([ad for ad in self.samples if 'invest' in ad['search_term']])}
            - #ads from 'musk':        {len([ad for ad in self.samples if 'musk' in ad['search_term']])}
            - #ads from 'profit':      {len([ad for ad in self.samples if 'profit' in ad['search_term']])}
            - #ads from 'scam':        {len([ad for ad in self.samples if 'scam' in ad['search_term']])}
            - #ads Scam by manual:     {len([ad for ad in self.samples if self.get_label(ad, True)])}
            - #ads Not-Scam by manual: {len([ad for ad in self.samples if not self.get_label(ad, True)])}
            - #ads Scam by AI:         {len([ad for ad in self.samples if self.get_label(ad, False)])}
            - #ads Not-Scam by AI:     {len([ad for ad in self.samples if not self.get_label(ad, False)])}
            - #ads unique (u-ads):     {len(set([ad.get('ad_creative_bodies', [None])[0] for ad in self.samples]))}
            - #ads transcribed:        {len([ad for ad in self.samples if 'video_transcription' in ad])}
            - #unique page names:      {len(set([ad.get('page_name', None) for ad in self.samples]))}
            - True positives:          {self.get_scores()[0]}
            - False positives:         {self.get_scores()[1]}
            - False negatives:         {self.get_scores()[2]}
            - True negatives:          {self.get_scores()[3]}
            - F1 score:                {self.get_scores()[4]}
            - Precision:               {self.get_scores()[5]}
            - Recall:                  {self.get_scores()[6]}
            - Accuracy:                {self.get_scores()[7]}
            - Specificity:             {self.get_scores()[8]}
            - NPV:                     {self.get_scores()[9]}
            - MCC:                     {self.get_scores()[10]}
            - Balanced accuracy:       {self.get_scores()[11]}
            - F2 score:                {self.get_scores()[12]}
            - G-mean:                  {self.get_scores()[13]}
            Confusion matrix (of the samples):
                  AI
            Manual   True  False
               True    {self.get_scores()[0]}     {self.get_scores()[2]}
               False   {self.get_scores()[1]}     {self.get_scores()[3]}
               
             "Very likely" statistics:
            - #ads Scam by AI:         {self.get_scores(True)[0]+self.get_scores(True)[2]}
            - #ads Not-Scam by AI:     {self.get_scores(True)[1]+self.get_scores(True)[3]}
            - True positives:          {self.get_scores(True)[0]}
            - False positives:         {self.get_scores(True)[1]}
            - False negatives:         {self.get_scores(True)[2]}
            - True negatives:          {self.get_scores(True)[3]}
            - F1 score:                {self.get_scores(True)[4]}
            - Precision:               {self.get_scores(True)[5]}
            - Recall:                  {self.get_scores(True)[6]}
            - Accuracy:                {self.get_scores(True)[7]}
            - Specificity:             {self.get_scores(True)[8]}
            - NPV:                     {self.get_scores(True)[9]}
            - MCC:                     {self.get_scores(True)[10]}
            - Balanced accuracy:       {self.get_scores(True)[11]}
            - F2 score:                {self.get_scores(True)[12]}
            - G-mean:                  {self.get_scores(True)[13]}
            Confusion matrix (of the samples):
                  AI
            Manual   True  False
               True    {self.get_scores(True)[0]}     {self.get_scores(True)[2]}
               False   {self.get_scores(True)[1]}     {self.get_scores(True)[3]}
            
            Filtered Unique data statistics:
            - #ads unique (u-ads):     {len(self.unique_data)} / {len(self.data)}
            - #ads with about crypto:  {len([ad for ad in self.unique_data if ad['classification'].get('about_crypto', False)])}
            - #ads with free crypto:   {len([ad for ad in self.unique_data if ad['classification'].get('free_crypto', False)])}
            - #ads with giveaway:      {len([ad for ad in self.unique_data if ad['classification'].get('giveaway', False)])}
            - #ads with bio link:      {len([ad for ad in self.unique_data if ad['classification'].get('bio_link', False)])}
            - #ads with limited time:  {len([ad for ad in self.unique_data if ad['classification'].get('limited_time', False)])}
            - #ads with unrealistic:   {len([ad for ad in self.unique_data if ad['classification'].get('unrealistic', False)])}
            - #ads Scam by AI:         {len([ad for ad in self.unique_data if self.get_label(ad, False)])}
            - #ads Not-Scam by AI:     {len([ad for ad in self.unique_data if not self.get_label(ad, False)])}
            - #ads transcribed:        {len([ad for ad in self.unique_data if 'video_transcription' in ad])}
            - #unique page names:      {len(set([ad.get('page_name', None) for ad in self.unique_data]))}
            - #ads without body:       {len([ad for ad in self.unique_data if not ad.get('ad_creative_bodies', [None])[0]])}
            - #ads labeled:            {len(self.labeled_unique_data)} / {len(self.unique_data)}
            - #ads Scam by manual:     {len([ad for ad in self.labeled_unique_data if self.get_label(ad, True)])}
            - #ads Not-Scam by manual: {len([ad for ad in self.labeled_unique_data if not self.get_label(ad, True)])}
            - True positives:          {len([ad for ad in self.labeled_unique_data if self.get_label(ad, True) and self.get_label(ad, False)])}
            - False positives:         {len([ad for ad in self.labeled_unique_data if not self.get_label(ad, True) and self.get_label(ad, False)])}
            - False negatives:         {len([ad for ad in self.labeled_unique_data if self.get_label(ad, True) and not self.get_label(ad, False)])}
            - True negatives:          {len([ad for ad in self.labeled_unique_data if not self.get_label(ad, True) and not self.get_label(ad, False)])}
            ''')
        self.generate_graphs()

    def get_scores(self, very_likely=False):
        """
        Calculates the F1 score of the manual and AI labels.
        :param very_likely: Whether to calculate the scores for the "very likely" ads.
            Meaning that an ad is considered labeled a scam by AI if the confidence is "Very likely" and the label is True.
            If labeled as true and the confidence is not "Very likely", it is considered labeled as not a scam.
        :return: Tuple of (tp, fp, fn, tn, f1, precision, recall, accuracy)
        """
        self.samples = self.get_samples() # update the samples, just in case
        manual_labels = [self.get_label(ad, True) for ad in self.samples]
        ai_labels = [self.get_label(ad, False) and ad['classification']['confidence'] == 'Very likely' for ad in self.samples] \
            if very_likely else  [self.get_label(ad, False) for ad in self.samples]
        tp = sum([1 for i in range(len(manual_labels)) if     manual_labels[i] and ai_labels[i]])
        fp = sum([1 for i in range(len(manual_labels)) if not manual_labels[i] and ai_labels[i]])
        fn = sum([1 for i in range(len(manual_labels)) if     manual_labels[i] and not ai_labels[i]])
        tn = sum([1 for i in range(len(manual_labels)) if not manual_labels[i] and not ai_labels[i]])
        precision = tp / (tp + fp) if tp + fp != 0 else 'NaN'
        recall = tp / (tp + fn) if tp + fn != 0 else 'NaN'
        f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn != 0 else 'NaN'
        accuracy = (tp + tn) / (tp + tn + fp + fn) if tp + tn + fp + fn != 0 else 'NaN'
        specificity = tn / (tn + fp) if tn + fp != 0 else 'NaN'
        npv = tn / (tn + fn) if tn + fn != 0 else 'NaN'
        mcc = ((tp * tn) - (fp * fn)) / ((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))**0.5 if (tp + fp) * (tp + fn) * (tn + fp) * (tn + fn) != 0 else 'NaN'
        balanced_accuracy = (recall + specificity) / 2 if recall != 'NaN' and specificity != 'NaN' else 'NaN'
        f2 = 5 * precision * recall / (4 * precision + recall) if precision != 'NaN' and recall != 'NaN' else 'NaN'
        g_mean = (recall * specificity)**0.5 if recall != 'NaN' and specificity != 'NaN' else 'NaN'

        return tp, fp, fn, tn, f1, precision, recall, accuracy, specificity, npv, mcc, balanced_accuracy, f2, g_mean


    def create_html(self, ad, index, total):
        title = "\n\t\t".join(ad['ad_creative_link_titles']) if 'ad_creative_link_titles' in ad else ''
        desc = "<br>".join(ad['ad_creative_link_descriptions']) if 'ad_creative_link_descriptions' in ad else ''
        bodies = "<br>".join(ad['ad_creative_bodies']) if 'ad_creative_bodies' in ad else ''
        transcript = f"{ad['video_transcription']}" if 'video_transcription' in ad else ''
        page_url = (f'https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL'
                    f'&media_type=all&search_type=page&view_all_page_id={ad["page_id"]}') if 'page_id' in ad else ''
        url = f'https://www.facebook.com/ads/library/?id={ad["id"]}' if 'id' in ad else ''
        ad_urls = '<br>'.join([f'<a href="{url}" target="_blank">Ad {i + 1}</a>' for i, url in enumerate(ad['ad_creative_link_captions'])]) \
            if 'ad_creative_link_captions' in ad else ''
        html_content = f"""
        	<!DOCTYPE html>
          <html>
            <head>
              <title> Ad {index+1} / {total}</title>
              <style>
                * {{
                  background-color: #0f0f0f;
                  color: #808080;
                  font-size: 1.15rem;
                  border-radius: 1rem;
                  padding: 0 1rem;
                }}
                .ad {{
                  display: grid;
                  grid-template-columns: repeat(2, 1fr);
                  gap: 1rem;
                }}
                h1, h3, h4 {{
                  background: transparent;
                  text-align: center;
                  color: white;
                }}
                .title, .desc {{
                  grid-column: span 2;
                }}
                .bodies, .transcription {{
                  background: #1a1a1f;
                  color: #8181b1;
                  padding: 1rem;
                }}
                a {{
                  text-align: center;
                  color: #5f4af0;
                  text-decoration: none;
                }}
              </style>
            </head>
            <body>
              <div class='ad'>
                <h1 class='title'>{title} - {ad['id']} - {index+1} / {total}</h1>
                <h3 class='desc'>{desc}<br>{ad['search_term']} </h3>
                <div class='bodies'>
                  <h4>Ad Creative Bodies:</h4>
                  {bodies}
                </div>
                <div class='transcription'>
                  <h4>Video Transcription:</h4>
                  {transcript}
                </div>
                <a href="{page_url}" target="_blank">Page URL</a>
                <a href="{url}" target="_blank">Ad URL</a>
                {ad_urls}
              </div>
            </body>
          </html>
        """
        return html_content

    def open_ad_in_browser(self, ad, index, total):
        html_content = self.create_html(ad, index, total)
        file_path = f'manual/ad_{index + 1}.html'
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        webbrowser.open(f'file://{os.path.realpath(file_path)}')

    def get_label(self, ad, manual):
        """
        Returns the label of an ad.
        :param ad: The ad to get the label from.
        :param manual: Whether to get the manual or AI label.
        :return: True if the ad got labeled as a scam, False otherwise.
        """
        return ad.get('manual_label', {}).get('scam', False) if manual else ad.get('classification', {}).get('scam', False)

    def relabel(self):
        """
        Relabels the ads with AI in the samples.json file.
        """
        start = datetime.datetime.now()
        print(f'[{start.strftime("%H:%M")}] » Relabeling the ads with AI...')
        self.samples = self.get_samples() if not self.samples else self.samples
        ai = AIToolBox()
        for i, ad in enumerate(tqdm(self.samples, desc="Relabeling ads")):
            label = ai.generate_label(ad)
            ad['classification']['scam'] = label.get('scam', False)
            ad['classification']['reason'] = label.get('reason', '')
            ad['classification']['confidence'] = label.get('confidence', '')
        with open('output/samples.json', 'w') as f:
            json.dump({"data": self.samples}, f, indent=4)
        end = datetime.datetime.now()
        print(f'[{end.strftime("%H:%M")}] » Relabeled the ads with AI. {end-start}')

    def generate_graphs(self):
        """
        Generates graphs for the data.
        """
        scams = [ad for ad in self.unique_data if self.get_label(ad, False)]
        graphs = []
        graphs.append(('language_distribution', self.plot_language_distribution(scams)))
        graphs.append(('target_locations', self.plot_target_locations(scams)))
        graphs.append(('excluded_target_locations', self.plot_target_locations(scams, excluded=True)))
        graphs.append(('country_reach_distribution', self.plot_country_reach_distribution(scams)))
        graphs.append(('country_scam_count_distribution', self.plot_country_scam_count_distribution(scams)))
        graphs.append(('search_term_distribution_unique', self.plot_search_term_distribution(unique=True)))
        graphs.append(('search_term_distribution', self.plot_search_term_distribution()))
        graphs.append(('acc_target_ages', self.plot_acc_target_ages(scams)))
        graphs.append(('target_ages', self.plot_target_ages(scams)))
        graphs.append(('target_gender', self.plot_target_gender(scams)))
        graphs.append(('ad_duration', self.plot_ad_duration(scams)))
        # And now we also print it for the ads that only have a manual label:
        labeled_scams = [ad for ad in self.labeled_unique_data if self.get_label(ad, True) and self.get_label(ad, False)]
        graphs.append(('language_distribution_labeled', self.plot_language_distribution(labeled_scams)))
        graphs.append(('target_locations_labeled', self.plot_target_locations(labeled_scams)))
        graphs.append(('excluded_target_locations_labeled', self.plot_target_locations(labeled_scams, excluded=True)))
        graphs.append(('country_reach_distribution_labeled', self.plot_country_reach_distribution(labeled_scams)))
        graphs.append(('country_scam_count_distribution_labeled', self.plot_country_scam_count_distribution(labeled_scams)))
        graphs.append(('search_term_distribution_unique_labeled', self.plot_search_term_distribution(unique=True, only_labeled=True)))
        graphs.append(('acc_target_ages_labeled', self.plot_acc_target_ages(labeled_scams)))
        graphs.append(('target_ages_labeled', self.plot_target_ages(labeled_scams)))
        graphs.append(('target_gender_labeled', self.plot_target_gender(labeled_scams)))
        graphs.append(('ad_duration_labeled', self.plot_ad_duration(labeled_scams)))
        for name, (plt, fig) in graphs:
            fig.savefig(f'output/graphs/{name}.png')
            plt.close(fig)

    def plot_language_distribution(self, scams):
        """
        Plots the distribution of scam ads by language.
        """
        languages = []
        for ad in scams:
            languages += ad.get('languages', [])
        df_languages = pd.DataFrame(languages, columns=['language'])
        language_counts = df_languages['language'].value_counts().reset_index()
        language_counts.columns = ['language', 'count']
        fig = plt.figure(figsize=(10, 6))
        sns.barplot(x='language', y='count', data=language_counts)
        plt.title('Count of Scam Ads by Language - Filtered Unique data')
        plt.xlabel('Language')
        plt.ylabel('Count')
        plt.show()
        return plt, fig

    def plot_target_locations(self, scams, excluded=False):
        """
        Plots the distribution of target locations for scam ads.
        """
        locations = defaultdict(int)
        for ad in scams:
            for loc in ad.get('target_locations', []):
                locations[loc.get("name", "N/A")] += 1 if excluded == loc.get("excluded") else 0
        df_locations = pd.DataFrame(list(locations.items()), columns=['location', 'count'])
        df_locations = df_locations.sort_values(by='count', ascending=False)
        fig = plt.figure(figsize=(20, 12))
        sns.barplot(x='location', y='count', data=df_locations)
        incl = 'Excluded' if excluded else 'Included'
        plt.title(f'Distribution of {incl} Target Locations for Scam Ads - Filtered Unique data')
        plt.xlabel('Location')
        plt.ylabel('Count')
        plt.xticks(rotation=90)
        plt.show()
        return plt, fig

    def plot_country_reach_distribution(self, scams):
        """
        Plots the reach of scam ads by country.
        """
        countries = []
        for ad in scams:
            countries += [(a.get('country'), len(a.get('age_gender_breakdowns', []))) for a in ad.get('age_country_gender_reach_breakdown', [])]
        country_count = defaultdict(int)
        for country, reach in countries:
            country_count[country] += reach
        reach_per_country = list(country_count.items())
        df_country_reach = pd.DataFrame(reach_per_country, columns=['country', 'reach'])
        country_counts = df_country_reach.groupby('country')['reach'].sum().reset_index()
        country_counts.columns = ['country', 'reach']
        country_counts = country_counts.sort_values(by='reach', ascending=False)
        fig = plt.figure(figsize=(10, 6))
        sns.barplot(x='country', y='reach', data=country_counts)
        plt.title('Reach of Scam Ads by Country - Filtered Unique data')
        plt.xlabel('Country')
        plt.ylabel('Reach')
        plt.show()
        return plt, fig

    def plot_country_scam_count_distribution(self, scams):
        """
        Plots the count of scam ads by country.
        """
        countries = []
        for ad in scams:
            countries += [(a.get('country'), len(a.get('age_gender_breakdowns', []))) for a in ad.get('age_country_gender_reach_breakdown', [])]
        scam_count = defaultdict(int)
        for country, _ in countries:
            scam_count[country] += 1
        scam_count_per_country = list(scam_count.items())
        df_country_scam_count = pd.DataFrame(scam_count_per_country, columns=['country', 'scam_count'])
        country_scam_counts = df_country_scam_count.groupby('country')['scam_count'].sum().reset_index()
        country_scam_counts.columns = ['country', 'scam_count']
        country_scam_counts = country_scam_counts.sort_values(by='scam_count', ascending=False)
        fig = plt.figure(figsize=(10, 6))
        sns.barplot(x='country', y='scam_count', data=country_scam_counts)
        plt.title('Count of Scam Ads by Country - Filtered Unique data')
        plt.xlabel('Country')
        plt.ylabel('Scam Count')
        plt.show()
        return plt, fig

    def plot_search_term_distribution(self, unique=False, only_labeled=False):
        """
        Plots the distribution of scam ads by search term.
        """
        data = self.unique_data if unique else self.data
        search_terms = [ad['search_term'] for ad in data if 'search_term' in ad and self.get_label(ad, False)]
        if only_labeled:
            search_terms = [ad['search_term'] for ad in data if 'search_term' in ad and self.get_label(ad, True)]
        # remove ads_ from each search term
        search_terms = [term.replace('ads_', '') for term in search_terms]
        df_search_terms = pd.DataFrame(search_terms, columns=['search_term'])
        search_term_counts = df_search_terms['search_term'].value_counts().reset_index()
        search_term_counts.columns = ['search_term', 'count']
        fig = plt.figure(figsize=(10, 6))
        sns.barplot(x='search_term', y='count', data=search_term_counts)
        plt.title(f'Distribution of Scam Ads by Search Term - {"Filtered Unique" if unique else "Filtered"} data')
        plt.xlabel('Search Term')
        plt.ylabel('Count')
        plt.show()
        return plt, fig

    def plot_acc_target_ages(self, scams):
        """
        Plots the distribution of target ages for scam ads. (Accumulated)
        """
        age_counts = defaultdict(int)
        for adv in scams:
            ages = sorted(map(int, adv.get('target_ages', [])))
            if len(ages) >= 2:
                for age in range(ages[0], ages[1] + 1):
                    age_counts[age] += 1
            elif len(ages) == 1:
                 age_counts[ages[0]] += 1
        # Prepare data for plotting
        df_ages = pd.DataFrame(list(age_counts.items()), columns=['age', 'count']).sort_values(by='age')

        # Ensure all ages from min to max are included
        all_ages = pd.DataFrame({'age': range(df_ages['age'].min(), df_ages['age'].max() + 1)})
        df_ages = all_ages.merge(df_ages, on='age', how='left').fillna(0)

        # Plot the data
        fig = plt.figure(figsize=(10, 6))
        sns.lineplot(x='age', y='count', data=df_ages, marker='o')
        plt.title('Distribution of Target Ages for Scam Ads')
        plt.xlabel('Age')
        plt.ylabel('Count')
        plt.show()
        return plt, fig

    def plot_target_ages(self, scams):
        """
        Plots a bar graph per age range string key
        :param scams:  list of scam ads
        :return:
        """
        age_dict = defaultdict(int)
        for ad in scams:
            keys = ad.get('target_ages', [])
            key = '-'.join(keys) if len(keys) > 1 else keys[0] if len(keys) == 1 else 'N/A'
            age_dict[key] = age_dict.get(key, 0) + 1
        df_ages = pd.DataFrame(list(age_dict.items()), columns=['age', 'count'])
        df_ages = df_ages.sort_values(by='count', ascending=False)
        fig = plt.figure(figsize=(10, 6))
        ax = sns.barplot(x='age', y='count', data=df_ages)
        plt.title('Distribution of Target Age ranges for Scam Ads - Filtered Unique data')
        plt.xlabel('Age')
        plt.xticks(rotation=90)
        plt.ylabel('Count')
        # Add the exact number on top of each bar
        for p in ax.patches:
            ax.annotate(f'{int(p.get_height())}', (p.get_x() + p.get_width() / 2., p.get_height()),
                        ha='center', va='center', xytext=(0, 10), textcoords='offset points', rotation=90)
        plt.show()
        return plt, fig

    def plot_target_gender(self, scams):
        """
        Plots the distribution of target gender for scam ads.
        """
        genders = [ad.get('target_gender', 'Unknown') for ad in scams]
        df_genders = pd.DataFrame(genders, columns=['gender'])
        gender_counts = df_genders['gender'].value_counts().reset_index()
        gender_counts.columns = ['gender', 'count']
        fig = plt.figure(figsize=(10, 6))
        plt.pie(gender_counts['count'], labels=gender_counts['gender'], autopct='%1.1f%%', startangle=140)
        plt.title('Distribution of Target Gender for Scam Ads - Filtered Unique data')
        plt.show()
        return plt, fig

    def plot_ad_duration(self, scams):
        """
        Plots the distribution of ad durations grouped into specified categories.
        """
        durations = []
        for ad in scams:
            if 'ad_delivery_start_time' in ad:
                start_time = datetime.datetime.strptime(ad['ad_delivery_start_time'], '%Y-%m-%d')
                if 'ad_delivery_stop_time' in ad:
                    stop_time = datetime.datetime.strptime(ad['ad_delivery_stop_time'], '%Y-%m-%d')
                    duration = (stop_time - start_time).days
                else:
                    duration = 1826 # more than 5 years for unending ads
                durations.append(duration)

        # Define the duration categories
        categories = {
            '< 1 week': 7,
            '< 2 weeks': 14,
            '< 1 month': 30,
            '< 1 quarter': 90,
            '< 1 half': 180,
            '< 1 year': 365,
            '< 2 years': 730,
            '< 5 years': 1825,
            'infinite': float('inf')
        }

        # Group durations into categories
        duration_counts = {category: 0 for category in categories}
        for duration in durations:
            for category, max_days in categories.items():
                if duration < max_days:
                    duration_counts[category] += 1
                    break

        # Prepare data for plotting
        df_duration = pd.DataFrame(list(duration_counts.items()), columns=['Duration', 'Count'])

        # Plot the data
        fig = plt.figure(figsize=(10, 6))
        ax = sns.barplot(x='Duration', y='Count', data=df_duration)
        plt.title('Ad Duration Distribution for Scam Ads - Filtered Unique data')
        plt.xlabel('Duration')
        plt.ylabel('Count')

        # Add the exact number on top of each bar
        for p in ax.patches:
            ax.annotate(f'{int(p.get_height())}', (p.get_x() + p.get_width() / 2., p.get_height()),
                        ha='center', va='center', xytext=(0, 10), textcoords='offset points')

        plt.show()
        return plt, fig


