import logging

import vlc

logger = logging.getLogger(__name__)


class VLCPlayer:

    def __init__(self):
        # creating a basic vlc instance
        self._instance = vlc.Instance([
            "--file-caching=10000 --disc-caching=10000"
        ])
        # creating an empty vlc media player
        self.media_player = self._instance.media_player_new()
        self.media = None

    def is_playing(self):
        return self.media_player.is_playing()

    def play(self):
        if self.media is not None:
            if self.media_player.get_media() is None:
                self._open_file()
            self.media_player.stop()
            self.media_player.play()

    def stop(self):
        self.media_player.stop()

    def create_media(self, audio_file):
        # create the media
        self.media = self._instance.media_new(audio_file)

    def erase_media(self):
        self.media = None

    def _open_file(self):
        """
        Open a media file in a MediaPlayer
        """
        # put the media in the media player
        self.media_player.set_media(self.media) 
