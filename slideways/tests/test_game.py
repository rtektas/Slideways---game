import unittest
from partie2 import Game, nouveau_plateau, fin, coup_possible, choisir_coup

class Rules(unittest.TestCase):
    def test_boundaries(self):
        for shift in [-3, 3]:
            moves = coup_possible(nouveau_plateau(), [shift]*4, 1)
            for r in range(1, 5):
                self.assertNotIn(str(r)+('-' if shift == -3 else '+'), moves)

    def test_no_immediate_reverse(self):
        g = Game(); g.play('A1')
        self.assertNotIn('A1', g.legal())
        g.play('2+'); self.assertNotIn('2-', g.legal())
        with self.assertRaises(ValueError): g.play('2-')

    def test_recolor(self):
        g = Game(); g.play('A1'); g.play('B1'); g.play('C1'); g.play('A1')
        self.assertEqual(g.board[0][0], 2)

    def test_multiple_lines_same_winner(self):
        b = nouveau_plateau(); b[0] = [1]*4; b[1] = [1]*4
        self.assertEqual(fin(b, [0]*4), 1)
        b[2] = [2]*4
        self.assertEqual(fin(b, [0]*4), 'égalité')

    def test_shifted_columns_and_diagonals(self):
        b = nouveau_plateau()
        for r in range(4): b[r][r] = 1
        self.assertEqual(fin(b, [0, -1, -2, -3]), 1)
        self.assertEqual(fin(b, [0]*4), 1)
        self.assertEqual(fin(b, [0, 1, 2, 3]), 0)

    def test_ai_win_and_block_both_players(self):
        for player in [1, 2]:
            b = nouveau_plateau(); b[0] = [player]*3+[0]
            self.assertEqual(choisir_coup(b, [0]*4, player, 'B2'), 'D1')
            b = nouveau_plateau(); b[0] = [3-player]*3+[0]
            m = choisir_coup(b, [0]*4, player, 'C1')
            self.assertIn(m, ['A1', 'B1', 'D1'])

    def test_complete_ai_game(self):
        g = Game()
        while not g.result:
            m = choisir_coup(g.board, g.shifts, g.turn, g.last)
            self.assertIn(m, g.legal()); g.play(m)
            self.assertTrue(all(-3 <= x <= 3 for x in g.shifts))
        self.assertLessEqual(len(g.history), 300)
        with self.assertRaises(ValueError): g.play('A1')

if __name__ == '__main__': unittest.main()

class Difficulty(unittest.TestCase):
    def test_levels_and_cancel(self):
        from partie2 import DIFFICULTIES
        from threading import Event
        import time
        depths=[]
        for level in DIFFICULTIES:
            stats={};b=nouveau_plateau();t=time.monotonic()
            m=choisir_coup(b,[0]*4,1,difficulte=level,stats=stats)
            self.assertIn(m,coup_possible(b,[0]*4,1))
            self.assertLess(time.monotonic()-t,2.5)
            depths.append(stats['depth'])
        self.assertGreater(depths[-1],depths[1])
        cancel=Event();cancel.set();t=time.monotonic()
        choisir_coup(nouveau_plateau(),[0]*4,1,difficulte='Expert',cancel=cancel)
        self.assertLess(time.monotonic()-t,.1)
