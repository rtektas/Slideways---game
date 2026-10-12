"""Slideways — Neon Arcade. Projet de Resul Tektas."""
import sys
import math
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF, QSettings, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QPainter, QColor, QPen, QLinearGradient, QRadialGradient, QFont, QPolygonF
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QComboBox,
 QVBoxLayout, QHBoxLayout, QGridLayout, QSpinBox, QStackedWidget, QFrame, QSlider,
 QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QButtonGroup, QShortcut)
from controller import Controller, Think, QThreadPool
from partie2 import Game, DIFFICULTIES
from audio import Audio

CYAN = '#48ecff'
PINK = '#ff58c8'


def label(text, size=14, color='#a5a0c9', bold=False):
    w = QLabel(text)
    w.setStyleSheet(f'color:{color};font-size:{size}px;font-weight:{"bold" if bold else "normal"};background:transparent;')
    return w


def button(text, action, primary=False):
    b = QPushButton(text); b.setCursor(Qt.PointingHandCursor)
    if primary: b.setObjectName('primary')
    b.clicked.connect(action)
    return b


def glow(widget, color, blur=24):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur); effect.setOffset(0, 0); effect.setColor(QColor(color))
    widget.setGraphicsEffect(effect)


class Backdrop(QWidget):
    def __init__(self):
        super().__init__(); self.phase = 0
        self.anim = QTimer(self); self.anim.timeout.connect(self.tick); self.anim.start(50)
    def tick(self):
        self.phase = (self.phase + 0.012) % 1; self.update()
    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w,h = self.width(),self.height()
        bg = QLinearGradient(0,0,w,h);bg.setColorAt(0,QColor('#100b29'));bg.setColorAt(1,QColor('#060815'))
        p.fillRect(self.rect(),bg)
        for x,y,col,radius in [(w*.8,h*.18,'#622162',w*.5),(w*.1,h*.6,'#073c57',w*.5)]:
            rad = QRadialGradient(QPointF(x,y),radius)
            c=QColor(col);c.setAlpha(120);rad.setColorAt(0,c);rad.setColorAt(1,QColor(0,0,0,0))
            p.fillRect(self.rect(),rad)
        horizon=h*.72
        p.setPen(QPen(QColor(116,61,164,65),1))
        for i in range(-10,11):
            p.drawLine(QPointF(w/2+i*20,horizon),QPointF(w/2+i*w*.13,h))
        for i in range(12):
            t=(i+self.phase)/12; y=horizon+(h-horizon)*t*t
            p.drawLine(QPointF(0,y),QPointF(w,y))
        for i in range(45):
            x=(i*137+37)%max(w,1); y=(i*73+19)%max(int(h*.7),1)
            p.setPen(QColor(170,169,224,55+(i%4)*15));p.drawPoint(x,y)


class Tile(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent); self.value=0; self.recent=False
        self.setFixedSize(60,60); self.setCursor(Qt.PointingHandCursor)
    def paintEvent(self, event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        rect=QRectF(3,3,self.width()-6,self.height()-6)
        col=QColor(CYAN if self.value==1 else PINK if self.value==2 else '#66518d')
        hover=self.underMouse() and self.isEnabled()
        fill=QColor('#13283a' if self.value==1 else '#31152e' if self.value==2 else '#171329')
        if hover: fill=fill.lighter(150)
        p.setBrush(fill);p.setPen(QPen(col if self.value or hover else QColor('#413459'),1.5));p.drawRoundedRect(rect,9,9)
        if self.recent:
            p.setBrush(Qt.NoBrush);p.setPen(QPen(QColor('#ffe398'),2));p.drawRoundedRect(rect.adjusted(-2,-2,2,2),10,10)
        if self.value:
            for thick,alpha in [(10,18),(6,45),(3,255)]:
                c=QColor(col);c.setAlpha(alpha);p.setPen(QPen(c,thick,Qt.SolidLine,Qt.RoundCap));p.setBrush(Qt.NoBrush)
                if self.value==1:
                    p.drawLine(QPointF(20,20),QPointF(40,40));p.drawLine(QPointF(40,20),QPointF(20,40))
                else: p.drawEllipse(QRectF(18,18,24,24))
        else:
            p.setPen(Qt.NoPen);p.setBrush(QColor('#6e5b8b' if hover else '#3e3453'));p.drawEllipse(QPointF(30,30),2,2)
        if not self.isEnabled() and not self.value:
            p.setBrush(QColor(5,4,12,65));p.setPen(Qt.NoPen);p.drawRoundedRect(rect,9,9)


class GamePanel(Controller):
    def __init__(self, shell):
        QWidget.__init__(self)
        self.shell=shell; self.active=False; self.token=0;self.busy=False;self.paused=False;self.jobs={}
        self.pool=QThreadPool(self);self.pool.setMaxThreadCount(1)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.timeout.connect(self.start_ai)
        layout=QVBoxLayout(self);layout.setContentsMargins(16,8,16,8);layout.setSpacing(14)
        top=QHBoxLayout();top.addWidget(label('SLIDEWAYS',25,'#f0e6ff',True));top.addStretch()
        top.addWidget(button('← MENU',self.shell.menu));layout.addLayout(top)
        controls=QHBoxLayout();self.modes=[]
        for i in range(2):
            controls.addWidget(label(f'{"✕" if i==0 else "○"}  JOUEUR {i+1}',13,CYAN if i==0 else PINK,True))
            combo=QComboBox();combo.addItems(['Humain','IA']);combo.setCurrentIndex(i)
            combo.currentIndexChanged.connect(self.mode_changed);self.modes.append(combo);controls.addWidget(combo)
            if i==0: controls.addStretch()
        controls.addSpacing(16);controls.addWidget(label('RYTHME IA',11))
        self.delay=QSpinBox();self.delay.setRange(100,3000);self.delay.setValue(500);self.delay.setSuffix(' ms');self.delay.setSingleStep(100)
        controls.addWidget(self.delay);layout.addLayout(controls)
        airow=QHBoxLayout();airow.addStretch();airow.addWidget(label('DIFFICULTÉ IA',11))
        self.difficulty=QComboBox();self.difficulty.addItems(list(DIFFICULTIES));self.difficulty.setCurrentText('Normal');self.difficulty.currentTextChanged.connect(self.mode_changed)
        airow.addWidget(self.difficulty);airow.addStretch();layout.addLayout(airow)
        self.status=label('',19,'#ffffff',True);self.status.setAlignment(Qt.AlignCenter);self.status.setMinimumHeight(44)
        layout.addWidget(self.status)
        arena=QFrame();arena.setObjectName('arena');arena.setFixedSize(862,310)
        self.grid=QGridLayout(arena);self.grid.setContentsMargins(16,16,16,16);self.grid.setSpacing(6)
        for c in range(1,11): self.grid.setColumnMinimumWidth(c,60)
        self.buttons={};self.arrows={}
        for r in range(4):
            for direction,col,text in [('-',0,'‹'),('+',11,'›')]:
                move=f'{r+1}{direction}';b=button(text,lambda checked=False,m=move:self.human_move(m))
                b.setFixedSize(40,60);b.setStyleSheet('font-size:28px;padding:0px;');b.setAccessibleName('Glisser à gauche' if direction=='-' else 'Glisser à droite')
                self.grid.addWidget(b,3-r,col);self.arrows[move]=b
            for c in range(4):
                move=f'{"ABCD"[c]}{r+1}';b=Tile();b.clicked.connect(lambda checked=False,m=move:self.human_move(m));self.buttons[move]=b
        center=QHBoxLayout();center.addStretch();center.addWidget(arena);center.addStretch();layout.addLayout(center)
        self.last_label=label('',12);self.last_label.setAlignment(Qt.AlignCenter);layout.addWidget(self.last_label)
        hint=label('COLOREZ  •  GLISSEZ  •  ALIGNEZ QUATRE',12,'#80759d',True);hint.setAlignment(Qt.AlignCenter);layout.addWidget(hint)
        row=QHBoxLayout();row.addStretch()
        row.addWidget(button('↻  REJOUER',self.new_game))
        self.pause=button('Ⅱ  PAUSE',self.shell.pause_game);row.addWidget(self.pause)
        row.addWidget(button('RÈGLES',self.shell.rules));row.addStretch();layout.addLayout(row)
        layout.addStretch();self.game=Game();self.render()

    def new_game(self):
        self.invalidate();self.game=Game();self.paused=False;self.pause.setText('Ⅱ  PAUSE');self.render();self.schedule()
    def render(self):
        g=self.game;allowed=set(g.legal())
        human=self.active and not self.paused and not self.busy and self.modes[g.turn-1].currentText()=='Humain'
        for b in self.buttons.values(): self.grid.removeWidget(b)
        for r in range(4):
            for c in range(4):
                move=f'{"ABCD"[c]}{r+1}';b=self.buttons[move];b.value=g.board[r][c];b.recent=move==g.last
                b.setAccessibleName(f'Rangée {r+1}, case {c+1}, '+['vide','croix','cercle'][b.value])
                b.setEnabled(human and move in allowed);b.update();self.grid.addWidget(b,3-r,c+g.shifts[r]+4)
        for m,b in self.arrows.items(): b.setEnabled(human and m in allowed)
        if g.result: msg='ÉGALITÉ  —  '+g.reason if g.result=='égalité' else f'VICTOIRE DU JOUEUR {g.result} !'
        elif self.paused: msg='PARTIE EN PAUSE'
        else: msg=f'JOUEUR {g.turn}  •  '+('L’IA RÉFLÉCHIT…' if self.modes[g.turn-1].currentText()=='IA' else 'À VOUS DE JOUER')
        self.status.setText(msg)
        self.last_label.setText(f'{len(g.history):02d} COUPS JOUÉS   /   '+('PARTIE TERMINÉE' if g.result else 'LE CONTOUR DORÉ INDIQUE LA DERNIÈRE CASE JOUÉE'))
    def schedule(self):
        if self.active: super().schedule()
        else: self.timer.stop()
    def start_ai(self):
        if self.active: super().start_ai()
    def human_move(self,move):
        if self.active: super().human_move(move)


class Hero(QWidget):
    """An animated isometric board, drawn live rather than a static illustration."""
    def __init__(self):
        super().__init__();self.t=0;self.setMinimumSize(380,350)
        self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(33)
    def tick(self):
        if self.isVisible():self.t+=.033;self.update()
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        p.translate(self.width()*.51,self.height()*.40+math.sin(self.t*.8)*9)
        scale=min(self.width()/520,self.height()/480);p.scale(scale,scale)
        p.rotate(-8+math.sin(self.t*.25)*3)
        def point(x,y,z=0):return QPointF((x-y)*55,(x+y)*27-z)
        for r in range(4):
            shift=math.sin(self.t*.7+r*1.1)*.38
            for c in range(4):
                x,y=c-1.5+shift,r-1.5
                corners=[point(x-.45,y-.45),point(x+.45,y-.45),point(x+.45,y+.45),point(x-.45,y+.45)]
                shadow=[q+QPointF(0,16) for q in corners]
                p.setBrush(QColor('#100d22'));p.setPen(QPen(QColor('#2b2141'),1));p.drawPolygon(QPolygonF(shadow))
                v=[[1,0,2,0],[0,2,1,0],[2,1,0,1],[0,0,2,0]][r][c]
                col=QColor(CYAN if v==1 else PINK if v==2 else '#796592')
                p.setBrush(QColor('#142436' if v==1 else '#31162e' if v==2 else '#20192c'))
                p.setPen(QPen(col,1.5));p.drawPolygon(QPolygonF(corners))
                center=point(x,y,3)
                if v:
                    p.save();p.translate(center);p.scale(1,.55);p.rotate(-45)
                    for width,alpha in [(12,15),(7,40),(3,255)]:
                        cc=QColor(col);cc.setAlpha(alpha);p.setPen(QPen(cc,width,Qt.SolidLine,Qt.RoundCap));p.setBrush(Qt.NoBrush)
                        if v==1:p.drawLine(QPointF(-12,-12),QPointF(12,12));p.drawLine(QPointF(12,-12),QPointF(-12,12))
                        else:p.drawEllipse(QRectF(-16,-16,32,32))
                    p.restore()
        p.setPen(QPen(QColor(167,117,201,40),1));p.setBrush(Qt.NoBrush)
        for radius in [220,255]:p.drawEllipse(QRectF(-radius,-radius*.42+40,radius*2,radius*.84))


class MenuButton(QPushButton):
    def __init__(self,text,action,number='',primary=False):
        super().__init__();self.caption=text;self.number=number;self.primary=primary;self._hover=0.
        self.setFixedHeight(57);self.setCursor(Qt.PointingHandCursor);self.setFocusPolicy(Qt.StrongFocus)
        self.clicked.connect(action);self.anim=QPropertyAnimation(self,b'hover');self.anim.setDuration(150)
    def get_hover(self):return self._hover
    def set_hover(self,v):self._hover=v;self.update()
    hover=pyqtProperty(float,get_hover,set_hover)
    def enterEvent(self,e):self.anim.stop();self.anim.setEndValue(1.);self.anim.start()
    def leaveEvent(self,e):self.anim.stop();self.anim.setEndValue(0.);self.anim.start()
    def paintEvent(self,e):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        hover=max(self._hover,.65 if self.hasFocus() else 0)
        p.setBrush(QColor(255,94,191,int(20+hover*22)) if self.primary else QColor(255,255,255,int(hover*10)))
        p.setPen(Qt.NoPen);p.drawRoundedRect(QRectF(0,0,self.width(),self.height()),4,4)
        if self.primary or hover:
            p.fillRect(QRectF(0,8,3,41),QColor(PINK if self.primary else CYAN))
        p.setPen(QColor('#faefff'));p.setFont(QFont('Segoe UI',16,QFont.DemiBold))
        p.drawText(QRectF(22+hover*7,0,self.width()-80,self.height()),Qt.AlignVCenter,self.caption)
        p.setFont(QFont('Consolas',10));p.setPen(QColor(PINK if self.primary else '#7d6e90'))
        p.drawText(QRectF(self.width()-45,0,36,self.height()),Qt.AlignCenter,'›' if hover else self.number)


class Window(Backdrop):
    def __init__(self):
        super().__init__();self.setWindowTitle('Slideways');self.resize(1180,820);self.setMinimumSize(1020,790)
        self.settings=QSettings('ResulTektas','SlidewaysArcade');self.audio=Audio()
        self.audio.volume=int(self.settings.value('volume',30))/100
        self.audio.muted=str(self.settings.value('muted','false')).lower()=='true'
        self.return_page=None;self.return_active=False;self.fade=None
        self.setStyleSheet('''QWidget{color:#eee7ff;font-family:"Segoe UI","DejaVu Sans",sans-serif;font-size:13px;}
          QLabel{background:transparent;} QPushButton{background:#21192f;border:1px solid #54405e;border-radius:5px;padding:10px 18px;}
          QPushButton:hover{background:#39243c;border:1px solid #dd78bc;} QPushButton:pressed{background:#54275d;}
          QPushButton:checked{background:#44253f;border:1px solid #ff86d6;color:white;}
          QPushButton:disabled{color:#605569;border-color:#332744;background:#191222;}
          QPushButton#primary{background:#f0bca4;color:#21101f;border:0;font-weight:bold;padding:16px;}
          QPushButton#primary:hover{background:#ffdbcb;}
          QComboBox,QSpinBox{background:#211a2e;border:1px solid #55405c;border-radius:4px;padding:7px;}
          QComboBox QAbstractItemView{background:#211734;color:white;selection-background-color:#713363;}
          QFrame#arena{background:rgba(12,9,27,220);border:1px solid #624275;border-radius:14px;}
          QFrame#card{background:rgba(30,23,43,220);border:1px solid #46334e;border-radius:8px;}
          QSlider::groove:horizontal{height:4px;background:#49365c;}
          QSlider::handle:horizontal{background:#f0bca4;width:14px;margin:-5px 0;border-radius:6px;}
        ''')
        outer=QVBoxLayout(self);outer.setContentsMargins(38,20,38,14)
        host=QWidget();host.setMaximumWidth(1140);row=QHBoxLayout();row.addStretch();row.addWidget(host,1);row.addStretch();outer.addLayout(row)
        v=QVBoxLayout(host);v.setContentsMargins(0,0,0,0)
        header=QHBoxLayout();header.addWidget(label('R / T     RESUL TEKTAS',11,'#b9a5c2',True));header.addStretch()
        header.addWidget(label('SLIDEWAYS  /  02',11,'#7d6d8a'));v.addLayout(header)
        self.stack=QStackedWidget();v.addWidget(self.stack,1)
        self.menu_page=self.build_menu();self.stack.addWidget(self.menu_page)
        self.panel=GamePanel(self);self.stack.addWidget(self.panel)
        self.setup_page=self.build_setup();self.stack.addWidget(self.setup_page)
        self.rules_page=self.build_rules();self.stack.addWidget(self.rules_page)
        self.options_page=self.build_options();self.stack.addWidget(self.options_page)
        self.credits_page=self.build_credits();self.stack.addWidget(self.credits_page)
        self.pause_page=self.build_pause();self.stack.addWidget(self.pause_page)
        footer=QHBoxLayout();footer.addWidget(label('ÉCHAP  Retour / Pause     •     F11  Plein écran',11,'#91809e'));footer.addStretch()
        self.sound_button=button('',self.toggle_sound);footer.addWidget(self.sound_button)
        self.volume=QSlider(Qt.Horizontal);self.volume.setRange(0,100);self.volume.setValue(int(self.audio.volume*100));self.volume.setFixedWidth(100)
        self.volume.valueChanged.connect(self.change_volume);footer.addWidget(self.volume);v.addLayout(footer)
        QShortcut('Escape',self,activated=self.escape);QShortcut('F11',self,activated=self.fullscreen)
        self.menu()

    def page(self,title,kicker):
        page=QWidget();v=QVBoxLayout(page);v.setContentsMargins(28,34,28,28);v.setSpacing(18)
        top=QHBoxLayout();top.addWidget(label(kicker,11,'#d7aa94',True));top.addStretch();top.addWidget(button('← RETOUR',self.back));v.addLayout(top)
        v.addWidget(label(title,38,'#faefff',True))
        return page,v
    def build_menu(self):
        page=QWidget();h=QHBoxLayout(page);h.setContentsMargins(40,30,0,30);h.setSpacing(0)
        left=QVBoxLayout();left.setSpacing(7);left.addStretch()
        left.addWidget(label('UN JEU DE STRATÉGIE EN MOUVEMENT',10,'#d3a38e',True));left.addSpacing(10)
        title=label('SLIDE\nWAYS',73,'#fff0ee',True);title.setStyleSheet('font-family:"Segoe UI",sans-serif;font-size:73px;font-weight:900;color:#fff0ee;line-height:1;');left.addWidget(title)
        left.addWidget(label('Une ligne peut tout changer.',17,'#ac97b7'));left.addSpacing(23)
        self.play_button=MenuButton('Nouvelle partie',self.setup,'01',True);left.addWidget(self.play_button)
        self.resume_button=MenuButton('Continuer',self.resume,'02');left.addWidget(self.resume_button)
        left.addWidget(MenuButton('Comment jouer',self.rules,'03'))
        left.addWidget(MenuButton('Options',self.options,'04'))
        bottom=QHBoxLayout();bottom.addWidget(button('CRÉDITS',self.credits));bottom.addWidget(button('QUITTER',self.close));left.addLayout(bottom)
        left.addStretch();h.addLayout(left,5)
        right=QVBoxLayout();self.hero=Hero();right.addWidget(self.hero,1)
        text=label('PENSEZ LE COUP.\nDÉPLACEZ L’ÉQUILIBRE.',17,'#c1a9cf',True);text.setAlignment(Qt.AlignCenter);right.addWidget(text)
        right.addWidget(label('        SOLO  /  DUEL LOCAL  /  SPECTATEUR',10,'#7e6c8c'));right.addSpacing(70);h.addLayout(right,6)
        return page
    def build_setup(self):
        page,v=self.page('Choisissez votre défi.','NOUVELLE PARTIE')
        self.mode=QComboBox();self.mode.addItems(['SOLO  /  CONTRE L’IA','DUEL  /  DEUX JOUEURS','DÉMO  /  IA CONTRE IA']);self.mode.setMinimumHeight(42)
        v.addWidget(label('MODE DE JEU',11));v.addWidget(self.mode)
        v.addWidget(label('DIFFICULTÉ DE L’IA',11))
        row=QHBoxLayout();self.level_group=QButtonGroup(self);self.level_buttons=[]
        descriptions=[('Facile','Pour découvrir','Jeu permissif et imprévisible.'),('Normal','Pour progresser','Anticipe votre prochain coup.'),('Difficile','Pour se mesurer','Construit ses plans sur plusieurs coups.'),('Expert','Pour le défi','Recherche plus loin avant de décider.')]
        for i,(name,sub,desc) in enumerate(descriptions):
            b=QPushButton(name+'\n\n'+sub);b.setCheckable(True);b.setMinimumHeight(106);self.level_group.addButton(b,i);self.level_buttons.append(b);row.addWidget(b)
        self.level_buttons[1].setChecked(True);v.addLayout(row)
        self.level_description=label(descriptions[1][2],16,'#dcc5e3');v.addWidget(self.level_description)
        self.level_group.buttonClicked[int].connect(lambda i:self.level_description.setText(descriptions[i][2]))
        self.mode.currentIndexChanged.connect(lambda i:[b.setEnabled(i!=1) for b in self.level_buttons])
        v.addStretch();v.addWidget(label('Les croix commencent. Retournez une case, ou déplacez une rangée.',13))
        v.addWidget(button('ENTRER DANS LA PARTIE   →',self.start,True));return page
    def build_rules(self):
        page,v=self.page('Simple à jouer. Subtil à maîtriser.','COMMENT JOUER')
        for number,title,body in [
            ('01','Alignez quatre symboles','Une ligne, une colonne ou une diagonale de votre couleur : vous gagnez.'),
            ('02','Choisissez votre action','Colorez une case vide ou adverse, OU faites glisser une rangée avec les flèches.'),
            ('03','Chaque glissement compte','Les cases suivent leur rangée, dans une limite de trois positions à gauche ou à droite.'),
            ('04','Pas de retour immédiat','La dernière case jouée est protégée un tour. Le dernier glissement ne peut pas être immédiatement annulé.')]:
            f=QFrame();f.setObjectName('card');r=QHBoxLayout(f);r.setContentsMargins(18,13,18,13)
            r.addWidget(label(number,25,'#d8a993',True));col=QVBoxLayout();col.addWidget(label(title,18,'#f5eaf9',True))
            t=label(body,14);t.setWordWrap(True);col.addWidget(t);r.addLayout(col,1);v.addWidget(f)
        t=label('Égalité : deux couleurs alignées simultanément, trois répétitions du même état, aucun coup disponible ou 300 coups joués.',12);t.setWordWrap(True);v.addWidget(t);v.addStretch();return page
    def build_options(self):
        page,v=self.page('À votre rythme.','OPTIONS')
        v.addWidget(label('AFFICHAGE',12,'#d5ac98',True));v.addWidget(button('BASCULER PLEIN ÉCRAN  /  F11',self.fullscreen))
        self.motion=QPushButton('ANIMATIONS : OUI');self.motion.setCheckable(True);self.motion.setChecked(True);self.motion.clicked.connect(self.motion_changed);v.addWidget(self.motion)
        v.addSpacing(20);v.addWidget(label('AUDIO',12,'#d5ac98',True))
        v.addWidget(label('La musique se règle depuis la barre en bas de chaque écran.\nLe volume et le mode muet sont mémorisés.',16))
        v.addSpacing(20);v.addWidget(label('DIFFICULTÉ EN COURS',12,'#d5ac98',True))
        self.options_level=QComboBox();self.options_level.addItems(list(DIFFICULTIES));self.options_level.setCurrentText('Normal')
        self.options_level.currentTextChanged.connect(lambda s:self.panel.difficulty.setCurrentText(s));v.addWidget(self.options_level)
        t=label('Le changement s’applique au prochain calcul de l’IA. Le réglage de difficulté est commun aux deux IA en mode spectateur.',13);t.setWordWrap(True);v.addWidget(t);v.addStretch();return page
    def build_credits(self):
        page,v=self.page('Derrière les lignes.','CRÉDITS')
        v.addWidget(label('PROJET ORIGINAL',11,'#d7aa94',True));v.addWidget(label('Resul Tektas',28,'#f8eafa',True))
        v.addSpacing(24);v.addWidget(label('MUSIQUE',11,'#d7aa94',True));v.addWidget(label('Empacotatron — Fupi',23,'#f8eafa'))
        v.addWidget(label('Versions menu et loop · CC0 1.0\nopengameart.org/content/empacotatron',14))
        v.addSpacing(24);v.addWidget(label('DIRECTION VISUELLE',11,'#d7aa94',True))
        t=label('Décor vectoriel animé, plateau en perspective et symboles lumineux.\nSources, licences et fichiers d’origine inclus dans le dossier du jeu.',16);t.setWordWrap(True);v.addWidget(t);v.addStretch();return page
    def build_pause(self):
        page,v=self.page('Faites une pause.','PARTIE SUSPENDUE')
        v.addStretch();v.addWidget(button('REPRENDRE   →',self.resume,True));v.addWidget(button('COMMENT JOUER',self.rules));v.addWidget(button('OPTIONS',self.options));v.addWidget(button('RETOUR AU MENU',self.menu));v.addStretch();return page
    def transition(self,page):
        if self.fade:self.fade.stop()
        old=self.stack.currentWidget()
        if old:old.setGraphicsEffect(None)
        self.stack.setCurrentWidget(page)
        if hasattr(self,'motion') and not self.motion.isChecked():return
        effect=QGraphicsOpacityEffect(page);page.setGraphicsEffect(effect)
        self.fade=QPropertyAnimation(effect,b'opacity',self);self.fade.setDuration(240);self.fade.setStartValue(.12);self.fade.setEndValue(1.);self.fade.setEasingCurve(QEasingCurve.OutCubic);self.fade.start()
    def suspend(self):
        self.panel.active=False;self.panel.invalidate();self.panel.render()
    def show_info(self,page):
        self.return_page=self.stack.currentWidget();self.return_active=self.panel.active;self.suspend();self.transition(page)
    def back(self):
        target=self.return_page or self.menu_page
        if target==self.panel:self.resume()
        elif target==self.pause_page:self.transition(self.pause_page)
        else:self.menu()
    def setup(self):self.suspend();self.return_page=self.menu_page;self.transition(self.setup_page)
    def rules(self):self.show_info(self.rules_page)
    def options(self):
        self.options_level.setCurrentText(self.panel.difficulty.currentText());self.show_info(self.options_page)
    def credits(self):self.show_info(self.credits_page)
    def pause_game(self):self.suspend();self.return_page=self.panel;self.transition(self.pause_page)
    def motion_changed(self):
        active=self.motion.isChecked();self.motion.setText('ANIMATIONS : '+('OUI' if active else 'NON'))
        if active:self.anim.start(50);self.hero.timer.start(33)
        else:self.anim.stop();self.hero.timer.stop()
    def refresh_sound(self):
        self.sound_button.setText('SON INDISPONIBLE' if not self.audio.ready else 'MUSIQUE : OFF' if self.audio.muted else 'MUSIQUE : ON')
        self.sound_button.setToolTip(self.audio.error if not self.audio.ready else 'Couper ou rétablir la musique')
    def toggle_sound(self):self.audio.toggle();self.settings.setValue('muted',self.audio.muted);self.refresh_sound()
    def change_volume(self,value):self.audio.set_volume(value);self.settings.setValue('volume',value)
    def start(self):
        p=self.panel;p.active=False;p.invalidate();index=self.mode.currentIndex()
        p.modes[0].setCurrentIndex(1 if index==2 else 0);p.modes[1].setCurrentIndex(0 if index==1 else 1)
        p.difficulty.setCurrentText(list(DIFFICULTIES)[self.level_group.checkedId()])
        p.active=True;p.new_game();self.transition(p);self.audio.play('game');self.refresh_sound()
    def menu(self):
        self.suspend();self.resume_button.setVisible(bool(self.panel.game.history) and not self.panel.game.result)
        self.transition(self.menu_page);self.audio.play('menu');self.refresh_sound()
    def resume(self):
        p=self.panel;p.active=True;p.paused=False;p.render();p.schedule();self.transition(p);self.audio.play('game');self.refresh_sound()
    def fullscreen(self):self.showNormal() if self.isFullScreen() else self.showFullScreen()
    def escape(self):
        current=self.stack.currentWidget()
        if current==self.panel:self.pause_game()
        elif current==self.pause_page:self.resume()
        elif current!=self.menu_page:self.back()
    def closeEvent(self,event):
        self.panel.invalidate();self.panel.pool.waitForDone();self.audio.close();self.settings.sync();event.accept()


if __name__=='__main__':
    app=QApplication(sys.argv);window=Window();window.show();sys.exit(app.exec_())
