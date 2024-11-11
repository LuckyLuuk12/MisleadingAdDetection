import json
import os
import random

from classifier import Classifier
from sklearn.metrics import confusion_matrix


class Tester:
    def __init__(self):
        self.amount = 300  # the size of the test set
        self.allow_similar = False  # allow bodies and transcripts to be similar to already gathered ones
        self.allow_empty = False  # allow bodies and transcripts to be both empty

    def gather(self, read_from=None):
        """
        This method looks in the output directory and gathers random files up to the amount specified.
        It first randomly selects a search term folder and then a random file from the json folder within it.
        :param read_from: Whether to get already gathered data from a file in labeled folder
        :return: The file name of the gathered data.
        """
        if read_from and os.path.exists(f'labeled/{read_from}') and read_from.endswith('.json'):
            with open(f'labeled/{read_from}', 'r') as f:
                ads = json.load(f)["data"]
                print(f'» Gathered {len(ads)} ads from {read_from}')
                return read_from
        gathered = []
        already_gathered = set()
        self.amount = int(input('» Enter the number of ads to gather: '))
        for i in range(self.amount):
            # Gather a random file
            term = random.choice(os.listdir('output'))
            # Count the number of files in output/{term}/json and pick a random one
            files = os.listdir(f'output/{term}/json')
            file = random.choice(files)

            # Read JSON data and randomly select an ad
            with (open(f'output/{term}/json/{file}', 'r') as f):
                data = json.load(f)["data"]
                ad = random.choice(data)
                # TODO: there is a flaw here because if we don't want empty ads, we might get one by the allow_similar
                # TODO: and the code could also get stuck in an infinite loop if all ads are similar
                # If we don't allow empty ads, check if the body and transcript are not empty
                max_attempts = len(data)
                attempts = 0
                if not self.allow_empty:
                    bodies = ad['ad_creative_bodies'] if 'ad_creative_bodies' in ad else None
                    transcript = ad['video_transcription'] if 'video_transcription' in ad else None
                    while attempts <= max_attempts and not bodies and not transcript:
                        attempts += 1
                        ad = random.choice(data)
                # If we don't allow similar ads,
                # check if bodies and transcripts are not similar to already gathered ones
                if not self.allow_similar:
                    # Convert list of bodies to 1 big string and then do the check
                    if 'ad_creative_bodies' in ad:
                        body = ' '.join(ad['ad_creative_bodies'])
                    while attempts <= max_attempts and 'ad_creative_bodies' in ad and 'video_transcription' in ad and \
                            (body, ad['video_transcription']) in already_gathered:
                        ad = random.choice(data)
                        if 'ad_creative_bodies' in ad:
                            body = ' '.join(ad['ad_creative_bodies'])
                gathered.append(ad)
                body = ' '.join(ad['ad_creative_bodies']) if 'ad_creative_bodies' in ad else None
                transcript = ad['video_transcription'] if 'video_transcription' in ad else None
                already_gathered.add((body, transcript))
        # See if we already have a labeled-{amount}.json file and if not, create one starting from 0
        labeled_files = os.listdir('labeled')
        labeled_files = [f for f in labeled_files if f.startswith('labeled-') and f.endswith('.json')]
        labeled_files.sort()
        if len(labeled_files) == 0 or not read_from:
            labeled_file = 'labeled-0.json'
        else:
            last = labeled_files[-1]
            last = int(last.split('-')[1].split('.')[0])
            labeled_file = f'labeled-{last + 1}.json'
        # Write the gathered data to the labeled file
        with open(f'labeled/{labeled_file}', 'w') as f1:
            json.dump({"data": gathered}, f1, indent=4)
        print(f'» Gathered {len(gathered)} ads from {labeled_file}')
        return labeled_file

    def test(self):
        """
        This method asks the user for a number and uses the gather method on labeled/labeled-{number}.json.
        Note that if the file does not exist, it will gather new data or fall back to labeled-0.json if existing.
        :return:
        """
        number = input('» Enter the number of labeled file to test: ')
        gathered_file = self.gather(f'labeled-{number}.json')
        classifier = Classifier()
        classifier.classify_json(f'labeled/{gathered_file}', True)
        # Now if the ads have a manual label we can compare the results, otherwise we must ask the user to label them
        with (open(f'labeled/{gathered_file}', 'r') as f):
            ads = json.load(f)['data']
            if 'manual_label' in ads[0]:
                #  Compare the 'manual_label' with the ['classification']['label'] and give a confusion matrix
                labels = [ad['manual_label'] for ad in ads]
                predictions = [ad['classification']['classification'] for ad in ads]
                print('» Confusion matrix:')
                cm = confusion_matrix(labels, predictions, labels=['S', 'NS'])
                print(cm)
            else:
                print('» Please label the ads manually before testing them:')
                for i, ad in enumerate(ads):
                    bodies = "\n\t".join(ad['ad_creative_bodies']) if 'ad_creative_bodies' in ad else ''
                    transcript = ad['classification']['video_transcription'] if 'classification' in ad\
                        and 'video_transcription' in ad['classification'] else ''
                    print(f'{i + 1} / {len(ads)}\t-\t{ad["id"]}'
                          f'\n\t{bodies}'
                          f'\n\t{transcript}')
                    label = input('Enter the label (1: "S",\t else: "NS"): ')
                    ad['manual_label'] = 'S' if label == '1' else 'NS'
                with open(f'labeled/{gathered_file}', 'w') as f1:
                    json.dump(ads, f1, indent=4)
