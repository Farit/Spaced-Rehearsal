import logging

import vlc

from src.config import ConfigAdapter

logger = logging.getLogger(__name__)


class Player:

    def __init__(self, audio_file):
        self.audio_file = audio_file
        self.vlc_player = VLCPlayer()

    def play(self):
        self.vlc_player.play(self.audio_file)


class VLCPlayer:

    def __init__(self):
        self.config = ConfigAdapter(filename='config.cfg')

    def play(self, audio_file):
        vlc.MediaPlayer(f'file://{audio_file}').play()
