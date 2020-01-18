## Program description

The name of the program Spaced Rehearsal is one of the names of a learning 
technique that exploits the spacing effect. It helps to learn or memorise 
a material by a revision which is spaced in gradually increasing intervals.
Such periodic review improves retention of material in the long-term memory. 
You can read more about it in the [Wikipedia](https://en.wikipedia.org/wiki/Spaced_repetition).

Program implements this technique in console. 

![Alt Text](https://github.com/Farit/Spaced-Rehearsal/raw/master/demo.gif)

Review time can be viewed graphically. After running the program open your
browser and go to the **localhost:8888.**

![Alt Text](https://github.com/Farit/Spaced-Rehearsal/raw/master/review_demo.png)


## Installation

1. Install pyenv
2. Install pipenv
3. Create virtual environment using pipenv with python version 3.8.1
    ```shell script
        pipenv --python $PYENV_DIR/versions/3.8.1/bin/python
    ```
4. Install required packages from Pipfile.
    ```shell script
        pipenv install
    ```
5. Install required nltk data.
    ```shell script
        pipenv run python -m nltk.downloader punkt averaged_perceptron_tagger
    ```
6. Install **libVLC**

    python-vlc package is Python bindings for libVLC. Without libVLC the python-vlc package won't work, 
    because all it does is try to load that library (a .dylib, .so, or .dll, depending on your platform) and 
    call functions out of it. If python-vlc could't load that library it would output the following error:
    `OSError: dlopen(libvlccore.dylib, 6): image not found`
    The easiest way to get libVLC library is to just install the VLC player.
    

## How to run the program?

### General functionality.

By running the following command:
   ```
   python3.6 run.py
   ```
you start the program with general functionality. In this mode, you can create,
alter, delete, search and review flashcards. All of your flashcards are saved
in sqlite database (you can find database name in a configuration file)

### English specific functionality.

By starting the program with the following command:
   ```shell script
   pipenv run python run.py english-mediator
   ```

you start the program with english functionality. This mode dedicated to 
learning English words and phrases. English mediator enhances 
the general functionality by providing additional fields for an answer 
pronunciation and ability to add an explanation for the flashcard.


## Program enhancement.
You can very easily add new mediator for your target language or any other 
specific mediator for your needs by extending the base mediator. 
You can look at English mediator for the example of how you can do it. 
For any questions, you can contact me. I'll be happy to help you.
