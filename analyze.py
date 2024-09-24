"""
@author: Luuk Kablan
@description: This file contains the analysis class that is used to analyze the data.
@date: 31-7-2024
"""
from AdDownloader.start_app import start_gui
from AdDownloader.cli import run_analysis

class Analyzer:
    """
    This class is used to analyze the collected data.
    """

    def __init__(self):
        self.output_dir = 'out'

    def load_data(self):
        # Load data from JSON file
        pass

    def analyze(self):
        """
        This method analyzes the data.
        :return: The analysis results.
        """
        start_gui()
        run_analysis()
        pass
