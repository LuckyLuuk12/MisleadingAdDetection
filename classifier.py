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

# Suppress specific warnings from moviepy
warnings.filterwarnings("ignore", category=UserWarning, module="moviepy")
logging.getLogger("httpx").setLevel(logging.WARNING)


class Classifier:
    def __init__(self):
        load_dotenv()
        os.environ['HSA_OVERRIDE_GFX_VERSION'] = '10.3.0'
        self.max_video_length = os.getenv('MAX_VIDEO_LENGTH') or 150
        self.model = whisper.load_model("turbo")
        self.model_name = "llama3.2"
        self.client = ollama.Client()  # Using this we can get responses faster, we still need to keep message memory
        self.max_ollama_history = int(os.getenv('MAX_OLLAMA_HISTORY')) or 8
        self.top_k = int(os.getenv('TOP_K')) or 30
        self.top_p = float(os.getenv('TOP_P')) or 0.7
        self.temp = float(os.getenv('TEMPERATURE')) or 0.3

    def textify(self):
        """
        This method loops over all collected ads and checks if there is a video for the ad id.
        Then it will convert the video to text and store the text in the JSON file.
        """
        output_dir = 'output'
        start_time = datetime.datetime.now()
        print(f'» [{start_time.strftime("%H:%M")}] Starting complex speech to text...')
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
                for ad in ad_data['data']:
                    ad_id = ad['id']
                    if 'video_transcription' in ad:
                        continue
                    video_path = f'{output_dir}/{folder}/ads_videos/ad_{ad_id}_video.mp4'
                    # Check if the video file exists and convert it to text
                    if f'ad_{ad_id}_video.mp4' in os.listdir(f'{output_dir}/{folder}/ads_videos'):
                        count += 1
                        text, language = self.whisper_stt(video_path)
                        if text:
                            ad['video_transcription'] = text
                        if language:
                            ad['detected_language'] = language
                        with open(f'{output_dir}/{folder}/json/{json_file}', 'w') as w:
                            json.dump(ad_data, w, indent=4)
        end_time = datetime.datetime.now()
        total_time = (end_time - start_time).seconds / 60
        print(f'» [{end_time.strftime("%H:%M")}] Finished complex speech to text within {total_time:.2f} minutes! '
              f'({count} ads)')

    def whisper_stt(self, video_path):
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
            video = VideoFileClip(video_path).subclip(0, self.max_video_length)
            if video.audio is None:
                return text, language
            video.audio.write_audiofile(audio_path, verbose=False, logger=None)
            video.close()
            audio = AudioSegment.from_wav(audio_path)
            audio.export(audio_path, format='wav')
            # Convert audio to text using Whisper
            result = self.model.transcribe(audio=audio_path)
            print(f'» [{datetime.datetime.now().strftime("%H:%M")}] Result: {result}')
            text = result['text']
            language = result['language']
            print(f'» [{datetime.datetime.now().strftime("%H:%M")}] Converted video to text for `{video_path}`')
        except Exception as e:
            print(f'» [{datetime.datetime.now().strftime("%H:%M")}] Error converting video to text: {e}')
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)

        return text, language

    def first_prompt(self, log=False):
        """
        This method is used to prompt the LLM for the first time.
        It should explain to the model what the purpose of the program is.
        :param log: Whether to log the messages to the console.
        :return: The updated messages list as memory for the LLM.
        """
        msg = """
        You are a specialist in detecting scam ads. Help classify ads as "S"
        (scam) or "NS" (not scam) based on ad creative bodies and video transcriptions.
        A scam ad is misleading, false, or deceptive, often offering free or
        unrealistic products/services, seeking personal info or money, or
        leading to phishing sites. Provide a confidence score (0-1) and a short'
        explanation for each classification. Return results in JSON format please.
        If you do not understand the language or if the ad is not about cryptocurrency,
        then you may return "NS" with a confidence score of 0.0 without an explanation.
        Here you also see an example JSON template what I expect you to return:
        {"classification": "S", "confidence": 0.5, "explanation": "The ad is a scam because..."}
        Just say "ok" if you understood, then I'll show you some examples.
        """
        return self.prompt([], msg, log)

    def second_prompt(self, messages, log=False):
        """
        This method is used to prompt the LLM for the second time.
        It should provide examples of the "classification" task we want to perform.
        :return: The updated messages list as memory for the LLM.
        """
        msg = f'Below are some examples of inputs and the desired example outputs, just say "ok" if you understood.\n'
        # Open the example_scams.json file and read the data list of JSON objects
        with open('example_scams.json', 'r') as f:
            example_data = json.load(f)
        # example['ad_creative_bodies'], example['video_transcription']
        for example in example_data['data']:
            try:
                msg += f'''Possible Input:
                {{
                    "ad_creative_bodies": {example['ad_creative_bodies']},
                    "video_transcription": "{example['video_transcription']}"
                }}
                '''
                msg += f'''Expected Output:
                {{"classification": {example['output']['classification']}, "confidence": {example['output']['confidence']},"explanation": "{example['output']['explanation']}"}}
                '''
            except Exception as e:
                print(f'» Could not provide example: {e}')
        return self.prompt(messages, msg, log)

    def classify_prompt(self, messages, ad, log=False):
        """
        This method is used to prompt the LLM for the classification task.
        :param messages: The memory for the LLM.
        :param ad: The ad to classify of which we provide the ad_creative_bodies, ad_creative_link_captions,
        ad_creative_link_descriptions, ad_creative_titles, video_transcription and detected_language.
        :param log: Whether to log the messages to the console.
        :return: The updated messages list as memory for the LLM.
        """
        msg = f"""
        Please classify the ad below as "S" (scam) or "NS" (no scam) as instructed before:\n
        {{
            "ad_creative_bodies": {ad['ad_creative_bodies'] if 'ad_creative_bodies' in ad else None},
            "video_transcription": {ad['video_transcription'] if 'video_transcription' in ad else None},
        }}
        \n See here the template example JSON format for the classification and don't return anything else:\n
        {{"classification": "S", "confidence": 0.5, "explanation": "The ad is a scam because..."}}
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
        if log:
            print(f'» [{start_time.strftime("%H:%M")}] User: {msg}')
        messages.append({'role': 'user', 'content': msg})
        classification = self.client.chat(model=self.model_name, messages=messages, stream=False,
                                          options={'top_k': self.top_k, 'top_p': self.top_p, 'temperature': self.temp})
        full_classification = classification['message']['content']
        # for line in classification:
        #     full_classification += line['message']['content']
        response_time = datetime.datetime.now()
        if log:
            print(f'» [{response_time.strftime("%H:%M")}] LLM: ({response_time-start_time} - hh:mm:ss:ms)\n'
                  f'{full_classification}')
        messages.append({'role': 'assistant', 'content': full_classification})
        return messages[:4] + messages[-self.max_ollama_history:]

    def classify(self, only_filtered=False, log=False):
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
        print(f'» [{start_time.strftime("%H:%M")}] Starting complex classification...')
        # Loop over all folders in the output directory
        for folder in os.listdir(output_dir):
            # Skip if the folder is not a directory
            json_folder = 'filtered' if only_filtered else 'json'
            if not os.path.isdir(f'{output_dir}/{folder}/{json_folder}'):
                continue
            print(f'» [{datetime.datetime.now().strftime("%H:%M")}] Classifying folder: `{folder}`')
            # Loop over JSON files in the folder/json directory
            for json_file in os.listdir(f'{output_dir}/{folder}/{json_folder}'):
                self.classify_json(f'{output_dir}/{folder}/{json_folder}/{json_file}', log)
        end_time = datetime.datetime.now()
        total_time = (end_time - start_time).seconds / 60
        print(f'» [{end_time.strftime("%H:%M")}] Finished complex classification within {total_time:.2f} minutes! '
              f'({success} / {processed} ads successfully classified)')

    def classify_json(self, path: str, log=False):
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
            print(f'» [{start_time.strftime("%H:%M")}] Could not find JSON file: `{path}`')
            return success, processed
        print(f'» [{start_time.strftime("%H:%M")}] Starting complex classification for `{path}`...')
        # Loop over JSON files in the folder/json directory
        with open(path, 'r', encoding='utf-8') as f:
            ad_data = json.load(f)
        # Loop over all ads in the JSON file
        messages = self.first_prompt(log)
        messages = self.second_prompt(messages, log)
        for ad in ad_data['data']:
            if f'classification' in ad and ad['classification'] is not None \
                    and 'model' in ad['classification'] and ad['classification']['model'] == self.model_name:
                continue
            processed += 1
            messages = self.classify_prompt(messages, ad, log)
            try:
                ad['classification'] = self.try_to_json(messages[-1]['content'])
                ad['classification']['model'] = self.model_name
                success += 1
            except Exception as e:
                print(f'» [{datetime.datetime.now().strftime("%H:%M")}] Could not classify ad: {e} '
                      f'in\n\t{messages[-1]["content"]}')
                messages.pop()
                messages.pop()  # Pop twice for prompt & response
        with open(path, 'w', encoding='utf-8') as w:
            json.dump(ad_data, w, indent=4)
            print(f'» [{datetime.datetime.now().strftime("%H:%M")}] Updated JSON file: `{path}`')
        end_time = datetime.datetime.now()
        total_time = (end_time - start_time).seconds / 60
        print(f'» [{end_time.strftime("%H:%M")}] Finished complex classification within {total_time:.2f} minutes! '
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
            res = re.search(r'\{.*}', msg, re.DOTALL).group()
            res = res.replace('\\n', '').replace('\\t', '').replace("'", '"')
            # Now remove any commas that are not inside a string
            res = re.sub(r',\s*([}\]])', r'\1', res)
            return json.loads(res)
