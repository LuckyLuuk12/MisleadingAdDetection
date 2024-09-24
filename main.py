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
    project = None
    collector = Collector()
    analyzer = Analyzer()
    # filter = Filter()
    # classifier = Classifier()
    # inspector = Inspector()
    while True:
        print(f'» Working on project (folder): {project}')
        print('1. Select project (folder)')
        print('2. Collect data')
        print('3. Analyze data')
        print('4. Start pre-filtering')
        print('5. Start complex classification')
        print('6. Manual data inspection')
        print('7. Do all (except analysis)')
        print('8. Exit')
        choice = input('Enter your choice: ')
        if choice == '1':
            project = input('» Enter the project name (folder): ')
        elif choice == '2':
            collector.collect(project_name=project)
        elif choice == '3':
            analyzer.analyze()
        elif choice == '4':
            print('» NOT IMPLEMENTED YET!')
            # filter.filter()
        elif choice == '5':
            print('» NOT IMPLEMENTED YET!')
            # classifier.classify()
        elif choice == '6':
            print('» NOT IMPLEMENTED YET!')
            # inspector.inspect()
        elif choice == '7':
            print('» NOT IMPLEMENTED YET!')
            # collector.collect()
            # filter.filter()
            # classifier.classify()
            # inspector.inspect()
        else:
            print('» Closing the program...')
            break


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

