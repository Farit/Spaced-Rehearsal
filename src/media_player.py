import logging

import vlc

logger = logging.getLogger(__name__)


class Player:

    def __init__(self):
        self.vlc_player = VLCPlayer()

    def play(self, audio_file):
        self.vlc_player.play(audio_file)


class VLCPlayer:

    def play(self, audio_file):
        vlc.MediaPlayer(f'file://{audio_file}').play()
