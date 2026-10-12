"""Slideways — projet original de Resul Tektas, moteur corrigé.
Les coordonnées A–D suivent les cases de leur rangée quand elle glisse.
"""
import random
from collections import Counter


def nouveau_plateau():
    return [[0] * 4 for _ in range(4)]


def indice_plateau(coup):
    return [int(coup[1]) - 1, 'ABCD'.index(coup[0])]


def coup_possible(plateau, decalage, joueur, dernier_coup=''):
    moves = []
    for r in range(4):
        for c in range(4):
            move = f'{"ABCD"[c]}{r+1}'
            if plateau[r][c] != joueur and move != dernier_coup:
                moves.append(move)
        for direction, step in [('-', -1), ('+', 1)]:
            move = f'{r+1}{direction}'
            inverse = f'{r+1}{"+" if direction == "-" else "-"}'
            if -3 <= decalage[r] + step <= 3 and dernier_coup != inverse:
                moves.append(move)
    return moves


def coup_AI(plateau, decalage, joueur, coup):
    """Applique un coup déjà validé."""
    if coup[0] in '1234':
        decalage[int(coup[0])-1] += 1 if coup[1] == '+' else -1
    else:
        r, c = indice_plateau(coup)
        plateau[r][c] = joueur


def lignes(plateau, decalage):
    cells = {(r, c + decalage[r]): plateau[r][c]
             for r in range(4) for c in range(4)}
    result = [row[:] for row in plateau]
    for col in range(-3, 7):
        for slope in [-1, 0, 1]:
            coords = [(r, col + slope*r) for r in range(4)]
            if all(p in cells for p in coords):
                result.append([cells[p] for p in coords])
    return result


def fin(plateau, decalage):
    winners = {line[0] for line in lignes(plateau, decalage)
               if line[0] and len(set(line)) == 1}
    if len(winners) == 2:
        return 'égalité'
    return next(iter(winners), 0)


DIFFICULTIES = {
    'Facile': (1, 0.10),
    'Normal': (2, 0.35),
    'Difficile': (4, 1.0),
    'Expert': (6, 2.0),
}


def choisir_coup(plateau, decalage, joueur, dernier_coup='', profondeur=2,
                  difficulte=None, cancel=None, stats=None):
    """Approfondissement itératif borné en temps ; conserve le dernier tour complet."""
    import time
    depth_limit, budget = DIFFICULTIES.get(difficulte, (profondeur, 2.0))
    deadline = time.monotonic() + budget
    root = joueur
    info = stats if stats is not None else {}
    info.update(depth=0, nodes=0)
    options = coup_possible(plateau, decalage, joueur, dernier_coup)
    if not options or fin(plateau, decalage): return None
    random.shuffle(options)
    if difficulte == 'Facile' and random.random() < 0.60:
        return options[0]

    class StopSearch(Exception): pass
    def check():
        if (cancel is not None and cancel.is_set()) or time.monotonic() >= deadline:
            raise StopSearch()
    def score(board, shifts):
        return sum((0,1,5,30,500)[line.count(root)] -
                   (0,1,5,30,500)[line.count(3-root)] for line in lignes(board, shifts))
    def children(board, shifts, turn, last):
        out=[]
        for move in coup_possible(board, shifts, turn, last):
            check()
            b,s=[r[:] for r in board],shifts[:]
            coup_AI(b,s,turn,move)
            winner=fin(b,s)
            rank=(10000 if winner==root else -10000 if winner==3-root else score(b,s))
            out.append((rank,move,b,s))
        out.sort(key=lambda v:v[0],reverse=turn==root)
        return out
    def search(board, shifts, turn, last, depth, alpha, beta):
        check();info['nodes']+=1
        winner=fin(board,shifts)
        if winner:
            return 0 if winner=='égalité' else (10000+depth if winner==root else -10000-depth)
        if depth==0: return score(board,shifts)
        entries=children(board,shifts,turn,last)
        if not entries:return 0
        best=-float('inf') if turn==root else float('inf')
        for _,move,b,s in entries:
            value=search(b,s,3-turn,move,depth-1,alpha,beta)
            if turn==root: best=max(best,value);alpha=max(alpha,best)
            else: best=min(best,value);beta=min(beta,best)
            if beta<=alpha:break
        return best
    chosen=options[0]
    try:
        entries=children(plateau,decalage,joueur,dernier_coup)
        # Always detect an immediate win before exploring deeper branches.
        for _,move,b,s in entries:
            if fin(b,s)==root:
                info['depth']=1;return move
        for depth in range(1,depth_limit+1):
            best=-float('inf');candidate=chosen;alpha=-float('inf')
            ordered=sorted(entries,key=lambda e:e[1]!=chosen)
            for _,move,b,s in ordered:
                value=search(b,s,3-joueur,move,depth-1,alpha,float('inf'))
                if value>best:best=value;candidate=move
                alpha=max(alpha,best)
            chosen=candidate;info['depth']=depth
    except StopSearch:
        pass
    return chosen


class Game:
    def __init__(self):
        self.board = nouveau_plateau()
        self.shifts = [0]*4
        self.turn = 1
        self.last = ''
        self.result = 0
        self.reason = ''
        self.history = []
        self.seen = Counter({self.key(): 1})

    def key(self):
        return (tuple(map(tuple, self.board)), tuple(self.shifts), self.turn, self.last)

    def legal(self):
        return [] if self.result else coup_possible(self.board, self.shifts, self.turn, self.last)

    def play(self, move):
        move = move.strip().upper()
        if move not in self.legal():
            raise ValueError('Coup interdit : choisissez une case ou une flèche disponible.')
        self.history.append((self.turn, move))
        coup_AI(self.board, self.shifts, self.turn, move)
        self.last = move
        self.turn = 3-self.turn
        self.result = fin(self.board, self.shifts)
        self.seen[self.key()] += 1
        if not self.result and self.seen[self.key()] >= 3:
            self.result, self.reason = 'égalité', 'Même position répétée trois fois.'
        if not self.result and not self.legal():
            self.result, self.reason = 'égalité', 'Aucun coup disponible.'
        if not self.result and len(self.history) >= 300:
            self.result, self.reason = 'égalité', 'Limite de 300 coups atteinte.'


def boucle_jeu():
    game = Game()
    print('SLIDEWAYS — vous : X ; IA : O. Coups : A1, 2+, 3-. Q : quitter.')
    try:
        while not game.result:
            for r in reversed(range(4)):
                print(str(r+1)+'  '+'   '*(game.shifts[r]+3)+' '.join('.XO'[v] for v in game.board[r]))
            print('Décalages :', game.shifts)
            if game.turn == 1:
                move = input('Votre coup > ').strip().upper()
                if move == 'Q':
                    return
            else:
                move = choisir_coup(game.board, game.shifts, game.turn, game.last)
                print('IA :', move)
            try:
                game.play(move)
            except ValueError as e:
                print(e)
        print('Égalité.' if game.result == 'égalité' else f'Joueur {game.result} gagnant !')
        print(game.reason)
    except (EOFError, KeyboardInterrupt):
        print('\nPartie quittée.')


if __name__ == '__main__':
    boucle_jeu()
