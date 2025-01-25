"""
@author: Luuk Kablan
@description: Main code that provides Console User Interface to perform the steps of the project.
@date: 31-7-2024
"""
import datetime

from ai import AIToolBox
from collect import Collector
from filter import Filter
from manual import Inspector


def main():
    """
    Main function to open the console user interface.
    :return: None
    """
    collector = Collector()
    crypto_filter = Filter()
    classifier = AIToolBox()
    inspector = Inspector()
    while True:
        print('1. [AddDownloaderAPI]    Collect data')
        print('2. [Whisper STT]         Start video transcription')
        print('3. [Llama3.2]            Start criteria generation')
        print('4. [Filter]              Start crypto ad filtering')
        print('5. [Llama3.2]            Start binary labeling')
        print('6. [Manual]              Open manual labeling tool')
        print('7. [Manual]              Show statistics')
        print('8. [Llama3.2]            Relabel samples')
        print('9. [PIPELINE]            Execute all steps')
        print('x. Exit')
        choice = input('» Enter your choice: ')
        if choice == '1':
            collector.collect()
        elif choice == '2':
            classifier.transcribe_all()
        elif choice == '3':
            classifier.generate_criteria()
        elif choice == '4':
            crypto_filter.filter()
        elif choice == '5':
            classifier.label_all()
        elif choice == '6':
            inspector.inspect()
        elif choice == '7':
            inspector.print_stats()
        elif choice == '8':
            inspector.relabel()
        elif choice == '9':
            collector.collect()
            classifier.transcribe_all()
            classifier.generate_criteria()
            crypto_filter.filter()
            classifier.label_all()
            inspector.inspect()
        else:
            print('» Closing the program...')
            break


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

