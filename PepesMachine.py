import random
import json
import os
import sys
import time

REQUEST_SETTINGS = None

# Determine session id from environment or argv (subprocess mode)
SESSION_ID = os.environ.get('SESSION_ID') if os.environ.get('SESSION_ID') else (sys.argv[1] if len(sys.argv) > 1 else None)
BASE_DIR = os.path.dirname(__file__)
USER_DATA_DIR = os.path.join(BASE_DIR, 'user_data')
os.makedirs(USER_DATA_DIR, exist_ok=True)
DATA_FILE = os.path.join(USER_DATA_DIR, f"data_{SESSION_ID}.json") if SESSION_ID else os.path.join(BASE_DIR, "data.json")
PATTERN_FILE = os.path.join(USER_DATA_DIR, f"pattern_{SESSION_ID}.json") if SESSION_ID else os.path.join(BASE_DIR, "pattern.json")


def draw0(self,x,y,xdist,ydist):
    # print("Tile = Padrão Triangulos || rotation angle = 0, || Coordenates :",x+xdist+1,y+ydist+1,"|| color_fundo:",self.CorFundo, "color_padrão:",self.CorPattern)
    gridValues[x+xdist+1][y+ydist+1].append({
    "tile": "Padrao Triangulos",
    "rotation": 0,
    "coordinates": (x+xdist+1, y+ydist+1),
    "color_fundo": self.CorFundo,
    "color_padrao": self.CorPattern
})

def draw90(self,x,y,xdist,ydist):
    # print("Tile = Padrão Triangulos || rotation angle = 90, || Coordenates :",x+xdist+1,y+ydist+1,"|| color_fundo:",self.CorFundo, "color_padrão:",self.CorPattern)
    gridValues[x+xdist+1][y+ydist+1].append({
    "tile": "Padrao Triangulos",
    "rotation": 90,
    "coordinates": (x+xdist+1, y+ydist+1),
    "color_fundo": self.CorFundo,
    "color_padrao": self.CorPattern
})

def drawsquare_0(self,x,y,xdist,ydist):
    # print("Tile = Padrão Quadrado || rotation angle = 0 || Coordenates :",x+xdist+1,y+ydist+1,"|| color_fundo:",self.CorFundo, "color_padrão:",self.CorPattern)
    gridValues[x+xdist+1][y+ydist+1].append({
    "tile": "Padrao Quadrado",
    "rotation": 0,
    "coordinates": (x+xdist+1, y+ydist+1),
    "color_fundo": self.CorFundo,
    "color_padrao": self.CorPattern
})

def drawsquare_90(self,x,y,xdist,ydist):
    # print("Tile = Padrão Quadrado || rotation angle = 90 || Coordenates :",x+xdist+1,y+ydist+1,"|| color_fundo:",self.CorFundo, "color_padrão:",self.CorPattern)
    gridValues[x+xdist+1][y+ydist+1].append({
    "tile": "Padrao Quadrado",
    "rotation": 90,
    "coordinates": (x+xdist+1, y+ydist+1),
    "color_fundo": self.CorFundo,
    "color_padrao": self.CorPattern
})

def drawsquare_180(self,x,y,xdist,ydist):
    # print("Tile = Padrão Quadrado || rotation angle = 180 || Coordenates :",x+xdist+1,y+ydist+1,"|| color_fundo:",self.CorFundo, "color_padrão:",self.CorPattern)
    gridValues[x+xdist+1][y+ydist+1].append({
    "tile": "Padrao Quadrado",
    "rotation": 180,
    "coordinates": (x+xdist+1, y+ydist+1),
    "color_fundo": self.CorFundo,
    "color_padrao": self.CorPattern
})

def drawsquare_270(self,x,y,xdist,ydist):
    # print("Tile = Padrão Quadrado || rotation angle = 270, || Coordenates :",x+xdist+1,y+ydist+1,"|| color_fundo:",self.CorFundo, "color_padrão:",self.CorPattern)
    gridValues[x+xdist+1][y+ydist+1].append({
    "tile": "Padrao Quadrado",
    "rotation": 270,
    "coordinates": (x+xdist+1, y+ydist+1),
    "color_fundo": self.CorFundo,
    "color_padrao": self.CorPattern
})

class PatternStyles:
    def __init__(self,CorFundo,CorPattern,Filletes,patternEssencials,PepeQuad1,PepeQuad2):
        self.CorPattern = CorPattern
        self.CorFundo = CorFundo
        self.Filletes = Filletes
        self.patternEssencials = patternEssencials
        self.divLarg = patternEssencials[0]
        self.divAlt = patternEssencials[1]
        self.largTela = patternEssencials[2]
        self.altTela = patternEssencials[3]
        self.PepeQuad1 = PepeQuad1
        self.PepeQuad2 = PepeQuad2
    def aleluia_triangulos(self):
        random_pattern = random.randint(1,7)
        x,y,sizeX,sizeY = self.Filletes[-1]
        Xtimes = int(sizeX / (self.largTela/self.divLarg))
        Ytimes = int(sizeY / (self.altTela/self.divAlt))
        if random_pattern == 1:
            random_start = random.randint(0,1)
            for ydist in range(Ytimes):
                for xdist in range(Xtimes):
                    if random_start == 0:
                        draw0(self,x,y,xdist,ydist)
                    else:
                        draw90(self,x,y,xdist,ydist)
        elif random_pattern == 2:
            for ydist in range(Ytimes):
                for xdist in range(Xtimes):
                    random_number = random.randint(0,1)
                    if random_number == 0:
                        draw0(self,x,y,xdist,ydist)
                    else :
                        draw90(self,x,y,xdist,ydist)
        elif random_pattern== 3:
            random_start = random.randint(0,1)
            for ydist in range(Ytimes):
                for xdist in range(Xtimes):
                    if xdist%2 == random_start:
                        draw90(self,x,y,xdist,ydist)
                    else:
                        draw0(self,x,y,xdist,ydist)
        elif random_pattern== 4:
            random_start = random.randint(0,1)
            for ydist in range(Ytimes):
                for xdist in range(Xtimes):
                    if ydist%2 == random_start:
                        draw90(self,x,y,xdist,ydist)
                    else:
                        draw0(self,x,y,xdist,ydist)
        elif random_pattern== 5:
            random_start = random.randint(0,1)
            for ydist in range(Ytimes):
                for xdist in range(Xtimes):
                    if ydist%2 == 0:
                        if xdist%2== random_start:
                            draw90(self,x,y,xdist,ydist)
                        else:
                            draw0(self,x,y,xdist,ydist)
                    else:
                        if xdist%2== random_start:
                            draw0(self,x,y,xdist,ydist)
                        else:
                            draw90(self,x,y,xdist,ydist)
        elif random_pattern== 6:
            for ydist in range(Ytimes):
                for xdist in range(Xtimes):
                    if ydist%2 == 0:
                        if xdist%4 <= 1:
                            draw0(self,x,y,xdist,ydist)
                        else:
                            draw90(self,x,y,xdist,ydist)
                    else:
                        if xdist%4 <= 1:
                            draw90(self,x,y,xdist,ydist)
                        else:
                            draw0(self,x,y,xdist,ydist)
        elif random_pattern== 7:
            for ydist in range(Ytimes):
                for xdist in range(Xtimes):
                    if ydist%4 < 2 :
                        if xdist%4 < 2:
                            draw0(self,x,y,xdist,ydist)
                        else:
                            draw90(self,x,y,xdist,ydist)
                    else:
                        if xdist%4 < 2:
                            draw90(self,x,y,xdist,ydist)
                        else:
                            draw0(self,x,y,xdist,ydist)
    def aleluia_quadrados(self):
        random_pattern = random.randint(1,14)
        x,y,sizeX,sizeY = self.Filletes[-1]
        Xtimes = int(sizeX / (self.largTela/self.divLarg))
        Ytimes = int(sizeY / (self.altTela/self.divAlt))
        
        if random_pattern == 1:
            times = 0
            for ydist in range(Ytimes):
                for xdist in range(Xtimes):
                    if times%4==0:
                        drawsquare_0(self,x,y,xdist,ydist)
                    elif times%4==1:
                        drawsquare_90(self,x,y,xdist,ydist)
                    elif times%4==2:
                        drawsquare_180(self,x,y,xdist,ydist)
                    elif times%4==3:
                        drawsquare_270(self,x,y,xdist,ydist)
                    times = times + 1
        
        if random_pattern == 2:
            for ydist in range(Ytimes):
                for xdist in range(Xtimes):
                    drawsquare_0(self,x,y,xdist,ydist)
                    
        if random_pattern == 3:
            for ydist in range(Ytimes):
                for xdist in range(Xtimes):
                    drawsquare_90(self,x,y,xdist,ydist)
                    
        if random_pattern == 4:
            times = 0
            for ydist in range(Ytimes):
                for xdist in range(Xtimes):
                    if ydist%2== 0:
                        if xdist%2 == 0:
                            drawsquare_0(self,x,y,xdist,ydist)
                        else:
                            drawsquare_90(self,x,y,xdist,ydist)
                    else:
                        if xdist%2 == 0:
                            drawsquare_270(self,x,y,xdist,ydist)
                        else:
                            drawsquare_180(self,x,y,xdist,ydist)
                            
        if random_pattern == 5:
            times = 0
            for ydist in range(Ytimes):
                for xdist in range(Xtimes):
                    if ydist%2== 0:
                        if xdist%2 == 0:
                            drawsquare_0(self,x,y,xdist,ydist)
                        else:
                            drawsquare_90(self,x,y,xdist,ydist)
                    else:
                        if xdist%2 == 0:
                            drawsquare_180(self,x,y,xdist,ydist)
                        else:
                            drawsquare_270(self,x,y,xdist,ydist)
        
        if random_pattern == 6:
            times = 0
            for ydist in range(Ytimes):
                for xdist in range(Xtimes):
                    if ydist%2== 0:
                        if xdist%2 == 0:
                            drawsquare_180(self,x,y,xdist,ydist)
                        else:
                            drawsquare_0(self,x,y,xdist,ydist)
                    else:
                        if xdist%2 == 0:
                            drawsquare_90(self,x,y,xdist,ydist)
                        else:
                            drawsquare_270(self,x,y,xdist,ydist)
                            
        if random_pattern == 7:
            times = 0
            for ydist in range(Ytimes):
                for xdist in range(Xtimes):
                    if ydist%2== 0:
                        if xdist%2 == 0:
                            drawsquare_180(self,x,y,xdist,ydist)
                        else:
                            drawsquare_0(self,x,y,xdist,ydist)
                    else:
                        if xdist%2 == 0:
                            drawsquare_0(self,x,y,xdist,ydist)
                        else:
                            drawsquare_180(self,x,y,xdist,ydist)
                            
        if random_pattern == 8:
            for ydist in range(Ytimes):
                for xdist in range(Xtimes):
                    if xdist%4==0:
                        drawsquare_90(self,x,y,xdist,ydist)
                    elif xdist%4==1:
                        drawsquare_270(self,x,y,xdist,ydist)
                    elif xdist%4==2:
                        drawsquare_270(self,x,y,xdist,ydist)
                    elif xdist%4==3:
                        drawsquare_90(self,x,y,xdist,ydist)
                        
        if random_pattern == 9:
            for ydist in range(Ytimes):
                for xdist in range(Xtimes):
                    if ydist%4==0:
                        if xdist%4==0:
                            drawsquare_0(self,x,y,xdist,ydist)
                        elif xdist%4==1:
                            drawsquare_0(self,x,y,xdist,ydist)
                        elif xdist%4==2:
                            drawsquare_270(self,x,y,xdist,ydist)
                        elif xdist%4==3:
                            drawsquare_90(self,x,y,xdist,ydist)
                    if ydist%4==1:
                        if xdist%4==0:
                            drawsquare_180(self,x,y,xdist,ydist)
                        elif xdist%4==1:
                            drawsquare_180(self,x,y,xdist,ydist)
                        elif xdist%4==2:
                            drawsquare_270(self,x,y,xdist,ydist)
                        elif xdist%4==3:
                            drawsquare_90(self,x,y,xdist,ydist)
                    if ydist%4==2:
                        if xdist%4==0:
                            drawsquare_270(self,x,y,xdist,ydist)
                        elif xdist%4==1:
                            drawsquare_90(self,x,y,xdist,ydist)
                        elif xdist%4==2:
                            drawsquare_0(self,x,y,xdist,ydist)
                        elif xdist%4==3:
                            drawsquare_0(self,x,y,xdist,ydist)
                    if ydist%4==3:
                        if xdist%4==0:
                            drawsquare_270(self,x,y,xdist,ydist)
                        elif xdist%4==1:
                            drawsquare_90(self,x,y,xdist,ydist)
                        elif xdist%4==2:
                            drawsquare_180(self,x,y,xdist,ydist)
                        elif xdist%4==3:
                            drawsquare_180(self,x,y,xdist,ydist)
        
        if random_pattern == 10:
            for ydist in range(Ytimes):
                for xdist in range(Xtimes):
                    if ydist%4==0:
                        if xdist%4==0:
                            drawsquare_90(self,x,y,xdist,ydist)
                        elif xdist%4==1:
                            drawsquare_90(self,x,y,xdist,ydist)
                        elif xdist%4==2:
                            drawsquare_0(self,x,y,xdist,ydist)
                        elif xdist%4==3:
                            drawsquare_180(self,x,y,xdist,ydist)
                    if ydist%4==1:
                        if xdist%4==0:
                            drawsquare_270(self,x,y,xdist,ydist)
                        elif xdist%4==1:
                            drawsquare_270(self,x,y,xdist,ydist)
                        elif xdist%4==2:
                            drawsquare_0(self,x,y,xdist,ydist)
                        elif xdist%4==3:
                            drawsquare_180(self,x,y,xdist,ydist)
                    if ydist%4==2:
                        if xdist%4==0:
                            drawsquare_0(self,x,y,xdist,ydist)
                        elif xdist%4==1:
                            drawsquare_180(self,x,y,xdist,ydist)
                        elif xdist%4==2:
                            drawsquare_90(self,x,y,xdist,ydist)
                        elif xdist%4==3:
                            drawsquare_90(self,x,y,xdist,ydist)
                    if ydist%4==3:
                        if xdist%4==0:
                            drawsquare_0(self,x,y,xdist,ydist)
                        elif xdist%4==1:
                            drawsquare_180(self,x,y,xdist,ydist)
                        elif xdist%4==2:
                            drawsquare_270(self,x,y,xdist,ydist)
                        elif xdist%4==3:
                            drawsquare_270(self,x,y,xdist,ydist)
        
        if random_pattern == 11:
            for ydist in range(Ytimes):
                for xdist in range(Xtimes):
                    if ydist%2==0:
                        if xdist%2==0:
                            drawsquare_0(self,x,y,xdist,ydist)
                        elif xdist%2==1:
                            drawsquare_180(self,x,y,xdist,ydist)
                    if ydist%2==1:
                        drawsquare_90(self,x,y,xdist,ydist)
                        
        if random_pattern == 12:
            for ydist in range(Ytimes):
                for xdist in range(Xtimes):
                    if ydist%8==0:
                        if xdist%8==0:
                            drawsquare_0(self,x,y,xdist,ydist)
                        elif xdist%8==1:
                            drawsquare_180(self,x,y,xdist,ydist)
                        elif xdist%8==2:
                            drawsquare_0(self,x,y,xdist,ydist)
                        elif xdist%8==3:
                            drawsquare_180(self,x,y,xdist,ydist)
                        elif xdist%8==4:
                            drawsquare_180(self,x,y,xdist,ydist)
                        elif xdist%8==5:
                            drawsquare_0(self,x,y,xdist,ydist)
                        elif xdist%8==6:
                            drawsquare_180(self,x,y,xdist,ydist)
                        elif xdist%8==7:
                            drawsquare_0(self,x,y,xdist,ydist)
                    elif ydist%8==1:
                        if xdist%8==0:
                            drawsquare_90(self,x,y,xdist,ydist)
                        elif xdist%8==1:
                            drawsquare_90(self,x,y,xdist,ydist)
                        elif xdist%8==2:
                            drawsquare_90(self,x,y,xdist,ydist)
                        elif xdist%8==3:
                            drawsquare_90(self,x,y,xdist,ydist)
                        elif xdist%8==4:
                            drawsquare_270(self,x,y,xdist,ydist)
                        elif xdist%8==5:
                            drawsquare_270(self,x,y,xdist,ydist)
                        elif xdist%8==6:
                            drawsquare_270(self,x,y,xdist,ydist)
                        elif xdist%8==7:
                            drawsquare_270(self,x,y,xdist,ydist)
                    elif ydist%8==2:
                        if xdist%8==0:
                            drawsquare_0(self,x,y,xdist,ydist)
                        elif xdist%8==1:
                            drawsquare_180(self,x,y,xdist,ydist)
                        elif xdist%8==2:
                            drawsquare_0(self,x,y,xdist,ydist)
                        elif xdist%8==3:
                            drawsquare_180(self,x,y,xdist,ydist)
                        elif xdist%8==4:
                            drawsquare_180(self,x,y,xdist,ydist)
                        elif xdist%8==5:
                            drawsquare_0(self,x,y,xdist,ydist)
                        elif xdist%8==6:
                            drawsquare_180(self,x,y,xdist,ydist)
                        elif xdist%8==7:
                            drawsquare_0(self,x,y,xdist,ydist)
                    elif ydist%8==3:
                        if xdist%8==0:
                            drawsquare_270(self,x,y,xdist,ydist)
                        elif xdist%8==1:
                            drawsquare_90(self,x,y,xdist,ydist)
                        elif xdist%8==2:
                            drawsquare_90(self,x,y,xdist,ydist)
                        elif xdist%8==3:
                            drawsquare_270(self,x,y,xdist,ydist)
                        elif xdist%8==4:
                            drawsquare_90(self,x,y,xdist,ydist)
                        elif xdist%8==5:
                            drawsquare_270(self,x,y,xdist,ydist)
                        elif xdist%8==6:
                            drawsquare_270(self,x,y,xdist,ydist)
                        elif xdist%8==7:
                            drawsquare_90(self,x,y,xdist,ydist)
                    elif ydist%8==4:
                        if xdist%8==0:
                            drawsquare_90(self,x,y,xdist,ydist)
                        elif xdist%8==1:
                            drawsquare_270(self,x,y,xdist,ydist)
                        elif xdist%8==2:
                            drawsquare_270(self,x,y,xdist,ydist)
                        elif xdist%8==3:
                            drawsquare_90(self,x,y,xdist,ydist)
                        elif xdist%8==4:
                            drawsquare_270(self,x,y,xdist,ydist)
                        elif xdist%8==5:
                            drawsquare_90(self,x,y,xdist,ydist)
                        elif xdist%8==6:
                            drawsquare_90(self,x,y,xdist,ydist)
                        elif xdist%8==7:
                            drawsquare_270(self,x,y,xdist,ydist)
                    elif ydist%8==5:
                        if xdist%8==0:
                            drawsquare_180(self,x,y,xdist,ydist)
                        elif xdist%8==1:
                            drawsquare_0(self,x,y,xdist,ydist)
                        elif xdist%8==2:
                            drawsquare_180(self,x,y,xdist,ydist)
                        elif xdist%8==3:
                            drawsquare_0(self,x,y,xdist,ydist)
                        elif xdist%8==4:
                            drawsquare_0(self,x,y,xdist,ydist)
                        elif xdist%8==5:
                            drawsquare_180(self,x,y,xdist,ydist)
                        elif xdist%8==6:
                            drawsquare_0(self,x,y,xdist,ydist)
                        elif xdist%8==7:
                            drawsquare_180(self,x,y,xdist,ydist)
                    elif ydist%8==6:
                        if xdist%8==0:
                            drawsquare_90(self,x,y,xdist,ydist)
                        elif xdist%8==1:
                            drawsquare_90(self,x,y,xdist,ydist)
                        elif xdist%8==2:
                            drawsquare_90(self,x,y,xdist,ydist)
                        elif xdist%8==3:
                            drawsquare_90(self,x,y,xdist,ydist)
                        elif xdist%8==4:
                            drawsquare_270(self,x,y,xdist,ydist)
                        elif xdist%8==5:
                            drawsquare_270(self,x,y,xdist,ydist)
                        elif xdist%8==6:
                            drawsquare_270(self,x,y,xdist,ydist)
                        elif xdist%8==7:
                            drawsquare_270(self,x,y,xdist,ydist)
                    elif ydist%8==7:
                        if xdist%8==0:
                            drawsquare_180(self,x,y,xdist,ydist)
                        elif xdist%8==1:
                            drawsquare_0(self,x,y,xdist,ydist)
                        elif xdist%8==2:
                            drawsquare_180(self,x,y,xdist,ydist)
                        elif xdist%8==3:
                            drawsquare_0(self,x,y,xdist,ydist)
                        elif xdist%8==4:
                            drawsquare_0(self,x,y,xdist,ydist)
                        elif xdist%8==5:
                            drawsquare_180(self,x,y,xdist,ydist)
                        elif xdist%8==6:
                            drawsquare_0(self,x,y,xdist,ydist)
                        elif xdist%8==7:
                            drawsquare_180(self,x,y,xdist,ydist)
        if random_pattern == 13:
            for ydist in range(Ytimes):
                for xdist in range(Xtimes):
                    if ydist%4== 0:
                        if xdist%2 == 0:
                            drawsquare_90(self,x,y,xdist,ydist)
                        else:
                            drawsquare_270(self,x,y,xdist,ydist)
                    elif ydist%4 == 1:
                        if xdist%2 == 0:
                            drawsquare_90(self,x,y,xdist,ydist)
                        else:
                            drawsquare_270(self,x,y,xdist,ydist)
                    elif ydist%4 == 2:
                        if xdist%2 == 0:
                            drawsquare_270(self,x,y,xdist,ydist)
                        else:
                            drawsquare_90(self,x,y,xdist,ydist)
                    elif ydist%4 == 3:
                        drawsquare_270(self,x,y,xdist,ydist)
        
        if random_pattern == 14:
            for ydist in range(Ytimes):
                for xdist in range(Xtimes):
                    if ydist%4== 0:
                        drawsquare_90(self,x,y,xdist,ydist)
                        
                    elif ydist%4 == 1:
                        if xdist%2 == 0:
                            drawsquare_270(self,x,y,xdist,ydist)
                        else:
                            drawsquare_90(self,x,y,xdist,ydist)
                    elif ydist%4 == 2:
                        drawsquare_90(self,x,y,xdist,ydist)
                    elif ydist%4 == 3:
                        if xdist%2 == 0:
                            drawsquare_90(self,x,y,xdist,ydist)
                        else:
                            drawsquare_270(self,x,y,xdist,ydist)
                    

def get_canvas_dimensions():
    try:
        if REQUEST_SETTINGS:
            data = REQUEST_SETTINGS
            altTela = int(data.get("canvas_height", 500))
            largTela = int(data.get("canvas_width", 500))
            altTela = max(100, min(1000000, altTela))
            largTela = max(100, min(1000000, largTela))
        else:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                altTela = int(data.get("canvas_height", 500))
                largTela = int(data.get("canvas_width", 500))
                altTela = max(100, min(1000000, altTela))
                largTela = max(100, min(1000000, largTela))
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        altTela = 500
        largTela = 500
    canvas_dividend = 50
    divLarg = int((largTela/canvas_dividend)/2)
    divAlt = int((altTela/canvas_dividend)/2)
    return altTela, largTela, divAlt, divLarg


def get_final_pepecolors():
    FinalPepeColors = {}
    All_Colors = []
    try:
        if REQUEST_SETTINGS:
            data = REQUEST_SETTINGS
        else:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    # Support both legacy string format ("#hex" or "off") and new object format:
    # button_n: { state: "on"|"off", color: "#hex" }
    for key, value in data.items():
        if not key.startswith("button_"):
            continue
        # new object format
        if isinstance(value, dict):
            state = value.get("state")
            color = value.get("color")
            if state == "on" and color:
                All_Colors.append(color)
        else:
            # legacy string format
            if isinstance(value, str) and value != "off":
                All_Colors.append(value)
    if not All_Colors:
        FinalPepeColors[0] = "black"
        FinalPepeColors[1] = "white"
        return FinalPepeColors
    selected_colors = random.sample(All_Colors, len(All_Colors))
    for index, color in enumerate(selected_colors):
        FinalPepeColors[index] = color
    if len(FinalPepeColors) < 2:
        additional_color = random.choice(["black", "white"])
        FinalPepeColors[len(FinalPepeColors)] = additional_color
    return FinalPepeColors


canIgoback = False
canIgobackintoFuture = False
gofoward = True
isdrawn = 0

altTela,largTela,divAlt,divLarg = get_canvas_dimensions()
Filletes = []
ADN = []
FinalPepeColors = get_final_pepecolors()

base_RandomNum = [1, 2]
def get_knob_value():
    try:
        if REQUEST_SETTINGS:
            return int(REQUEST_SETTINGS.get("knob_down", 0))
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            return int(data.get("knob_down", 0))
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return 0
    return 0


def set_new_colors():
    global FinalPepeColors
    FinalPepeColors = get_final_pepecolors()

def set_ADN_to_nothing():
    global ADN
    ADN = []

class PepeAI:
    def __init__(self):
        self.GetColors()
        self.GetPatternShape()
    def GetColors(self):
        self.pepeCores = FinalPepeColors
        self.colorFundo = random.choice(self.pepeCores)
        self.colorPattern = random.choice(self.pepeCores)
        while self.colorPattern == self.colorFundo:
            self.colorPattern = random.choice(self.pepeCores)
            self.colorFundo = random.choice(self.pepeCores)
    def GetPatternShape(self):
        try:
            if REQUEST_SETTINGS:
                data = REQUEST_SETTINGS
                switch_value = data.get("switch", None)
                slider_value = int(data.get("slider", 50))
            else:
                with open(DATA_FILE, "r") as f:
                    data = json.load(f)
                    switch_value = data.get("switch", None)
                    slider_value = int(data.get("slider", 50))
            if switch_value == "left":
                self.ShapeComand = "aleluia_quadrados"
            elif switch_value == "right":
                self.ShapeComand = "aleluia_triangulos"
            elif switch_value == "center":
                # Keep it simple: random choice weighted by slider (original code had an unclear block)
                if slider_value <= 50:
                    # bias toward squares
                    self.ShapeComand = random.choice(["aleluia_quadrados", "aleluia_triangulos"])
                else:
                    self.ShapeComand = random.choice(["aleluia_triangulos", "aleluia_quadrados"])
            else:
                self.ShapeComand = random.choice(("aleluia_triangulos", "aleluia_quadrados"))
            return
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            self.ShapeComand = random.choice(("aleluia_triangulos", "aleluia_quadrados"))


class PepeDrawer:
    def __init__(self,CorFundo,CorPattern,PepeQuad1,PepeQuad2,ShapeComand):
        self.CorFundo = CorFundo
        self.CorPattern = CorPattern
        self.FirstX,self.FirstY = PepeQuad1
        self.SecX,self.SecY = PepeQuad2
        self.ShapeComand = ShapeComand      
        self.altTela = altTela
        self.largTela = largTela
        self.divAlt = divAlt
        self.divLarg = divLarg
    def startbyFilette(self):        
        if self.SecX < self.FirstX:
            self.SizeX = (self.FirstX - self.SecX) 
            self.FirstX = self.SecX
        else:
            self.SizeX = (self.SecX - self.FirstX) 
        if self.SecY < self.FirstY:
            self.SizeY = (self.FirstY - self.SecY) 
            self.FirstY = self.SecY
        else:
            self.SizeY = (self.SecY - self.FirstY)     
        self.RealDirectionX = self.SizeX * (self.largTela/self.divLarg)
        self.RealDirectionY = self.SizeY * (self.altTela/self.divAlt)
        Filletes.append((self.FirstX,self.FirstY,self.RealDirectionX,self.RealDirectionY))
        self.DrawPattern()
    def DrawPattern(self):
        patternEssencials = [self.divLarg,self.divAlt,self.largTela,self.altTela]
        patrao = PatternStyles(self.CorFundo,self.CorPattern,Filletes,patternEssencials,(self.FirstX,self.FirstY),(self.SecX,self.SecY))
        if self.ShapeComand == "aleluia_quadrados":
            patrao.aleluia_quadrados()    
        elif self.ShapeComand == "aleluia_triangulos":
            patrao.aleluia_triangulos()      

def check_for_touching_colors(self, ADN, NewPepe, a, y, NewNum):
    tester_i = 0
    ll = len(ADN)
    touched_colors = []
    if len(FinalPepeColors) < 4:
        return NewPepe
    while tester_i < ll:
        cor_cobaia, cor2_cobaia, (x1, y1), (x2, y2), pattern_cobaia = ADN[tester_i]
        if (x2 >= self.Xpoints[a-1] and x1 <= self.Xpoints[a] and 
            (y1 < y + NewNum and y + NewNum > y1)):
            touched_colors.append((cor_cobaia, cor2_cobaia, pattern_cobaia))
        tester_i += 1
    nbr_touched_colors = len(touched_colors)
    cancel_operation = 0
    max_attempts = 500
    while cancel_operation < max_attempts:
        if nbr_touched_colors == 0:
            return NewPepe
        for color_pair in touched_colors:
            if (NewPepe.colorFundo in color_pair or NewPepe.colorPattern in color_pair):
                NewPepe = PepeAI()
                break
        else:
            break
        cancel_operation += 1
    return NewPepe

class StartPepeFunction:
    def __init__(self):
        self.Xpoints = [] 
        set_ADN_to_nothing()
        self.altTela, self.largTela, self.divAlt, self.divLarg = get_canvas_dimensions()
        # Initialize gridValues here
        global gridValues
        gridValues = [[[] for _ in range(self.divAlt + 2)] for _ in range(self.divLarg + 2)]
        print("\nPadrão com ", self.divAlt*self.divLarg, " mosaicos || largura:", self.largTela, "altura:", self.altTela, "\n")
        self.start()
    def start(self):
        knob_value = get_knob_value()
        RandomNum = [num + knob_value for num in base_RandomNum]
        x = 0
        while x < self.divLarg:
            self.Xpoints.append(x)
            NewNum = random.choice(RandomNum)
            x = x + NewNum
        self.Xpoints.append(self.divLarg)
        self.rowNumber = len(self.Xpoints)
        a = 0
        while a < self.rowNumber-1:
            a = a + 1
            self.Ypoints = []
            y = 0
            while y < self.divAlt:
                self.Ypoints.append(y)
                NewNum = random.choice(RandomNum)
                if y + NewNum > self.divAlt:
                    NewNum = self.divAlt - y
                NewPepe = PepeAI()
                NewPepe = check_for_touching_colors(self,ADN,NewPepe,a,y,NewNum)
                newPepitos = PepeDrawer(NewPepe.colorFundo,NewPepe.colorPattern,(self.Xpoints[a-1],y),(self.Xpoints[a],y+NewNum),NewPepe.ShapeComand)
                newPepitos.startbyFilette()
                ADN.append((NewPepe.colorFundo,NewPepe.colorPattern,(self.Xpoints[a-1],y),(self.Xpoints[a],y+NewNum),newPepitos.ShapeComand))
                y = y + NewNum

def draw_pepe(write_to_file=True):
    set_new_colors()
    StartPepeFunction()
    # Collect all non-empty grid values
    pattern_data = []
    for i, col in enumerate(gridValues):
        for j, cell in enumerate(col):
            if cell:  # Only add non-empty cells
                for entry in cell:
                    entry_with_coords = dict(entry)
                    entry_with_coords["grid_x"] = i
                    entry_with_coords["grid_y"] = j
                    # Remove 'coordinates' tuple to avoid duplication (optional)
                    if "coordinates" in entry_with_coords:
                        del entry_with_coords["coordinates"]
                    pattern_data.append(entry_with_coords)
    if write_to_file:
        # Ensure user_data directory exists (should already)
        os.makedirs(os.path.dirname(PATTERN_FILE), exist_ok=True)
        with open(PATTERN_FILE, "w") as f:
            json.dump(pattern_data, f, indent=2)
        return None
    else:
         # Return the pattern data to caller (in-memory)
         return pattern_data


def generate(settings=None):
    """
    Minimal adapter for Flask:
      - settings: dict (same structure previously stored in data.json)
      - returns: pattern_data (list of tile dicts)
    """
    global REQUEST_SETTINGS, gridValues, Filletes, ADN, FinalPepeColors, canIgoback, canIgobackintoFuture, gofoward, isdrawn
    # Reset any global state we reuse
    REQUEST_SETTINGS = settings or {}
    Filletes = []
    ADN = []
    set_new_colors()
    # Ensure gridValues exists and is cleared by StartPepeFunction, but set to empty here
    gridValues = {}
    # Run generator but ask it to return data instead of writing files
    pattern = draw_pepe(write_to_file=False)
    # Clean up / reset REQUEST_SETTINGS to avoid bleed
    REQUEST_SETTINGS = None
    return pattern

if __name__ == '__main__':
    # When run as a script, produce files for backward compatibility
    global gridValues
    gridValues = {}
    # If the script is invoked directly as a subprocess, write per-session pattern file as configured above
    # Ensure any previous status markers for this session are cleared
    try:
        if SESSION_ID:
            run_marker = os.path.join(USER_DATA_DIR, f"generate_{SESSION_ID}.running")
            done_marker = os.path.join(USER_DATA_DIR, f"generate_{SESSION_ID}.done")
        else:
            run_marker = os.path.join(BASE_DIR, 'generate.running')
            done_marker = os.path.join(BASE_DIR, 'generate.done')
        # remove existing done marker
        if os.path.exists(done_marker):
            os.remove(done_marker)
    except Exception:
        pass

    try:
        draw_pepe(write_to_file=True)
        # On successful completion, touch done marker and remove running marker
        try:
            with open(done_marker, 'w') as f:
                f.write(str(time.time()))
        except Exception:
            pass
        try:
            if os.path.exists(run_marker):
                os.remove(run_marker)
        except Exception:
            pass
    except Exception:
        # On failure, try to remove running marker so server won't think it's stuck
        try:
            if os.path.exists(run_marker):
                os.remove(run_marker)
        except Exception:
            pass


# Print all non-empty grid values in a readable way
#for i, col in enumerate(gridValues):
#    for j, cell in enumerate(col):
#        if cell:  # Only print non-empty cells
#            print(f"gridValues[{i}][{j}]:")
#            for entry in cell:
#                print(entry)