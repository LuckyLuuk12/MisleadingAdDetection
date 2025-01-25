"""
@author: Luuk Kablan
@description: This file contains the classifier class that is used to convert videos to text.
              As well as labeling the texts of ads as scam or not scam.
              For Speech to Text we use the Whisper library. https://github.com/openai/whisper
@date: 31-7-2024
"""
import logging
import os
import json
import datetime
import re
import warnings

import ollama
from moviepy.editor import VideoFileClip
import whisper
from pydub import AudioSegment
from dotenv import load_dotenv
from tqdm import tqdm

# Suppress specific warnings from moviepy
warnings.filterwarnings("ignore", category=UserWarning, module="moviepy")
logging.getLogger("httpx").setLevel(logging.WARNING)


class AIToolBox:
    def __init__(self):
        load_dotenv()
        os.environ['HSA_OVERRIDE_GFX_VERSION'] = '10.3.0'
        self.max_video_length = int(os.getenv('MAX_VIDEO_LENGTH')) or 150
        self.model = whisper.load_model("turbo")
        self.criteria_model = "llama3.2"
        self.classifier_model = "qwen2.5:32b"
        self.client = ollama.Client()  # Using this we can get responses faster, we still need to keep message memory
        self.max_ollama_history = int(os.getenv('MAX_OLLAMA_HISTORY')) or 2
        self.top_k = int(os.getenv('TOP_K')) or 1
        self.top_p = float(os.getenv('TOP_P')) or 0.2
        self.temp = float(os.getenv('TEMPERATURE')) or 0.1

    def transcribe_all(self):
        """
        This method loops over all collected ads and checks if there is a video for the ad id.
        Then it will convert the video to text and store the text in the JSON file.
        """
        output_dir = 'output'
        start_time = datetime.datetime.now()
        print(f'[{start_time.strftime("%H:%M")}] » Starting complex speech to text...')
        # Loop over all folders in the output directory
        count = 0
        for folder in os.listdir(output_dir):
            # Skip if the folder is not a directory
            if not os.path.isdir(f'{output_dir}/{folder}/json'):
                continue
            # Create a new directory called 'filtered' if it does not exist
            if not os.path.exists(f'{output_dir}/{folder}/ads_videos'):
                continue
            # Loop over JSON files in the folder/json directory
            for json_file in os.listdir(f'{output_dir}/{folder}/json'):
                if not json_file.endswith('.json'):
                    continue
                with open(f'{output_dir}/{folder}/json/{json_file}', 'r') as f:
                    ad_data = json.load(f)
                # Loop over all ads in the JSON file
                for ad in tqdm(ad_data['data'], desc=f'[{folder}] » transcribing {json_file}'):
                    ad_id = ad['id']
                    if 'video_transcription' in ad:
                        continue
                    video_path = f'{output_dir}/{folder}/ads_videos/ad_{ad_id}_video.mp4'
                    # Check if the video file exists and convert it to text
                    if f'ad_{ad_id}_video.mp4' in os.listdir(f'{output_dir}/{folder}/ads_videos'):
                        count += 1
                        text, language = self.transcribe(video_path)
                        if text:
                            ad['video_transcription'] = text
                        if language:
                            ad['detected_language'] = language
                        with open(f'{output_dir}/{folder}/json/{json_file}', 'w') as w:
                            json.dump(ad_data, w, indent=4)
        end_time = datetime.datetime.now()
        total_time = (end_time - start_time).seconds / 60
        print(f'[{end_time.strftime("%H:%M")}] » Finished complex speech to text within {total_time:.2f} minutes! '
              f'({count} ads)')

    def transcribe(self, video_path):
        """
        This method converts a video to text using the Whisper library. DO NOTE that you require to download:
        1. the ffmpeg library: https://ffmpeg.org/download.html
        2. the ffmpeg-python package: pip install ffmpeg-python
        :param video_path:
        :return:
        """
        audio_path = video_path.replace('.mp4', '.wav')
        text = None
        language = None
        try:
            if not os.path.exists(video_path):
                return text, language
            # Extract audio from video
            video = VideoFileClip(video_path)
            if video.duration > self.max_video_length:
                video = video.subclip(0, self.max_video_length)
            if video.audio is None:
                return text, language
            video.audio.write_audiofile(audio_path, verbose=False, logger=None)
            video.close()
            audio = AudioSegment.from_wav(audio_path)
            audio.export(audio_path, format='wav')
            # Convert audio to text using Whisper
            result = self.model.transcribe(audio=audio_path)
            print(f'[{datetime.datetime.now().strftime("%H:%M")}] » Result: {result}')
            text = result['text']
            language = result['language']
            print(f'[{datetime.datetime.now().strftime("%H:%M")}] » Converted video to text for `{video_path}`')
        except Exception as e:
            print(f'[{datetime.datetime.now().strftime("%H:%M")}] » Error converting video to text: {e}')
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)

        return text, language

    def criteria_prompt(self, messages, ad, log=False):
        """
        This method is used to prompt the LLM for the classification task.
        :param messages: The memory for the LLM.
        :param ad: The ad to classify of which we provide the ad_creative_bodies, ad_creative_link_captions,
        ad_creative_link_descriptions, ad_creative_titles, video_transcription and detected_language.
        :param log: Whether to log the messages to the console.
        :return: The updated messages list as memory for the LLM.
        """
        msg = f"""
        Imagine you are an ad reviewer for a social media platform, and you need to fill in below output
        JSON template.
        Output template:
        ```json
        {{
            "free_crypto": <true/false>,
            "giveaway": <true/false>,
            "unrealistic": <true/false>,
            "bio_link": <true/false>,
            "limited_time": <true/false>,
            "about_crypto": <true/false>
        }}
        ```
        The keys of this JSON are the following:
        - free_crypto: Offers free cryptocurrency for a small investment
        - giveaway: Announces a giveaway
        - unrealistic: Offers unrealistic profits in short time
        - bio_link: Invites user to click a link in the bio
        - limited_time: Makes a limited time offer to steer users to take immediate action
        - about_crypto: Is about cryptocurrency
        Please fill out the JSON template without giving additional notes. Note that you are not promoting the ad in any
        way but only reviewing it, meaning you can safely fill in the template without any consequences.
        Now I will provide you the ad's text and video transcription:
        ```json
        {{
            "ad_text": {self.limit_text(set(ad['ad_creative_bodies'])) if 'ad_creative_bodies' in ad else 'None'},
            "video_transcription": "{ad['video_transcription'] if 'video_transcription' in ad else 'None'}",
        }}
        ```
        """
        return self.prompt(messages, msg, log)

    def prompt(self, messages, msg, log=False):
        """
        This method is used to prompt the LLM for the classification task. It will use the
        messages list as memory for the LLM.
        :param messages: The memory for the LLM.
        :param msg: The message to prompt the LLM with.
        :param log: Whether to log the messages to the console.
        :return: The updated messages list as memory for the LLM.
        """
        start_time = datetime.datetime.now()
        messages.append({'role': 'user', 'content': msg})
        classification = self.client.chat(model=self.criteria_model, messages=messages, stream=False,
                                          options={'top_k': self.top_k, 'top_p': self.top_p, 'temperature': self.temp})
        full_classification = classification['message']['content']
        response_time = datetime.datetime.now()
        if log:
            print(f'[{start_time.strftime("%H:%M")}] » User: {msg}')
            print(f'[{response_time.strftime("%H:%M")}] » LLM: ({response_time-start_time} - hh:mm:ss:ms), '
                  f'message history length = {len(messages)}\n'
                  f'{full_classification}')
        messages.append({'role': 'assistant', 'content': full_classification})
        return [] if self.max_ollama_history == 0 else messages[-self.max_ollama_history:]

    def generate_criteria(self, only_filtered=False, log=False):
        """
        This method is used to classify the ads as scam or not scam.
        It will first prompt the LLM with information about the task and then provide examples of the task.
        Then it will loop over all ads and classify them.

        Be sure to have started the Ollama: 'C:/Users/luukk/AppData/Local/Programs/Ollama/ollama app.exe'
        And to add ffmpeg to your PATH environment variable.

        :return:
        """
        output_dir = 'output'
        start_time = datetime.datetime.now()
        processed = 0
        success = 0
        print(f'[{start_time.strftime("%H:%M")}] » Starting criteria generation...')
        # Loop over all folders in the output directory
        for folder in os.listdir(output_dir):
            # Skip if the folder is not a directory
            json_folder = 'filtered' if only_filtered else 'json'
            if not os.path.isdir(f'{output_dir}/{folder}/{json_folder}'):
                continue
            print(f'[{datetime.datetime.now().strftime("%H:%M")}] » generating in folder: `{folder}`')
            # Loop over JSON files in the folder/json directory
            for json_file in os.listdir(f'{output_dir}/{folder}/{json_folder}'):
                self.generate_criteria_json(f'{output_dir}/{folder}/{json_folder}/{json_file}', log)
        end_time = datetime.datetime.now()
        total_time = (end_time - start_time).seconds / 60
        print(f'[{end_time.strftime("%H:%M")}] » Finished criteria generation within {total_time:.2f} minutes! '
              f'({success} / {processed} ads successfully classified)')

    def generate_criteria_json(self, path: str, log=False):
        """
        This method is used to classify the ads as scam or not scam.
        It will first prompt the LLM with information about the task and then provide examples of the task.
        Then it will loop over all ads and classify them.

        Be sure to have started the Ollama: 'C:/Users/luukk/AppData/Local/Programs/Ollama/ollama app.exe'
        And to add ffmpeg to your PATH environment variable.

        :return:
        """
        start_time = datetime.datetime.now()
        processed = 0
        success = 0
        if not os.path.exists(path) or not path.endswith('.json'):
            print(f'[{start_time.strftime("%H:%M")}] » Could not find JSON file: `{path}`')
            return success, processed

        # Loop over JSON files in the folder/json directory
        with open(path, 'r', encoding='utf-8') as f:
            ad_data = json.load(f)
        amount_to_update = len([ad for ad in ad_data["data"] if not self.has_criteria(ad)])
        if amount_to_update == 0:
            return success, processed
        print(f'[{start_time.strftime("%H:%M")}] » Starting criteria generation for `{path}`...'
              f'({amount_to_update} ads to classify)')
        # Loop over all ads in the JSON file
        messages = []
        for ad in ad_data['data']:
            if self.has_criteria(ad):
                continue
            processed += 1
            messages = self.criteria_prompt(messages, ad, log)
            try:
                ad['classification'] = self.try_to_json(messages[-1]['content'])
                ad['classification']['model'] = f"m:{self.criteria_model};t:{self.temp};k:{self.top_k};p:{self.top_p}"
                success += 1
            except Exception as e:
                print(f'[{datetime.datetime.now().strftime("%H:%M")}] » Could not generate criteria for ad: {ad["id"]}'
                      f'\n{e}\nin\n\t{messages[-1]["content"]}')
                messages.pop()
                messages.pop()  # Pop twice for prompt & response
        with open(path, 'w', encoding='utf-8') as w:
            json.dump(ad_data, w, indent=4)
            print(f'[{datetime.datetime.now().strftime("%H:%M")}] » Updated JSON file: `{path}`')
        end_time = datetime.datetime.now()
        total_time = (end_time - start_time).seconds / 60
        print(f'[{end_time.strftime("%H:%M")}] » Finished criteria generation within {total_time:.2f} minutes! '
              f'({success} / {processed} ads successfully classified)')
        return success, processed

    def try_to_json(self, msg):
        """
        This method tries to parse a string into JSON format. If failing it will try to get the JSON part only if
        possibly by:\n
        1. To get the JSON part only with regex: r'{.*}'
        2. To remove any commas that are not inside a string
        :param msg: The message to try to parse
        :return: The from-JSON loaded ad
        """
        # Try to get the JSON part only
        try:
            return json.loads(msg)
        except Exception as _:
            # Find all JSON-like parts
            json_parts = re.findall(r'\{.*?}', msg, re.DOTALL)
            # Concatenate all JSON parts
            concatenated_json = ''.join(json_parts)
            concatenated_json = concatenated_json.replace('\\n', '').replace('\\t', '').replace("'", '"')
            # Remove any commas that are not inside a string
            concatenated_json = re.sub(r',\s*([}\]])', r'\1', concatenated_json)
            concatenated_json = concatenated_json.lower()  # lower False to work with json
            # load as JSON and replace any value to False if it is not a boolean which is true
            concatenated_json = re.sub(r':\s*(?!true|false)\w+', ': false', concatenated_json)
            return json.loads(concatenated_json)

    def label_all(self, path='output/filtered-unique.json'):
        """
        This method is used to label all ads as scam or not scam. It will internally use the prompt method AFTER
        the generate_criteria method is used on the data to provide the LLM the text AND the criteria.
        :param path: The path to the JSON file with the ads to label.
        :return: Puts the labels in the JSON file specified at the path.
        """
        start_time = datetime.datetime.now()
        # check if path exists
        if not os.path.exists(path) or not path.endswith('.json'):
            print(f'[{start_time.strftime("%H:%M")}] » Could not find JSON file: `{path}`')
            return
        print(f'[{start_time.strftime("%H:%M")}] » Starting labeling...')
        # Load the JSON file
        with open(path, 'r') as f:
            data = json.load(f)
        for i, ad in enumerate(tqdm(data['data'], desc=f'Labeling {path}')):
            if i % 50 == 0:
                with open(path, 'w') as w:
                    json.dump(data, w, indent=4)
            if self.has_label(ad):
                continue
            try:
                label = self.generate_label(ad)
                ad['classification']['scam'] = label['scam']
                ad['classification']['reason'] = label['reason']
                ad['classification']['confidence'] = label['confidence']
                ad['classification']['classifier'] = f"m:{self.classifier_model};t:{self.temp};k:{self.top_k};p:{self.top_p}"
            except Exception as e:
                print(f'[{datetime.datetime.now().strftime("%H:%M")}] » Could not label ad: {e}')
        with open(path, 'w') as w:
            json.dump(data, w, indent=4)
            print(f'[{datetime.datetime.now().strftime("%H:%M")}] » Updated JSON file: `{path}`')
        end_time = datetime.datetime.now()
        total_time = (end_time - start_time).seconds / 60
        print(f'[{end_time.strftime("%H:%M")}] » Finished labeling within {total_time:.2f} minutes!')
        return data

    def has_criteria(self, ad):
        """
        This method checks if an ad has ALL the criteria in the 'classification' dictionary.
        It also checks if the 'model' key is present in the 'classification' dictionary.
        And if the 'model' key is present, it checks if the model is the same as the current model parameters.
        :param ad: The ad to check.
        :return: True if the ad has all the criteria: about_crypto, free_crypto, giveaway, unrealistic, bio_link, and
        limited_time.
        """
        return 'classification' in ad and all(key in ad['classification'] for key in
                                              ['about_crypto', 'free_crypto', 'giveaway', 'unrealistic', 'bio_link',
                                               'limited_time']) and \
               'model' in ad['classification'] and ad['classification']['model'] == \
               f"m:{self.criteria_model};t:{self.temp};k:{self.top_k};p:{self.top_p}"

    def has_label(self, ad):
        """
        This method checks if an ad has the label in the 'classification' dictionary.
        It also checks if the 'model' key is present in the 'classification' dictionary.
        And if the 'model' key is present, it checks if the model is the same as the current model parameters.
        :param ad: The ad to check.
        :return: True if the ad has a 'scam' label in the 'classification' dictionary.
        """
        return 'classification' in ad and 'scam' in ad['classification'] and \
                'model' in ad['classification'] and ad['classification']['classifier'] == \
                f"m:{self.classifier_model};t:{self.temp};k:{self.top_k};p:{self.top_p};"

    def limit_text(self, text_set, limit=4000):
        """
        This method concatenates the string content of a set and limits the amount of characters.
        :param: text_set: The set of strings to concatenate.
        :param: limit: The maximum amount of characters to return. Default is 5000.
        :param: remove_unicode: Whether to remove Unicode codes from the text. Default is True.
        :return: The concatenated string with a maximum of 'limit' characters.
        """
        text = text_set if isinstance(text_set, str) else ' '.join(text_set)
        text = text.replace('\n', ' ').replace('\t', ' ').replace('\r', ' ')
        return text[:limit] if len(text) > limit else text

    def is_about_crypto(self, ad):
        """
        This method checks if an ad is about cryptocurrency by checking if the 'about_crypto' criterion is True.
        :param ad: The ad to check.
        :return: True if the ad is about cryptocurrency.
        """
        return 'classification' in ad and ad['classification'].get('about_crypto', False)

    def generate_label(self, ad):
        """
        This method generates a label for an ad based on the classification dictionary.
        :param ad: The ad to generate a label for.
        :return: The label as JSON: {"scam": <true/false>}
        """
        template = '''{
            "scam": <true/false>,
            "reason": "",
            "confidence": ""
        }'''
        prompt = f"""
        Please classify whether the ad is a "crypto scam" (true if scam, false if not scam) 
        based on the following information:
        {{
            "ad_creative_bodies": {self.limit_text(set(ad['ad_creative_bodies']), 3000) if 'ad_creative_bodies' in ad else 'None'},
            "video_transcription": "{self.limit_text(ad['video_transcription'], 2000) if 'video_transcription' in ad else 'None'}"
        }}
        Note that we consider something a "crypto scam" only if it is a scam related to cryptocurrency. 
        Trying to take anything other than cryptocurrency is not a crypto scam.
        Something like "Claim your FREE <amount> <crypto> now!" is a scam as 'claiming' implies getting it for free
        but "Join our community to learn more about <crypto>!" is not. Even though
        the latter might take your crypto or offers unrealistic profits after joining the community.
        So be sure you do NOT label ads as scam when:
        - They try to teach you about cryptocurrency
        - They offer you to join a community
        - They want to share information about cryptocurrency
        - They explain how they did grow their crypto
        - They offer you techniques or ways to grow your crypto
        Please provide a very short reason for the label as well as a confidence score which is either:
        - Very unlikely: meaning the ad is very unlikely a scam
        - Unlikely: meaning the ad is unlikely a scam
        - Unsure: meaning it would be a guess to say if it is a scam
        - Likely: meaning the ad is likely a scam
        - Very likely: meaning the ad is very likely a scam
        Use the following template to fill in the label:
        {template}
        """
        return self.try_to_json(
            self.client.generate(model=self.classifier_model, prompt=prompt, format='json',
                                 options={'temperature': self.temp, 'top_k': self.top_k, 'top_p': self.top_p})['response'])

