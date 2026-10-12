import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import unittest
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest
from projet3 import Window

app = QApplication.instance() or QApplication([])

class Interface(unittest.TestCase):
    def setUp(self):
        self.w=Window();self.w.show();app.processEvents();self.p=self.w.panel
    def tearDown(self): self.w.close();app.processEvents()

    def test_menu_setup_and_modes(self):
        self.assertIs(self.w.stack.currentWidget(),self.w.menu_page)
        self.w.setup();self.assertIs(self.w.stack.currentWidget(),self.w.setup_page)
        self.w.level_buttons[3].click();self.w.start()
        self.assertEqual(self.p.difficulty.currentText(),'Expert')
        self.assertEqual([m.currentText() for m in self.p.modes],['Humain','IA'])
        self.assertTrue(all(b.text()=='' for b in self.p.buttons.values()))

    def test_internal_rules_options_and_pause(self):
        self.w.setup();self.w.start();self.w.rules()
        self.assertIs(self.w.stack.currentWidget(),self.w.rules_page)
        self.assertFalse(self.p.active)
        self.w.back();self.assertIs(self.w.stack.currentWidget(),self.p)
        self.w.pause_game();self.assertIs(self.w.stack.currentWidget(),self.w.pause_page)
        self.w.options();self.w.options_level.setCurrentText('Facile');self.w.back()
        self.w.resume();self.assertEqual(self.p.difficulty.currentText(),'Facile')

    def test_duel_clicks_shifts_and_victory(self):
        self.w.setup();self.w.mode.setCurrentIndex(1);self.w.start()
        self.p.buttons['A1'].click();self.assertEqual(self.p.game.board[0][0],1)
        self.p.arrows['2+'].click();self.assertEqual(self.p.game.shifts[1],1)
        self.p.new_game()
        for move in ['A1','A2','B1','B2','C1','C2','D1']:
            self.p.human_move(move)
        self.assertEqual(self.p.game.result,1)
        self.assertIn('VICTOIRE',self.p.status.text())

    def test_ai_reply_and_menu_resume(self):
        self.w.start();self.p.delay.setValue(100);self.p.buttons['A1'].click()
        for _ in range(150):
            QTest.qWait(20)
            if len(self.p.game.history)>=2:break
        self.assertEqual(len(self.p.game.history),2)
        self.w.menu();count=len(self.p.game.history);QTest.qWait(250)
        self.assertEqual(len(self.p.game.history),count)
        self.w.resume();self.assertTrue(self.p.active)

    def test_audio(self):
        a=self.w.audio;self.assertTrue(a.ready,a.error)
        self.assertEqual(a.track,'menu');self.assertTrue(a.mixer.music.get_busy())
        self.w.change_volume(43);self.assertAlmostEqual(a.volume,.43)
        before=a.muted;self.w.toggle_sound();self.assertNotEqual(a.muted,before)

if __name__=='__main__':unittest.main()
