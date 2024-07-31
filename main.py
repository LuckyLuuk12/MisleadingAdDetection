"""
@author: Luuk Kablan
@description: Main code that provides Console User Interface to perform the steps of the project.
@date: 31-7-2024
"""
from collect import Collector
from analyze import Analyzer


def main():
    """
    Main function to open the console user interface.
    :return: None
    """
    collector = Collector()
    analyzer = Analyzer()
    while True:
        print('1. Collect data')
        print('2. Analyze data')
        print('3. Exit')
        choice = input('Enter your choice: ')
        if choice == '1':
            collector.collect()
        elif choice == '2':
            analyzer.analyze()
        else:
            print('Closing the program...')
            break


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

