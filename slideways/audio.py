"""Lecture locale OGG : aucune connexion requise pendant le jeu."""
import os
from pathlib import Path
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

class Audio:
    def __init__(self):
        self.ready = False
        self.track = None
        self.volume = 0.30
        self.muted = False
        self.error = ''
        try:
            import pygame.mixer as mixer
            mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            self.mixer = mixer
            self.ready = True
        except Exception as exc:
            self.error = str(exc)

    def play(self, mode):
        if not self.ready or mode == self.track:
            return
        name = 'empacotatron_menu.ogg' if mode == 'menu' else 'empacotatron_loop.ogg'
        try:
            self.mixer.music.load(str(Path(__file__).parent / 'assets' / 'music' / name))
            self.mixer.music.set_volume(0 if self.muted else self.volume)
            self.mixer.music.play(-1, fade_ms=500)
            self.track = mode
        except Exception as exc:
            self.error = str(exc)
            self.ready = False

    def set_volume(self, value):
        self.volume = value / 100
        if self.ready: self.mixer.music.set_volume(0 if self.muted else self.volume)

    def toggle(self):
        self.muted = not self.muted
        if self.ready: self.mixer.music.set_volume(0 if self.muted else self.volume)

    def close(self):
        if self.ready: self.mixer.quit()
