"""Interface Slideways — Resul Tektas. Lancement : python projet3.py."""
import sys
from threading import Event
from PyQt5.QtCore import Qt, QTimer, QObject, QRunnable, QThreadPool, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QComboBox,
                            QVBoxLayout, QHBoxLayout, QGridLayout, QSpinBox)
from partie2 import Game, choisir_coup


class Signals(QObject):
    done = pyqtSignal(int, object)
    failed = pyqtSignal(int, str)


class Think(QRunnable):
    def __init__(self, token, game, difficulty="Normal"):
        super().__init__()
        self.token = token
        self.difficulty = difficulty
        self.cancel = Event()
        self.args = ([r[:] for r in game.board], game.shifts[:], game.turn, game.last)
        self.signals = Signals()

    def run(self):
        try:
            self.signals.done.emit(self.token, choisir_coup(*self.args, difficulte=self.difficulty, cancel=self.cancel))
        except Exception as exc:
            self.signals.failed.emit(self.token, str(exc))


class Controller(QWidget):
    def invalidate(self):
        for job in self.jobs.values(): job.cancel.set()
        self.token += 1; self.timer.stop(); self.busy = False

    def new_game(self):
        self.invalidate(); self.game = Game(); self.paused = False
        self.pause.setText('Pause'); self.render(); self.schedule()

    def mode_changed(self):
        if hasattr(self, 'game'):
            self.invalidate(); self.render(); self.schedule()

    def toggle_pause(self):
        self.invalidate(); self.paused = not self.paused
        self.pause.setText('Reprendre' if self.paused else 'Pause')
        self.render(); self.schedule()

    def human_move(self, move):
        if self.paused or self.busy or self.modes[self.game.turn-1].currentText() != 'Humain': return
        self.apply(move)

    def apply(self, move):
        try: self.game.play(move)
        except ValueError as exc:
            self.status.setText(str(exc)); return
        self.render(); self.schedule()

    def schedule(self):
        self.timer.stop()
        if not self.game.result and not self.paused and self.modes[self.game.turn-1].currentText() == 'IA':
            self.timer.start(self.delay.value())

    def start_ai(self):
        if self.game.result or self.paused or self.busy or self.modes[self.game.turn-1].currentText() != 'IA': return
        self.busy = True
        job = Think(self.token, self.game, self.difficulty.currentText()); self.jobs[self.token] = job
        job.signals.done.connect(self.ai_done); job.signals.failed.connect(self.ai_failed)
        self.render(); self.pool.start(job)

    def ai_done(self, token, move):
        self.jobs.pop(token, None)
        if token != self.token: return
        self.busy = False
        if move is not None: self.apply(move)
        else: self.render()

    def ai_failed(self, token, message):
        self.jobs.pop(token, None)
        if token != self.token: return
        self.busy = False; self.paused = True; self.pause.setText('Reprendre')
        self.render(); self.status.setText('Erreur IA : '+message)

    def closeEvent(self, event):
        self.invalidate(); self.pool.waitForDone(); event.accept()
