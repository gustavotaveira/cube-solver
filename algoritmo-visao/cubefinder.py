#!/usr/bin/python
#import cv

#apenas ajustes para executar a imagem do esp32cam e inclusao da url de stream http://192.168.1.104:81/stream
#incluido tambem os códigos para solucionar o cubo
import cv2
from math import pi,atan2,sqrt
from numpy import matrix
from time import time
import numpy as np
import kociemba        
import threading
import serial
import time
#----------------------------------------------------------------------------------------
#distancia entre 2 pontos no espaço HSV
def ptdstw(p1,p2):
    #test if hue is reliable measurement
    if p1[1]<100 or p2[1]<100:
        #hue measurement will be unreliable. Probably white stickers are present
        #leave this until end
        return 300.0+abs(p1[0]-p2[0])
    else:
        return abs(p1[0]-p2[0])

#----------------------------------------------------------------------------------------        

#distancia entre 2 pontos no espaço RGB
#cada ponto tem 3 coordenadas com valores de de 0 a 255
def ptdst3(p1,p2):
    dist=sqrt((p1[0]-p2[0])*(p1[0]-p2[0])+(p1[1]-p2[1])*(p1[1]-p2[1])+(p1[2]-p2[2])*(p1[2]-p2[2]))
    #se a cor do sticker estiver muito desbotada/palida (ou seja se todas as suas coordenadas RGB forem muito altas),
    # sera dificil identificar sua cor base, pois a saturacao estara muito baixa.
    #Assim incrementamos a distancia encontrada para ser maior e potencialmente essa cor do sticker se a ultima a ser considerada
    if (p1[0]>245 and p1[1]>245 and p1[2]>245):
        #the sticker could potentially be washed out. Lets leave it to the end
        dist=dist+300.0
    return dist

#----------------------------------------------------------------------------------------
#compfaces encontra o deslocamento medio dos 4 pontos da face antiga detectada (f2) em relação a face nova detectada(f1)
def compfaces(f1,f2):
    #total distance
    totd=0
    for p1 in f1:
        #aqui usa um valor relativamente alto que é arbitrario, é usado apenas para encontrarmos o menor valor de distancia entre os
        #pontos da face atual f1 e a face detectada anteriormente f2
        #minimal distance
        mind=10000 
        
        for p2 in f2:
            d=distanciaEuclidiana(p1,p2)
            #se a distancia entre os pontos p1 e p2 é menor que a distancia minima
            #entao a distancia entre os pontos se torna a distancia minima
            #desenhando geometricamente um sistema de coordenadas sobreposto a outro so que deslocado um pouco na diagonal, foi observado
            #que a menor distancia sempre sera do ponto na face anterior detectada f2 ate o mesmo ponto na proxima face detectada f1
            if d < mind:
                mind=d
        #encontrou a menor distancia (variavel mind) para o p1 da iteração atual? então adicione a distancia total e va para o proximo ponto da nova face detectada f1  
        totd += mind
    #ao encontrar todas as distancias entre os pontos da face anterior e nova, e somado tudo temos a distancia total 'totd'.
    #dividindo por 4 temos uma media aritmetica do deslocamento dos pontos que houve da face anterior para a face mais nova e atual detectada
    return totd/4

#----------------------------------------------------------------------------------------
#calcula e retorna o ponto medio entre dois pontos fornecidos ( (x1 + x2) / 2, (y1 + y2) / 2 )
#verifica o ponto medio(meio) da reta definida pelos dois pontos informados.
def avg(p1,p2):
    return (0.5*p1[0]+0.5*p2[0], 0.5*p1[1]+0.5*p2[1])

#----------------------------------------------------------------------------------------
#verifica se as coordenadas dos pontos t1 e t2 estao dentro de uma distancia prederminada.
def areclose(t1,t2,t):
    #is t1 close to t2 within t?
    return abs(t1[0]-t2[0])<t and abs(t1[1]-t2[1])<t

#----------------------------------------------------------------------------------------

#ordena os pontos no horario com base no angulo do vetor do ponto medio ate o ponto, em relacao ao eixo horizontal
#os pontos aqui tratados se tratam do 4 cantos do cubo de Rubik com base no sistema de coordenadas (grid) detectado no detectionMode.
#p1 = (0,0) origem do sistema de coordenadas
#p2 = (1,0) ponto final do eixo x
#p3 = (0,1) ponto final do eixo y
#p4 = (1,1) canto diagonal oposto a origem
#é interessante observar como a ordenacao do atan2 funciona, o 2 quadrante é o quadrante que tem os
#maiores angulos positivos, o 1 quadrante é o quadrante que tem os menores angulos positivos
#o 4 quadrante é o quadrante que tem os menores angulos negativos, e o 4 quadrante é o quadrante
#que tem os maiores angulos negativos.
#atan2 considera o sinal das coordenadas y e x para definir os quadrantes dos angulos
#e assim se estiverem no 2 quadrante, soma 180 para encontrar o angulo complementar
#se estiver no 3 quadrante, subtrai 180 para encontrar o angulo complementar
#por padrao o angulo positivo vai de 0 a 180 no sentido antihorario
#por padrao o angulo negativo vai de 0 a -180 no sentido horario
#os angulos obtidos sao em radianos e assim é feita a ordenação inversa
#no sentido horario do maior angulo para o menor:
#2 quadrante, 1 quadrante, 4 quadrante, 3 quadrante
#logo o primeiro ponto da ordenacao sempre sera o superior esquerdo e seguindo a partir
#dai no sentido horario
def winded(p1,p2,p3,p4):
    #return the pts in correct order based on quadrants
    #ponto medio de quatro pontos (calcula o centro do quadrilatero formado pelos 4 pontos)
    #o ponto medio de um poligono pode ser entendido como centro de massa do mesmo, nesse caso o poligono é um quadrilatero representando a face do cubo
    #o resultado sera (1/2, 1/2) para o caso dos pontos acima descritos
    avg=(0.25*(p1[0]+p2[0]+p3[0]+p4[0]),0.25*(p1[1]+p2[1]+p3[1]+p4[1])) 
    
    #cria uma lista de tupla (angulo, ponto) onde o angulo é arctan do ponto em relacao ao ponto medio, e p é o ponto, isso para cada ponto na lista.
    #o angulo é a inclinação em relação ao eixo x.
    ps=[( atan2(p[1]-avg[1], p[0]-avg[0]), p ) for p in [p1,p2,p3,p4]] 

    #ordena a lista de tupla (angulo, ponto) em ordem descendente (do maior para o menor), e utiliza o primeiro elemento da tupla pra ordenar, se todos os primeiros elementos
    #forem iguais, usa o segundo elemento e assim por diante, ate encontrar alguma posicao de elemento que nao sejam iguais(esse é o comportamento padrão).
    #nao importa se a ordem for reversa ou nao o resultado é o mesmo
    ps.sort(reverse=True) 
    #retorna os pontos ordenados pelo angulo arcotangente em relacao ao ponto medio, 
    return [p[1] for p in ps]

#----------------------------------------------------------------------------------------
#valores das faces numeros de 0 a 5
#valores dos stickers numerados de 0 a 8 da esquerda para direita, de baixo para cima
#no video do andrej a sequencia apresentada das faces é:
#0 - laranja (com a face amarela voltada para cima)
#1 - verde
#2 - vermelho
#3 - azul 
#4 - amarelo (a partir do azul mostrar o amarelo girando o cubo no sentido antihorario)
#5 - branco (mantendo o eixo vertical do cubo quando foi mostrado o amarelo, girar no sentido antihorario(andrej virou no sentido antihorario))
#return tuple of neighbors given face and sticker indeces
#retorna uma tupla de tuplas
def neighbors(f,s):
    if f==0 and s==0: return ((1,2),(4,0)) #quina
    if f==0 and s==1: return ((4,3),) #meio
    if f==0 and s==2: return ((4,6),(3,0)) #quina
    if f==0 and s==3: return ((1,5),) #meio e assim por diante...
    if f==0 and s==5: return ((3,3),)
    if f==0 and s==6: return ((1,8),(5,2))
    if f==0 and s==7: return ((5,5),)
    if f==0 and s==8: return ((3,6),(5,8))
    
    if f==1 and s==0: return ((2,2),(4,2))
    if f==1 and s==1: return ((4,1),)
    if f==1 and s==2: return ((4,0),(0,0))
    if f==1 and s==3: return ((2,5),)
    if f==1 and s==5: return ((0,3),)
    if f==1 and s==6: return ((2,8),(5,0))
    if f==1 and s==7: return ((5,1),)
    if f==1 and s==8: return ((0,6),(5,2))
    
    if f==2 and s==0: return ((4,8),(3,2))
    if f==2 and s==1: return ((4,5),)
    if f==2 and s==2: return ((4,2),(1,0))
    if f==2 and s==3: return ((3,5),)
    if f==2 and s==5: return ((1,3),)
    if f==2 and s==6: return ((3,8),(5,6))
    if f==2 and s==7: return ((5,3),)
    if f==2 and s==8: return ((1,6),(5,0))
    
    if f==3 and s==0: return ((4,6),(0,2))
    if f==3 and s==1: return ((4,7),)
    if f==3 and s==2: return ((4,8),(2,0))
    if f==3 and s==3: return ((0,5),)
    if f==3 and s==5: return ((2,3),)
    if f==3 and s==6: return ((0,8),(5,8))
    if f==3 and s==7: return ((5,7),)
    if f==3 and s==8: return ((2,6),(5,6))
    
    if f==4 and s==0: return ((1,2),(0,0))
    if f==4 and s==1: return ((1,1),)
    if f==4 and s==2: return ((1,0),(2,2))
    if f==4 and s==3: return ((0,1),)
    if f==4 and s==5: return ((2,1),)
    if f==4 and s==6: return ((0,2),(3,0))
    if f==4 and s==7: return ((3,1),)
    if f==4 and s==8: return ((3,2),(2,0))
    
    if f==5 and s==0: return ((1,6),(2,8))
    if f==5 and s==1: return ((1,7),)
    if f==5 and s==2: return ((1,8),(0,6))
    if f==5 and s==3: return ((2,7),)
    if f==5 and s==5: return ((0,7),)
    if f==5 and s==6: return ((2,6),(3,8))
    if f==5 and s==7: return ((3,7),)
    if f==5 and s==8: return ((3,6),(0,8))

#----------------------------------------------------------------------------------------
#esse metodo é responsavel por definir as cores de cada face do cubo armazenada apos o usuario pressionar espaço durante a deteccao e rastreamento
#o problema que surge é que as cores detectadas podem ser muito parecidas e é dificil determinar um range adequado para cada cor de sticker
#usando informações do problema(nesse caso o cubo) definimos uma ordem em que as faces devem ser apresentadas e base em faces opostas, 3 cores possiveis das quinas
#e 2 cores possiveis dos meios, definimos com exatidão qual cores estamos observando
#esse metodo processa as cores detectadas e atribui a cada uma seu valor fixo de cor com base em caracteristicas do cubo
#no video do andrej a sequencia apresentada é:
#0 - laranja (ao mostrar o laranja a face amarela deve estar para cima. Em seguida girar antihorario para mostrar o verde e assim por diante)
#1 - verde
#2 - vermelho
#3 - azul 
#4 - amarelo (a partir do azul mostrar o amarelo girando o cubo no sentido antihorario em relação a tela)
#5 - branco (mantendo o eixo vertical do cubo quando foi mostrado o amarelo, girar no sentido antihorario(andrej virou no sentido antihorario) e mostrar o branco)
#o objetivo desse metodo é montar a matriz assigned onde as linhas representam as faces do cubo de 0 a 5
#e as colunas representam os stickers de cada face numerados de 0 a 9, da esquerda para direita de cima para baixo no grid
#e os valores de cada sticker representa a face a qual pertencem
#os elementos da coluna de numero 4 sao os stickers centrais e sao definidos estaticamente conforme mostramos na sequencia predefinida na variavel mycols
def processColors(useRGB=True):
    global assigned,didassignments

    #assign all colors
    bestj=0
    besti=0
    bestcon=0
    matchesto=0
    bestd=10001
    #taken é uma contagem de ocorrencias para as 6 faces do cubo
    #cada face conta a quantidade de stickers que foram identificados como pertencentes a ela (o valor maximo é 8 pois o sticker central ja é predefinido)
    #o criterio utilizado é a distancia no espaço RGB entre a cor detectada do sticker e a cor detectada do sticker do centro
    #quanto menor a distancia, mais proxima da cor do centro aquele sticker esta, logo pertencera aquela face
    taken=[0 for i in range(6)]
    done=0
    
    #dict of opposite faces
    #dicionario onde a chave e o valor são inteiros
    opposite={0:2, 1:3, 2:0, 3:1, 4:5, 5:4} 
    
    #possibilities for each face
    #a variavel 'poss' indica as possibilidades para um sticker de pertencer a cada uma das 6 faces do cubo possiveis
    #é um dicionario que armazena como chave a face e a posicao do sticker, e como valor uma lista contendo o numero de cada face
    #é usada para remover as faces que nao forem possibilidades para um sticker
    #o criterio usado para remover é identificar os stickers vizinhos do sticker da iteração atual
    # remove dos stickers vizinhos a face oposta ao sticker atual, pois essa possibilidade de face nunca ocorre(caracteristica do cubo de Rubik)
    # remove dos stickers vizinhos a face do sticker da iteração atual, pois obviamente não se encontram nessa face (caracteristica do cubo de Rubik)
    poss={}

    #para cada face do cubo
    for j,f in enumerate(hsvs):
        #para cada sticker do cubo
        for i,s in enumerate(f):
            #armazena uma lista de 6 faces possiveis em ordem crescente de 0 a 5 em cada posicao
            #armazena a possibilidade de faces para cada sticker de cada face do cubo de Rubik
            poss[j,i]=list(range(6))
    
    #we are looping different arrays based on the useRGB flag
    toloop = hsvs
   #por padrao usara RGB pois o parametro default do metodo é useRGB=True
    if useRGB: 
        #colors.shape: (6, 9) - 6 faces com 9 cores de sticker cada face
        toloop=colors
    
    #8 stickers, centro nao conta, das 6 faces do cubo de Rubik
    while done<8*6:
        #best distance
        bestd=10000
        forced=False
        #para cada face do cubo
        for j,f in enumerate(toloop):
            #para cada sticker do cubo
            for i,s in enumerate(f):
                #se nao for igual ao centro (i==4) e nao foi atribuido cor ainda para essa posicao (assigned[j][i] == -1)
                if i!=4 and assigned[j][i]==-1 and (not forced):
                    
                    #this is a non-center sticker.
                    #find the closest center
                    #a variavel 'considered' conta a quantidade de faces que sao consideradas para cada sticker
                    #esse valor tende a diminuir para cada sticker, conforme as possibilidades de face vao sendo removidas
                    considered=0
                    
                    #lembrando que poss[j][i] = [0, 1, 2, 3, 4, 5] onde cada numero é o numero de face considerada como possibilidade
                    #o valor de k é o valor de cada numero da face listado em poss[j][i]
                    for k in poss[j,i]:

                        #if false, all colors for this center were already assigned
                        #se a quantidade de stickers atribuidos a cada face numerada k, for igual a 8, significa que todos os stickers daquela face ja foram
                        #atribuidos, logo o sticker atual deve remover essa face por não ser mais uma de suas possibilidades.
                        if taken[k]<8:
                            
                            #use Euclidean in RGB space or more elaborate
                            #distance metric for Hue Saturation
                            if useRGB:
                                #calcula a distancia entre a cor do centro da face k e a cor do sticker atual 
                                dist=ptdst3(s, toloop[k][4])
                            else:
                                dist=ptdstw(s, toloop[k][4])
                                
                            considered+=1
                            #encontra a menor distancia entre a cor RGB do sticker atual e a cor do centro das 6 faces
                            # no final deste loop teremos a menor distancia bestd 
                            # no final deste loop teremos as coodenadas de face e posicao do sticker de menor distancia em bestj e besti, respectivamente
                            # e no final deste loop teremos a face que melhor se adequa a esse sticker em matchesto (usando o criterio de menor distancia RGB)
                            #bestj armazena a face do cubo onde bestd foi encontrada
                            #besti armazena a posicao do sticker onde bestd foi encontrada
                            #matchesto armazena o indice de poss[j][i] onde foi encontrada a menor distancia
                            if dist < bestd:
                                bestd=dist
                                bestj=j
                                besti=i
                                matchesto=k
                   
                    #IDEA: ADD PENALTY IF 2ND CLOSEST MATCH IS CLOSE TO FIRST
                    #i.e. we are uncertain about it 
                    #se o sticker atual for o de menor distancia, armazena o numero de faces consideradas possibilidades dele na variavel best considered.
                    if besti == i and bestj == j: 
                        bestcon = considered

                    #se o numero de faces consideradas para o sticker atual é igual a 1, significa que so tem uma face a que ele pode pertencer,
                    # as outras faces ou foram removidas pelo criterio de face oposta ou vizinho, ou ja foram preenchidas com todos os seus stickers pertencentes.
                    #é um criterio de parada, por isso itera 8*6 em cada sticker do cubo, se o sticker so tem apenas uma face como possibilidade,
                    #não ha necessidade de avalia-lo mais, logo nao vai mais entrar no loop quando for esse sticker, dai entao reinicia o loop que itera sobre todos os stickers
                    #para iterar nao considerando mais stickers 'forçados' ou seja stickers que são forçados a serem somente de uma face, pois é sua unica possibilidade,
                    #com base nos criterios de vizinho e face oposta(caracteristicas do cubo)
                    if considered == 1:
                        #this sticker is forced! Terminate search 
                        #for better matches
                        forced=True
                        print('sticker',(i,j),'had color forced!')
                    
        #Obs: ao ser encerrado pela metade por um sticker forçado, o codigo continua com o sticker com a menor distancia ate a face encontrado ate o momento,
        #se for o primeiro sticker da primeira face dos loops atuais, mantem o bestj e besti e matchesto dos loops anteriores, logo nao altera o assigned,
        #se for o segundo sticker da primeira face dos loops atuais, vai associar o besti e bestj a menor correspondencia de distancia entre esse segundo sticker
        #e cada uma das faces, logo nao tem problema, pois sempre pegara a face com a menor distancia em relação ao sticker e associara essa a face ao sticker,
        #dessa forma alterando corretamente o assigned, então é muito provavel que seja a cor correta do sticker em relação a face que com ele forma a menor distancia 
        #no espaço RGB em relação as outras faces.

        #assign it
        #done é a contagem das vezes em que o loop que itera sobre todos os stickers foi reiniciado
        done=done+1
        #print matchesto,bestd
        #assigned é uma matriz de coordenadas de stickers onde cada coordenada armazena a face a qual o sticker(coordenada) com a menor distancia encontrada pertence.
        assigned[bestj][besti]=matchesto
        print(bestcon)
        
        #get the opposite side
        #remove this possibility from neighboring stickers (considera lados opostos para definir os vizinhos do sticker, os vizinhos sao as cores que estao na mesma pecinha quadrada do cubo)
        #since we cant have red-red edges for example (as cores laranja e vermelho podem ser muito parecidas)
        #also corners(quinas) have 2 neighbors. 
        # Also remove possibilities of edge/corners made up of opposite sides
        #opposite é um dicionario, que armazena a cor oposta de uma dada face dada como chave do dicionario
        #essa linha pega o numero da face oposta
        op= opposite[matchesto] 

        #pega os vizinhos dos sticker i dessa face j que tem a menor distancia em relação ao centro da face 
        ns=neighbors(bestj,besti)
        #para cada vizinho (face, sticker) na lista de vizinhos
        for neighbor in ns:
            p=poss[neighbor]
           
           #remove do vizinho do sticker atual a possibilidade de ser da face atual, pois obviamente nao e da face atual
            if matchesto in p: 
                p.remove(matchesto)

            #remove do vizinho do sticker atual a possibilidade de ser da face oposta a do sticker atual, pois os vizinhos do sticker atual nao podem ser da face oposta do mesmo
            #isso é uma caracteristica do cubo
            if op in p: 
                p.remove(op)
        #atribui a face atual o sticker atual que melhor atendeu o criterio de distancia RGB, cada face pode ter no maximo 8 stickers atribuidos
        taken[matchesto]+=1

    #didassignments marcado como True, permite que assigned(matriz que associa stickers a sua face original) seja usado para preencher cada cubinho do grid com as cores
    # corretas dentro do grid com linhas vermelhas na tela, se didassigments é false, preenche os cubinhos com as cores detectadas sem tratamento.   
    didassignments=True

#----------------------------------------------------------------------------------------

def distanciaEuclidiana(p1,p2):
    return sqrt(dot(p1[0]-p2[0], p1[1]-p2[1], p1[0]-p2[0], p1[1]-p2[1]))

#----------------------------------------------------------------------------------------
#verifica se dois segmentos se intersectam, retorna a porcentagem das retas a e b, e o ponto de intersecção
def intersect_seg(x1,x2,x3,x4,y1,y2,y3,y4):
    a = vect((x1, y1), (x2, y2))
    b = vect((x3, y3), (x4, y4))
    c = vect((x3, y3), (x1, y1))

    den = cross(a[0], a[1], b[0], b[1]) # a x b (valor total da area entre os dois segmentos informados)

    EPS = 0.1 #EPS é para tratar ponto flutuante, quanto menor mais precisao, menor que EPS significa menor que zero.
    
    if abs(den)< EPS: 
        return (False, (0,0),(0,0))
    
    ua = cross(b[0], b[1], c[0], c[1]) #b x c (procentagem da reta a ou sua porcentagem em area)
    ub = cross(a[0], a[1], c[0], c[1]) #a x c (porcentagem da reta b ou sua porcentagem em area) 
    
    ua=ua/den  #areas relativas(reta a) em relacao a area total, adimensional (sera o valor t da equacao parametrica do segmento de reta)
    ub=ub/den #areas relativas(reta b) em relacao a area total, adimensional (sera o valor t da equacao parametrica do segmento de reta)
    
    #equacao parametrica do segmento de reta(ponto + vetor = ponto deslocado pelo valor do vetor)
    #(x_desloc, y_desloc) = (x, y) + t * (x_vec, + y_vec)
    x=x1+ua*(x2-x1) #como usamos ua (valor parcial de area ou tamanho parcial da reta a) - escolhemos um ponto na reta a e o vetor do segmento multiplicado pelo t
    y=y1+ua*(y2-y1) #assim encontramos o ponto de intesecção
    return (True,(ua,ub),(x,y)) # retorna que tem intersecção, os comprimentos parciais das retas a e b, e o ponto de intesecção.
#----------------------------------------------------------------------------------------

#produto vetorial
def cross(v1x, v1y, v2x, v2y):
    return v1x*v2y - v1y*v2x 

#produto escalar
def dot(v1x, v1y, v2x, v2y):
    return v1x*v2x + v1y*v2y

#cria um vetor a partir de dois pontos
def vect(p_ini, p_end):
    return (p_end[0] - p_ini[0], p_end[1] - p_ini[1])

def vectorAddition(v1, v2):
    return (v1[0]+v2[0], v1[1]+v2[1])

def scalarTimesVect(k, v):
    return (k*v[0], k*v[1])
#----------------------------------------------------------------------------------------

def circulo(imagem, centro, raio, cor, grossura):
    return cv2.circle(imagem, centro, int(raio), cor, grossura)


#---------------------------------------------------------------------------------------

def main():
    #variaveis globais indicam quais variaveis nessa função sao utilizadas por outras funções
    global lastdetected, THR, prevface, onlyBlackCubes
    global succ, tracking, detected, grey, prev_grey, undetectednum, selected, colors, assigned, didassignments
    global SerialArduino
    global endArduinoEvent

    #variavel armazena o numero ideal de linhas de hough a serem detectadas durante a avaliação de um par de retas candidatas a serem sistema de coordenadas do cubo
    global dects

    #variavel responsavel por extrair as informações de cor e armazenar na variavel hsvs, quando o usuario pressionar espaço
    global extract

    #variavel que armazena as cores detectadas e é impressa caso o usuario aperte a tecla 'q'
    global hsvs

    #variavel booleana que controla se o programa faz a detecção ou nao caso o usuario pressione a tecla 'd'
    global dodetection

    #Largura e altura das imagens a serem processadas
    global W, H 

    #capture = cv2.VideoCapture(0) #webcam
    capture = cv2.VideoCapture("http://192.168.55.180:81/stream") #esp32cam mudar para 640x480 //para ver a tela de opcoes remova a porta e o contexto da url
    
    cv2.namedWindow("ESP32-CAM", 1)
    
    _, frame = capture.read()
    
    S1, S2  = frame.shape[:2]
    
    #denominador convertendo de 640x480 para 320x240 para melhorar a eficiencia
    W,H=int(S1/2), int(S2/2)

    lastdetected= 0
    
    #threshold da transformada de Hough
    #define o numero minimo de intersecções entre curvas no espaço de hough para que seja considerado uma reta detectada
    #cada ponto (x, y) no plano cartesiano define uma familia de curvas no espaço de hough onde os parametros polares(rho, theta) variam e as coordenadas (x, y) do ponto sao fixas.
    #quando cada curva dessa no espaço de hough se intersectam em um ponto, significa que naquele ponto de intersecção (rho, theta), os pontos (x, y) pertencem aquela reta.
    #entao aqui, precisamos que no minimo que 100 pontos pertençam a reta para seja detectada como uma linha
    THR=100
    
    #ideal number of number of lines detections, garante a invariancia a escala
    dects=50 

    #stores the coordinates(pontos) that make up(compoem) the face. in order: p,p1,p3,p2 (i.e.) counterclockwise winding(ordenados no sentido antihorario)
    #prevface é a lista de pontos que representam os cantos de uma face do cubo ordenados em sentido antihorario contando a partir da origem do sistema de coordenadas criado do cubo
    #p é a origem (0,0) do sistema de coordenadas (canto inferior esquerdo do cubo)
    #p1 é a coordenada (1, 0)
    #p3 é a coordenada (1, 1)
    #p2 é a coordenada (0, 1)
    #lembrando que o sistema de coordenadas criado os eixos x e y vão de 0 até 1 para cada eixo
    prevface=[(0,0),(5,0),(0,5)]
   
    dodetection=True
    
    onlyBlackCubes=False

    #success
    #number of frames in a row that we were successful in finding the outline 
    succ=0 
    
    tracking=0
    
    detected=0
    
    grey = np.zeros((W, H), np.int8)
    
    prev_grey = np.zeros((W, H), np.int8)

    undetectednum=100
    endArduinoEvent = False
    SerialArduino = abriConexaoSerialArduino();

    #stage=1 #1: learning colors
    extract=False
    
    selected=0

    #cria uma lista de listas com 6 posicoes: colors = [[], [], [], [], [], []]
    colors=[[] for i in range(6)]

    hsvs = [[] for i in range(6)]

    # cria uma matriz bidimensional 6x9 onde cada coluna é preenchida com -1
    # assigned = [
    #    [-1, -1, -1, -1, -1, -1, -1, -1, -1],  # 1ª linha
    #    [-1, -1, -1, -1, -1, -1, -1, -1, -1],  # 2ª linha
    #    [-1, -1, -1, -1, -1, -1, -1, -1, -1],  # 3ª linha
    #    [-1, -1, -1, -1, -1, -1, -1, -1, -1],  # 4ª linha
    #    [-1, -1, -1, -1, -1, -1, -1, -1, -1],  # 5ª linha
    #    [-1, -1, -1, -1, -1, -1, -1, -1, -1]   # 6ª linha
    # ]
    assigned=[[-1 for i in range(9)] for j in range(6)] 


    #atualiza a quinta coluna (indice 4) de cada linha da matriz
    # assigned = [
    #    [-1, -1, -1, -1,  0, -1, -1, -1, -1],  # 1ª linha: coluna 4 atualizada para 0
    #    [-1, -1, -1, -1,  1, -1, -1, -1, -1],  # 2ª linha: coluna 4 atualizada para 1
    #    [-1, -1, -1, -1,  2, -1, -1, -1, -1],  # 3ª linha: coluna 4 atualizada para 2
    #    [-1, -1, -1, -1,  3, -1, -1, -1, -1],  # 4ª linha: coluna 4 atualizada para 3
    #    [-1, -1, -1, -1,  4, -1, -1, -1, -1],  # 5ª linha: coluna 4 atualizada para 4
    #    [-1, -1, -1, -1,  5, -1, -1, -1, -1]   # 6ª linha: coluna 4 atualizada para 5
    #]
    for i in range(6):
        assigned[i][4]=i

    didassignments=False

    #iniciando loop de detecção
    while True:
        res, frame = capture.read()

        if not res:
            cv2.waitKey(0)
            break
        
        try:
            endLoop = loopPrincipal(frame)
        except Exception as e:
            print("Erro no loop principal: "+str(e))

        if(endLoop == -1):
            break

    cv2.destroyAllWindows()

#-------------------------------------------------------------------------------------

def loopPrincipal(frame):
    
    #variaveis passadas como parametro
    global sg, tracking,  onlyBlackCubes, lastdetected, THR, undetectednum, colors, selected, prev_grey
    global prevface, succ, sgc, dodetection, detected, grey, extract, didassignments

    #variaveis criadas dentro da função que devem ser globais pois sao utilizadas em outros trechos de codigo que nao sao executados na primeira execucao do metodo
    global p0, lastpt, v1, v2, features, houghLines, pt

    #cria uma imagem reduzida pela metade: 1 parametro(tamanho w e h), 2 parametro: bit depth(8 bits), 3 parametro( numero de canais: 3 canais)
    #np.zeros cria uma numpyarray do tamanho especificado e prenche com zeros do tipo especificado (cria uma imagem totalmente preta)
    sg = np.zeros((W, H, 3),np.int8)

    HEIGHT, WIDTH = sg.shape[:2]
    sg = cv2.resize(frame, (WIDTH, HEIGHT))

    sgc = sg.copy()

    grey = cv2.cvtColor(sg, cv2.COLOR_RGB2GRAY)

    #tracking mode (na primeira execucao tracking = 0, logo começa no modo detecção)
    if tracking > 0:
        trackingMode()
        
            
    #detection mode
    if tracking == 0:
        detectionMode()
    #esse else esta linkado apenas ao if do detection mode
    #se durante o trackingMode as valições passaram e o lucas-kanade nao perdeu os pontos antigos das cruzes entao usamos os novos pontos das cruzes, 
    #para obter o sistema de coordenadas do contorno externo do grid, realizando a combinação linear descrita abaixo, ao entrar no else tracking na realidade é igual a 1.
    #ao realizar a expansao para o sistema de coordenadas do cubo com base nos novos pontos das cruzes obtidos por meio do lucas-kanade, seguimos para exibir o grid
    #detectado em tela como se tivesse sido detectado pela primeira vez por meio da transformada de hough
    else:
        #we are in tracking mode, we need to fill in pt[] array
        #calculate the pt array for drawing from features
        #for p in features:
        p=features[0]
        p1=features[1]
        p2=features[2]
        
        v1 = vect(p, p1)
        v2 = vect(p, p2)

        #calcula tres novos pontos a partir do ponto de origem p somado com combinacoes lineares dos vetores v1 e v2
        #ao observar essa combinação linear em um plano cartesiano geometricamente, percebemos que o sistema de coordenadas formado por p, v1 e v2
        #é expandido por um fator de 2, isso significa que estamos levando o sistema de coordenadas que sao das cruzes do cubo (p, v1 e v2 sao pontos de rastreio
        #do algoritmo lucas-kanade, pontos das cruzes do cubo) para o sistema de coordenadas maior que são as bordas externas do cubo mágico, que são os pontos do
        #sistema de coordenadas da face do cubo.
        pt=[(p[0]-v1[0]-v2[0], p[1]-v1[1]-v2[1]),
            (p[0]+2*v2[0]-v1[0], p[1]+2*v2[1]-v1[1]),
            (p[0]+2*v1[0]-v2[0], p[1]+2*v1[1]-v2[1])]
        
        #armazena o valor dos pontos da face para calculos posteriores
        #3 pontos ja definem um plano
        prevface=[pt[0],pt[1],pt[2]]

    #a partir da primeira vez que a função detectionMode consegue identificar um grid(e incrementando a variavel succ), pula pra ca em seguida
    #é aqui que é preenchido o p0, v1 e v2 para colocar os pontos no centro das 4 cruzes encontradas no grid, permitindo que o rastreador Lucas-Kanade possa rastrear esses 4 pontos
    #use pt[] array to do drawing
    if (detected or undetectednum < 1) and dodetection:
        #undetectednum 'fills in' a few detection to make
        #things look smoother in case we fall out one frame
        #for some reason
        if not detected: 
            undetectednum+=1
            pt=lastpt
        if detected: 
            undetectednum=0
            lastpt=pt
        
        #extract the colors
        #convert to HSV
        hsv = cv2.cvtColor(sgc, cv2.COLOR_RGB2HSV)

        hue, sat, val = cv2.split(hsv)

        #do the drawing. pt array should store p,p1,p2
        #a variavel pt quando o grid é detectado pela primeira vez armazena as coordenadas do sistema de coordenadas do grid detectado, que representam os 4 cantos do cubo
        #pt = (p, p1, p2) onde p (0,0) origem do sistema de coordenadas, p1 (1,0) ponto final do eixo x, p2 (0, 1) ponto final do eixo y
        #p3 aqui é o ponto da diagonal superior direita (1, 1)
        vectp1p2 = vectorAddition(pt[1], pt[2])
        p3 = vect(pt[0], vectp1p2)

        sg = cv2.line(sg,(int(pt[0][0]), int(pt[0][1])),(int(pt[1][0]), int(pt[1][1])),(0,255,0),2)
        
        sg = cv2.line(sg,(int(pt[1][0]),int(pt[1][1])),(int(p3[0]), int(p3[1])),(0,255,0),2)
        
        sg = cv2.line(sg,(int(p3[0]), int(p3[1])),(int(pt[2][0]),int(pt[2][1])),(0,255,0),2)
        
        sg = cv2.line(sg,(int(pt[2][0]),int(pt[2][1])),(int(pt[0][0]),int(pt[0][1])),(0,255,0),2)
        
        #first sort the points so that 0 is BL 1 is UL and 2 is BR
        #ordena no sentido horario, onde o primeiro ponto é um superior esquerdo
        pt=winded(pt[0],pt[1],pt[2],p3)
        
        #find the coordinates of the 9 places we want to extract over
        #vetor que vai do canto superior esquerdo ate o superior direito
        v1 = vect(pt[0], pt[1])

        #vetor que vai do canto superior esquerdo ate o inferior esquerdo
        v2 = vect(pt[0], pt[3])

        #ponto do canto inferior esquerdo(origem do sistema de coordenadas)
        p0=(pt[0][0],pt[0][1])
        
        ep=[]
        
        i=1
        j=5
        #aqui itera por cada sticker do cubo, dividindo cada segmento do eixo de coordenadas por 6
        # assim temos uma distancia ate o centro de cada sticker do cubo
        # i é a linha de stickers mais inferior do cubo
        # j é a coluna de stickers mais a direita do cubo
        # 1 iteracao: 5/6 da altura do cubo fica fixo começando de baixo para cima,
        #             1/6 da largura do cubo é avançada começando da esquerda para direita
        #             isso é a coordenada do centro do sticker da 3 linha 1 coluna
        # 2 iteracao: 5/6 da altura do cubo fica fixo começando de baixo para cima,
        #             3/6 da largura do cubo é avançada começando da esquerda para direita
        #             isso é a coordenada do centro do sticker da 3 linha 2 coluna
        # 3 iteracao: 5/6 da altura do cubo fica fixo começando de baixo para cima,
        #             5/6 da largura do cubo é avançada começando da esquerda para direita
        #             isso é a coordenada do centro do sticker da 3 linha 3 coluna 
        # 4 iteracao: 3/6 da altura do cubo fica fixo começando de baixo para cima,
        #             1/6 da largura do cubo é avançada começando da esquerda para direita
        #             isso é a coordenada do centro do sticker da 2 linha 1 coluna 
        # e assim sucessivamente
        #lembrando que é uma soma de ponto com vetor, o ponto de origem do sistema coodenadas
        #fica no canto superior esquerdo, e somamos os vetores v1 e v2 que sao os eixos
        #de forma proporcional a posicao que queremos.
        #desenhar geometricamente os eixos e dividir em 6 partes pensando na face do cubo ajuda 
        # a entender
        for k in range(9):
            v1scaled = scalarTimesVect(i/6, v1)
            v2scaled = scalarTimesVect(j/6, v2)
            v1v2sum = vectorAddition(v1scaled, v2scaled)
            
            ep.append((p0[0]+v1v2sum[0], p0[1]+v1v2sum[1]))
            i=i+2
            if i==7:
                i=1
                j=j-2
        
        #raio do circulo a ser desenhado em cada sticker
        #divide o eixo superior do sistema de coordenadas(borda superior do cubo) em 6 segmentos
        # e pega o valor desse 1/6 de segmento que representa a distancia da borda do sticker ate o 
        # centro do sticker. Como todos os stickers do cubo tem o mesmo tamanho, o raio sera o mesmo
        # para todos os stickers 
        rad = distanciaEuclidiana(v1,(0.0,0.0))/6.0
        
        #colors
        cs=[]

        #hsv colors
        hsvcs=[]

        #denominator
        den=2
        
        #enumerate cria um iterador para cada item da lista ep e adiciona um indice
        #o item da lista p, é a localização(ponto) do centro do sticker no cubo
        #6 7 8
        #3 4 5
        #0 1 2
        for i,p in enumerate(ep):
            #define os intervalos para os quais a localizacao x e y do centro do sticker é valida
            #x e y devem ser maiores que o raio de um sticker do sistema de coordenadas(limite inferior) 
            # e menores que a resolucao da imagem menos o raio (limite superior)
            # isso garante mais robustez e impede que circulos sejam desenhados errado no grid 
            #rad < p[0] < W-rad  e rad < p[1] < H-rad
            if p[0]>rad and p[0]<W-rad and p[1]>rad and p[1]<H-rad:
                #extrair cor!!!
                #divide o raio do sticker por 2 para criar um circulo menor e calcula a media dos valores de
                #cor dos pixels de sgc nas coordenadas do diametro desse circulo menor
                #lembrando que a cor obtida e um array de 3 posicoes (para imagens coloridas)
                col = cv2.mean(sgc[int(p[1]-rad/den):int(p[1]+rad/den),int(p[0]-rad/den):int(p[0]+rad/den)])

                # -1 indica que o circulo deve ser totalmente preenchido com a cor extraida
                sg = circulo(sg, (int(p[0]), int(p[1])), rad, col, -1) 

                #se for o centro do sticker central do cubo printa de amarelo o circulo,
                #caso contrário fica branco
                if i==4:
                    sg = circulo(sg, (int(p[0]), int(p[1])), rad, (0,255,255),2)
                else:
                    sg = circulo(sg, (int(p[0]), int(p[1])), rad, (255,255,255),2)
                
                hueavg= cv2.mean(hue[int(p[1]-rad/den):int(p[1]+rad/den),int(p[0]-rad/den):int(p[0]+rad/den)])

                satavg= cv2.mean(sat[int(p[1]-rad/den):int(p[1]+rad/den),int(p[0]-rad/den):int(p[0]+rad/den)])
                
                #sg = cv2.putText(sg, str(int(hueavg)), (int(p[0])+70,int(p[1])), cv2.FONT_HERSHEY_SIMPLEX, 0.2, (255,255,255))
                
                #sg = cv2.putText(sg, str(int(satavg)), (int(p[0])+70,int(p[1])+10), cv2.FONT_HERSHEY_SIMPLEX, 0.2, (255,255,255))
                textColor = "("+str(int(col[0]))+","+str(int(col[1]))+",",str(int(col[2]))+")"
                sg = cv2.putText(sg, str(textColor), (int(p[0])+70,int(p[1])), cv2.FONT_HERSHEY_SIMPLEX, 0.2, (255,255,255))

                if extract:
                    #inclui a cor RGB extraida na lista cs
                    cs.append(col)
                    #inclui a cor HSV extraida na lista hsvcs
                    hsvcs.append((hueavg,satavg))
                    
        if extract:
            extract= not extract
            #select é inicializado com valor 0 no metodo main()
            # colocar a lista de cores detectadas da face no indice 0 da lista colors 
            colors[selected]=cs

            #hsvs detectados sao armazenados na lista hsvs
            hsvs[selected]=hsvcs
            #como o cubo tem 6 faces, o select é limitado entre o indice 0 e o indice 5
            selected=min(selected+1,5)

    #draw faces of the extracted cubes
    #o retangulo vermelho tem origem no ponto (20, 20) da imagem original
    x=20
    y=20
    
    #sticker
    #é a area do lado do sticker visto na imagem
    #o 13 significa a distancia horizontal e vertical ocupada por cada sticker dentro do grid no topo
    # ao clicar em espaço
    s=13

    #orange green red blue yellow white. Used only for visualization purposes
    #são cores no formato rgb usadas para saber qual cor do centro da face devemos mostrar para o cubo para cada quadrado na tela quando sao todos preenchidos ao apertar
    #espaço. O usuario em seguida aperta 'u' e entao é mostrada a sequencia que deve ser apresentada das faces, com base em sua cor de centro.
    #limitação: é necessário mostrar os centros nessa sequencia dessas nessa cores especificadas para que o algoritmo imprima corretamente as cores
    #mostrar a face laranja com a face amarela para cima, girar o cubo no sentido antihorario 
    #a ideia de manter as cores fixas numa sequencia predeterminada, garante a invariancia a iluminação, perdemos um pouco de praticidade porem ganhamos muito em robustez
    #para aumentar a praticidade, poderiamos ordenar as cores detectadas no formato hsv e encontrar as cores fixadas seguindo a sequencia encontrada, porem corremos
    #o risco de no caso de uma iluminação inadequada, invertermos cores muito proximas como laranja e vermelho, e dessa forma errar a posicao das cores fixadase errar a deteccao
    #como um todo.
    mycols=[(0,127,255), (20,240,20), (0,0,255), (200,0,0), (0,255,255), (255,255,255)]

    #-----------------------------------------------------------------------------
    #desenhando o grid de stickers que vemos ao pressionar espaço durante a execucao do programa
    #itera sobre cada face detectada
    for i in range(6):
        #verifica se tem cor detectada pra face atual, se nao tem avança para o proximo retangulo na horizontal
        # e pula a iteração 
        if not colors[i]: 
            #sticker separados por 3 vezes o seu lado, e os grids sao separados por 10 posicoes cada grid
            x+=3*s+10
            continue
        #draw the grid on top
        #imprime as cores detectadas no retangulo vermelho
        #cria as linhas pretas vistas ao pressionar espaço e ver as cores na tela
        sg = cv2.rectangle(sg, (x-1,y-1), (x+3*s+5,y+3*s+5), (0,0,0),-1)
        #canto superior esquerdo do retangulo do sticker
        x1,y1=x,y

        #canto inferior direito do retangulo do sticker
        x2,y2=x1+s,y1+s
        #itera por cada sticker detectado dentro da face detectada
        for j in range(9):
            #didassignments indica que as cores detectadas ja passaram por processamento previo no metodo processColors()
            if didassignments:
                #se ja foi apertado espaço para essa face, os valores salvos das cores processadas estarao em assigned
                #aqui reimprime esses valores com as cores definidas
                sg = cv2.rectangle(sg, (x1,y1), (x2,y2), mycols[assigned[i][j]],-1)
            else:
                #se foi apertado botão espaço agora e assigned ainda nao esta preenchido com as cores
                #busca do vetor que possui as cores armazenadas na detecção e imprime a cor
                # atual no sticker atual
                try:
                    sg = cv2.rectangle(sg, (x1,y1), (x2,y2), colors[i][j],-1)
                except IndexError as e:
                    print("Erro colors: ", e)
                    #print("colors.shape: ", np.asarray(colors).shape)
            
            #incrementa x1 para o proximo sticker com um adendo de 2 de grossura para reprentar
            #o traço preto do grid 
            x1+=s+2
            
            #se for sticker mais a direita da linha 1 ou linha 2, de cima pra baixo
            if j==2 or j==5:
                #volta o x para a posicao inicial mais a direita do cubo 
                x1=x
                #incrementa y1 na vertical para o sticker da proxima linha, de cima pra baixo
                y1+=s+2
            #incrementa o ponto atual inferior direito do retangulo para o proximo sticker
            x2,y2=x1+s,y1+s

        #avança x em 3 posicoes de sticker e incrementa 10 para dar um espaço entre dois grids
        x+=3*s+10
    #--------------------------------------------------------------------------
    #draw the selection rectangle
    #desenha o retangulo de seleção, aquele vermelho que fica na imagem
    x=20
    y=20
    for i in range(selected):
        x+=3*s+10
    
    sg = cv2.rectangle(sg, (x-1,y-1), (x+3*s+5,y+3*s+5), (0,0,255), 2)

    #inteiro que armazena a ultima quantidade de linhas detectadas pela transformada de hough
    lastdetected= len(houghLines)
    
    #swapping for LK
    #agora a imagem atual se torna a imagem anterior e grey sera carregado novamente a partir do frame mais atual
    #essa troca ocorre para armazenar os valores de imagem antiga e atual que o Lucas-Kanade precisa
    #para calcular a nova posição dos pixels detectados anteriormente.
    prev_grey, grey = grey, prev_grey
    
    #draw img
    imagetoShow = cv2.resize(sg, (640,480), interpolation=cv2.INTER_LINEAR)
    cv2.imshow("ESP32-CAM", imagetoShow)
    
    # handle events
    c = cv2.waitKey(10) % 0x100
    END_LOOP = -1

    
    #ESC
    if c == 27: 
        endArduinoEvent = True
        return END_LOOP
    cc = c

    # processing depending on the character
    processInformedCharacter(c, cc)

    return 0

#-------------------------------------------------------------------------------------------------------
#realiza o rastreio continuo do cubo na imagem, apos a detecção ter ocorrido
def trackingMode():
    global detected, features, tracking
    detected=2
    featArr = [[x for x in range(2)] for y in range(len(features))]
    featArr = np.asarray(featArr, dtype=np.float32)
    for i in range(len(features)):
        for j in range(2):
            featArr[i][j] = features[i][j]

    features = featArr
    
    #a partir dos pontos fornecidos(features), fornece os vetores que indicam a nova posicao dos pontos antigos.
    # o retorno é um array numpy no formado de 4 linhas e 2 colunas, retornando 4 vetores de duas posicoes x e y que indicam a nova posicao detectada.
    features, status, track_error = cv2.calcOpticalFlowPyrLK(prev_grey, grey, features, None, winSize=(7,7), maxLevel=3, criteria=(cv2.TermCriteria_COUNT|cv2.TermCriteria_EPS, 20 ,0.1),flags=0)
    
    # set back the points we keep
    # se o fluxo optico do ponto foi encontrado(st == 1) entao adiciona ele na nova lista de features
    # se o fluxo optico do ponto nao foi encontrado (st == 0) não adiciona a lista de features
    features = [ p for (st,p) in zip(status, features) if st] 
    
    #len retorna o numero de elementos do container informado
    # se o fluxo optico de algum dos pontos não foi encontrado nos perdemos o rastreio, precisamos executar o Lucas Kanade novamente
    if len(features) < 4:
        #we lost it, restart search 
        tracking = 0
    else:
        #make sure that in addition the distances are consistent
        ds1=distanciaEuclidiana(features[0], features[1])
        ds2=distanciaEuclidiana(features[2], features[3])
        
        #verifica se as distancias encontradas nao sao maiores que 40% pois isso significa que as linhas das cruzes de 1/3 ate 2/3 tem tamanhos diferentes em cima e em baixo
        #logo os pontos novos detectados pelo lucas-kanade estao incorretos logo reiniciar o rastreio
        #verifica linhas horizontais entre as cruzes
        if max(ds1,ds2)/min(ds1,ds2)>1.4: 
            tracking=0
        
        ds3=distanciaEuclidiana(features[0], features[2])
        ds4=distanciaEuclidiana(features[1], features[3])
        
        #verifica linhas verticais entre as cruzes
        if max(ds3,ds4)/min(ds3,ds4)>1.4: 
            tracking=0
        
        #se alguma das linhas for muito pequena, o rastreamento tambem falhou logo reinicia o rastreio
        if ds1<10 or ds2<10 or ds3<10 or ds4<10: 
            tracking=0
        
        #se o rastreamento falhou entao reinicia a detecção
        if tracking == 0: 
            detected=0

#---------------------------------------------------------------------------------------------------------------------
#realiza a detecção do cubo na imagem
def detectionMode():
    global detected, onlyBlackCubes, grey, lastdetected, dects, THR, houghLines, succ, prevface, features, tracking, pt

    detected=0
    
    # 3 é o kernel size e 0 é o sigma que é calculado a partir do kernel size
    dst2 = cv2.GaussianBlur(grey, (3,3), 0, None, 0, cv2.BORDER_REFLECT) 

    d = cv2.Laplacian(dst2, cv2.CV_8U, None, 3)

    #compara a imagem d se o pixel é maior que 8 se for seta 1 em d2, caso contrario 0. Assim, d2 será uma imagem binaria.
    d2 = cv2.compare(d, 8, cv2.CMP_GT)
    
    if onlyBlackCubes:
        #can also detect on black lines for improved robustness
        b = cv2.compare(grey, 100, cv2.CV_8U)
        d2 = cv2.bitwise_and(b, d2)
        
    #these weights should be adaptive. We should always detect 100 lines
    #o numero de intersecções da transformada de hough aumenta se a ultima detecção teve mais de 50 linhas detectadas
    if lastdetected>dects: 
        THR=THR+1

    #o numero de intersecções da transformada de hough diminui até no minimo 2 se a ultima detecção teve menos de 50 linhas detectadas
    if lastdetected<dects: 
        THR=max(2,THR-1)
    
    PI = 3.1415926
    houghLines = cv2.HoughLinesP(d2, 1, PI/45, THR, None, 10, 5) #retorna os pontos iniciais e finais de cada linha
    
    #store angles for later
    angs=[]
    
    #for p1, p2 in houghLines:
    for line in houghLines:
        #pontos inicial e final do segmento
        p1 = [line[0][0], line[0][1]]
        p2 = [line[0][2], line[0][3]]

        #retorna o angulo medido em radianos em relacao ao eixo horizontal
        a = atan2(p2[1]-p1[1],p2[0]-p1[0])
        #se o angulo for negativo soma 180(será o angulo do quadrante diametralmente oposto em relacao ao eixo horizontal) e adiciona a lista de angulos
        if a < 0:
            a += pi
        angs.append(a)
    

    #lets look for lines that share a common end point(extremidade em comum)
    t=10
    totry=[]

    for i in range(len(houghLines)):
        p1 = [houghLines[i][0][0], houghLines[i][0][1]]
        p2 = [houghLines[i][0][2], houghLines[i][0][3]]
        
        for j in range(i+1,len(houghLines)):
            q1 = [houghLines[j][0][0], houghLines[j][0][1]]
            q2 = [houghLines[j][0][2], houghLines[j][0][3]]


            #test lengths are approximately consistent
            dd1 = distanciaEuclidiana(p1, p2) #tamanho da reta
            dd2 = distanciaEuclidiana(q1, q2) #tamanho da outra reta

            #tolerancia de no maximo 30% de diferença entre as distancias dos dois pares de pontos(retas tem que ter tamanhos proximos)
            #retas com mais de 30% de diferença do comprimento são descartadas
            if max(dd1,dd2)/min(dd1,dd2)>1.3: 
                continue  
            
            matched=0

            #verifica se as extremidades estao proximas umas das outras, se sim, calcula o ponto medio da reta que liga os dois pontos,
            #armazena os pontos das outras extremidades, e o tamanho da primeira reta.
            if areclose(p1,q2,t): #t = 10
                IT=(avg(p1,q2), p2, q1,dd1)
                matched=matched+1
            if areclose(p2,q2,t): 
                IT=(avg(p2,q2), p1, q1,dd1)
                matched=matched+1
            if areclose(p1,q1,t): 
                IT=(avg(p1,q1), p2, q2,dd1)
                matched=matched+1
            if areclose(p2,q1,t): 
                IT=(avg(p2,q1), q2, p1,dd1)
                matched=matched+1
            
            #se nao tem retas se cruzando na extremidade, é verificado os segmentos internos
            if matched==0:
                #not touching at corner... try also inner grid segments hypothesis?
                p1=(float(p1[0]),float(p1[1]))
                p2=(float(p2[0]),float(p2[1]))
                q1=(float(q1[0]),float(q1[1]))
                q2=(float(q2[0]),float(q2[1]))
                success,(ua,ub),(x,y) = intersect_seg(p1[0],p2[0],q1[0],q2[0],p1[1],p2[1],q1[1],q2[1])
                
                #success indica que as linhas se intersectam, ua e ub indicam a proporção das retas a e b que se cruzam, ua e ub estao entre 0 e 1
                #x, y é o ponto onde as duas linhas se intersectam
                if success and ua>0 and ua<1 and ub>0 and ub<1:
                    #if they intersect
                    ok1=0
                    ok2=0
                    #epsilon é um valor para comparar float,quanto menor maior a precisao, se fosse int poderia ser usado zero sem problemas
                    epsilon = 0.05
                    # aqui verifica se a proporção calculada é igual a 1/3 ou 2/3 das retas a ou b, pois subtraindo a proporção que ha intersecção nas retas, se essa subtração
                    #for proxima de zero significa que a intersecção ocorre a 1/3 ou 2/3 das retas.
                    if abs(ua-1.0/3) < epsilon:
                        ok1=1
                    if abs(ua-2.0/3) < epsilon:
                        ok1=2
                    if abs(ub-1.0/3) < epsilon:
                        ok2=1
                    if abs(ub-2.0/3) < epsilon:
                        ok2=2

                    #se em cada uma das duas retas que se intersectam ou o criterio do 1/3 ou o criterio do 2/3 foram atendidos entao sao linhas internas do grid do cubo.    
                    if ok1>0 and ok2>0:
                        #ok these are inner lines of grid
                        #flip if necessary
                        #inverte os pontos inicial e final somente se o criterio dos 2/3 foi atendido, e nessa inversao a reta fica sendo como se tivesse atendido o criterio do 1/3
                        if ok1 == 2: 
                            p1,p2=p2,p1

                        if ok2 == 2:
                            q1,q2=q2,q1
                        
                        #both lines now go from p1->p2, q1->q2 and 
                        #intersect at 1/3
                        #calculate IT
                        z1=(q1[0]+2.0/3*(p2[0]-p1[0]),q1[1]+2.0/3*(p2[1]-p1[1]))
                        z2=(p1[0]+2.0/3*(q2[0]-q1[0]),p1[1]+2.0/3*(q2[1]-q1[1]))
                        z=(p1[0]-1.0/3*(q2[0]-q1[0]),p1[1]-1.0/3*(q2[1]-q1[1]))
                        
                        #armazena z(representando o ponto de inteseccao entre as retas p1p2 e q1q2, como a origem de um novo segmento)
                        #z1(representa o ponto de fim do segmento z-z1, que é um espelho da reta p1p2) distancia de p1 a p2
                        #z2(representa o ponto de fim do segmento z-z2, que é um espelho da reta q1q2)
                        #na pratica se as retas se intersectam esta movendo o ponto de intersecção dessas retas para ser a origem comum de p1p2 e q1q2, movendo elas 
                        #1/3 para tras (por isso o negativo), para se tornarem os contornos externos do cubo(canto mais proximo do cubo)
                        #desenhe o cubo geometricamente em forma de xis e plote os pontos e vera que o codigo esta transformando as linhas internas a distancia 1/3 da borda do cubo 
                        #em linhas de contorno externo do cubo que se intersectam na origem em comum entre elas.
                        IT=(z,z1,z2,dd1)
                        matched=1
            
            #only single one matched!! Could be corner
            #agora que encontrou ou configurou as retas para se intersectarem nas extremidades, faz as validacoes dos dois angulos possiveis entre as duas retas
            #para verificar se nao sao paralelas (diferenca do maior angulo e o valor perpendicular 90 graus tem que ser menor que 0,5 radianos(ou 30 graus) )
            if matched==1:
                
                #also test angle (em relacao ao eixo horizontal)
                #em radianos(multiplos reais de pi)
                a1 = atan2(p2[1]-p1[1],p2[0]-p1[0])
                a2 = atan2(q2[1]-q1[1],q2[0]-q1[0])
                
                #se o angulo estiver nos quadrantes 3 ou 4 do circulo trigonometrico, somar pi leva o valor para o quadrante diagonalmente oposto,
                #onde seno e cosseno do angulo se tornam positivos, ao somar pi o valor vai para a extremidade oposta do diametro do circulo trigonometrico que contem o ponto definido
                #por esse angulo.
                #tangente de um angulo negativo: tangente é uma função impar, logo a tangente tera um valor negativo
                if a1 < 0:
                    a1 += pi
                
                if a2 < 0:
                    a2 += pi
                
                #o menor angulo entre duas retas sempre é menor ou igual 90 graus
                #o maior angulo entre duas retas sempre esta entre 90 e 180 graus
                #aqui esta usando a logica do maior angulo, ao somar 180 ao angulo negativo e subtrair o angulo positivo da outra reta, obtemos o maior angulo entre as retas
                #fica facil de ver geometricamente, ao desenhar retas que se intesectam com inclinacoes de 30 graus positivas e negativas em relacao ao eixo horizontal
                ang = abs(abs(a2-a1)-pi/2)
                
                #analisando os extremos do maior angulo(90 e 180)
                #180 - 90 = 90 = 1,57 (retas totalmente paralelas)
                #90 - 90 = 0 (retas totalmente perpendiculares)
                #0,5 em radianos é igual a aproximadamente 30 graus
                #se a diferenca entre o maior angulo(de 90 ate 180) e o valor 90 graus, for maior que 30 graus(maior angulo aumentando e entao retas ficando paralelas)
                #nao entrara na conta do to try. Isso ocorre quando o maior angulo entre as duas retas for maior que 120 graus.
                #resumindo se a diferenca entre o maior angulo entre as duas retas e o menor valor possivel para esse angulo que é de 90 graus as retas são adicionadas, pois
                #nao sao paralelas 
                if ang < 0.5:
                    totry.append(IT)
    
    
    #now check if any points in totry are consistent!
    res=[]
    for i in range(len(totry)):
        #aqui ja sao as retas do contorno externo do cubo, candidatas a serem cantos que virarão o eixo de coordenadas do cubo
        p,p1,p2,dd=totry[i]
        a1 = atan2(p1[1]-p[1],p1[0]-p[0])
        a2 = atan2(p2[1]-p[1],p2[0]-p[0])
        if a1<0:a1+=pi
        if a2<0:a2+=pi
        dd=1.7*dd
        evidence=0
        
        #affine transform to local coords
        #transformacao afim para coordenadas locais
        #matriz afim(matriz dos coeficientes) utilizada em conjunto com a matriz coluna das incognitas, 
        #no gonzalez ele usa matriz linha das incognitas, logo a matriz afim é transposta na tabela do gonzalez no cap2
        #os vetores tem como origem comum p(que é a origem do sistema de coordenadas), p2 é o extremo final no eixo x, e p1 é o extremo final no eixo y
        A = matrix([[p2[0]-p[0], p1[0]-p[0], p[0]],
                    [p2[1]-p[1],p1[1]-p[1],p[1]],
                    [0,0,1]])
        
        #calcula a inversa da matriz obtida usando o metodo I (I de inversa) que vem junto com a matrix do numpy
        Ainv= A.I 
        
        #matriz das incognitas, no caso os valores de p1. Aqui é utilizada matriz coluna das incognitas, 
        #no gonzalez em vez disso é usado matriz linha e a matriz dos coeficientes é transposta em relação a matriz dos coeficientes 'A' aqui utilizada.
        v=matrix([[p1[0]],[p1[1]],[1]])
        
        #check likelihood of this coordinate system. iterate all lines
        #and see how many align with grid
        #aqui testa cada linha de hough detectada, projetando no novo sistema de coordeandas e verifica se atende
        for j in range(len(houghLines)):
        
            #test angle consistency with either one of the two angles
            #recupera o angulo da linha de hough em relação a horizontal positiva
            a = angs[j]

            #difenrença entre o angulo da linha atual no plano da imagem e a linha que é o eixo vertical do sistema de coordenadas
            ang1=abs(abs(a-a1)-pi/2)

            #difenrença entre o angulo da linha atual no plano da imagem e a linha que é o eixo horizontal do sistema de coordenadas
            ang2=abs(abs(a-a2)-pi/2)

            #0.1 em radianos é igual a aproximadamente 6 graus
            #esta comparando se as retas detectadas se alinham com as retas que são os eixos de coordenadas do cubo
            #se se alinham (menores que 6 graus) nos mantemos na mesma iteração, 
            #se a diferença entre os angulos são maiores que 6 graus entao pulamos pra proxima iteração
            if ang1 > 0.1 and ang2>0.1: 
                continue
            
            #a partir daqui sabemos que a linha da iteração atual se alinha com as linhas que sao candidatas a sistema de coordenadas do cubo
            #agora vamos aplicar a matriz inversa nelas e projetar no sistema de coordenadas do cubo pra ver se adequam em questao de tamanho
            #se se adequarem quer dizer que sao linhas do grid interno do cubo.

            #test position consistency.
            #ponto de origem da linha hough atual
            q1 = [houghLines[j][0][0], houghLines[j][0][1]]
            
            #ponto de fim da linha hough atual
            q2 = [houghLines[j][0][2], houghLines[j][0][3]]
            
            qwe=0.06
            
            #test one endpoint
            #matrix das incognitas
            v=matrix([[q1[0]],[q1[1]],[1]])

            #project it
            #vp é a projeção do ponto q1 do plano da imagem no sistema de coordenadas local
            #O resultado vp é um vetor coluna que representa as coordenadas do ponto projetado no novo sistema de coordenadas.
            #Ex: vp = | x |
            #         | y |
            #         | 1 |
            #onde x e y são as novas coordenadas do ponto no sistema de coordenadas do cubo
            vp=Ainv*v; 
            
            #como vp é um objeto matrix do numpy, logo deve ser acessada como se fosse uma matriz 2d(linhas e colunas)
            #vp[0,0] entao refere-se ao elemento na primeira linha e primeira coluna, que no caso é o x do vetor coluna 
            #vp[1,0] entao refere-se ao elemento na segunda linha e primeira coluna, que no caso é o y do vetor coluna
            #no novo sistema de coordenadas os eixos vao de 0 ate no maximo 1, logo se alguma coordenada x ou y do ponto da linha
            #sair fora desse intervalo, ele não pertence ao grid do cubo, não é uma linha interna do cubo. A precisao de ponto flutuante é 0.1 aqui, por isso o 1.1 e o -0.1.
            if vp[0,0] > 1.1 or vp[0,0]<-0.1: 
                continue
            if vp[1,0] > 1.1 or vp[1,0]<-0.1: 
                continue

            #entenda que para serem do grid as linhas precisam estar paralelas aos eixos nas posicoes(distancia em relacao a origem do eixo) 1/3 e 2/3 tanto na direção do eixo x
            #quanto na direção eixo y
            #aqui verificamos se todas as coordenadas do ponto estao fora das posicoes 1/3 e 2/3 do cubo
            #se alguma coordenada estiver na posicao correta significa que o ponto pertence ao grid, pois está em alguma das posicões corretas, e nao pula a iteração
            #qwe aqui é a precisao de ponto flutuante utilizada, quanto menor mais preciso devem ser as distancias, e mais dificil se torna a detecçao pois precisa se bem exato.
            if abs(vp[0,0]-1/3.0)>qwe and abs(vp[0,0]-2/3.0)>qwe and \
                abs(vp[1,0]-1/3.0)>qwe and abs(vp[1,0]-2/3.0)>qwe: 
                continue
            
            #the other end point
            #mesmas validações para o outro ponto da reta, lembrando que projetamos no novo sistema de coordenadas as duas extremidades(pontos)
            #de cada segmento detectado pela transformada de Hough. Aqui esta sendo feitas as validações para o segundo ponto da linha da iteração atual.
            #lembre-se segmentos sao representados por dois pontos em geometria computacional
            v=matrix([[q2[0]],[q2[1]],[1]])
            vp=Ainv*v;

            if vp[0,0] > 1.1 or vp[0,0]<-0.1: 
                continue
            if vp[1,0] > 1.1 or vp[1,0]<-0.1: 
                continue
            if abs(vp[0,0]-1/3.0)>qwe and abs(vp[0,0]-2/3.0)>qwe and \
                abs(vp[1,0]-1/3.0)>qwe and abs(vp[1,0]-2/3.0)>qwe: 
                continue

            #indica que os dois extremos projetados da linha atual atenderam as condições e logo a reta faz parte do grid interno
            #resumindo a variavel evidence, indica quantas retas fazem parte do grid interno do cubo
            evidence+=1
        
        #print evidence
        #armazena a quantidade de linhas que fazem parte do grid interno do cubo, e o ponto de origem p dos dois eixos e o ponto de fim p2 do eixo x, e o ponto de fim p1 do eixo y 
        res.append((evidence, (p,p1,p2)))
    
    #minimal change (usado para verificar a mudança de deslocamento medio dos pontos do grid anterior detectado e do novo)
    minch=10000
    
    #ordena a lista de sistemas de coordenadas candidatos obtida acima pelo numero de segmentos de linha que se alinham em cada um deles
    #segundo o andrej, os primeiros sistemas de coordenadas nesta listagem sempre serão valores altos e quase iguais de detecção de segmentos de linha que se alinham com eles
    #Isso se deve ao fato de que os 4 primeiros dessa lista correspondem aos sistemas de coordenadas dos 4 cantos do cubo.
    try:
        res.sort(reverse=True)
    except TypeError as e:
        #print("Erro: ", str(e))
        #print("lista res: ", res)
        res=[]
    
    #somente executa se a lista de sistema de coordenadas obtida é maior que zero
    if len(res)>0:
        minps=[]
        pt=[]
        #among good observations find best one that fits with last one
        for i in range(len(res)):
            #somente itera sobre os sistemas de coordenadas que tiveram numero de linhas que se 
            #alinharam com os eixos maior do que 2 (5% do total de linhas detectadas na transformada de hough)
            if res[i][0]>0.05*dects:
                #OK WE HAVE GRID
                p,p1,p2=res[i][1]
                
                #soma vetorial de p1 e p2
                #essa soma vetorial só é válida porque os dois pontos tem como origem a coordenada (0,0) do sistema de coordenadas, caso contrario precisaria subtrair a origem 
                #de cada coordenada de cada ponto do vetor
                p1p2 =(p2[0]+p1[0], p2[1]+p1[1])

                #p3 é o vetor que vai da origem(p) ate o ponto final que é soma vetorial de p2 e p1( que se trata da coordenada (1,1) do sistema de coordenadas do cubo)
                #lembrando que o sistema de coordenadas do cubo vai de 0 ate 1 para cada eixo
                #resumindo p3 que leva de p0 ate p1+p2
                #p3= (p2[0]+p1[0]-p[0], p2[1]+p1[1]-p[1])
                p3 = vect(p, p1p2)

                #aqui é criada a lista de pontos que representam os cantos do sistema de coordenadas do cubo
                w=[p,p1,p2,p3]

                #soma vetorial de p1 com p2
                #essa soma vetorial só é válida porque os dois pontos tem como origem a coordenada (0,0) do sistema de coordenadas, caso contrario precisaria subtrair a origem 
                #de cada coordenada de cada ponto do vetor
                p1p2 = (prevface[2][0] + prevface[1][0], prevface[2][1]+prevface[1][1])

                #inicialmente o codigo instancia prevface da seguinte forma: prevface=[(0,0),(5,0),(0,5)]
                #prevface sempre será uma lista com tres pontos, sendo o primeiro a origem do sistema de coordenadas
                #o segundo ponto o extremo final do eixo x, e o terceiro o extremo final do eixo y, ambos os eixos tem a origem como ponto inicial
                #p3= (prevface[2][0]+prevface[1][0]-prevface[0][0], 
                #    prevface[2][1]+prevface[1][1]-prevface[0][1])
                
                #vetor que vai da origem p ate a soma vetorial dos eixos x (origem p ate p1) e eixo y (origem p ate p2)
                p3 = vect(prevface[0], p1p2) 

                #to compute
                tc= (prevface[0],prevface[1],prevface[2],p3)

                #passa para o metodo a lista w com os pontos do sistema de coordenada detectado, e a lista tc das faces anteriormente detectadas
                #face aqui é definida como uma tupla que contem os 4 pontos do sistema de coordenadas que representam os 4 cantos do cubo em sentido antihorario a partir da origem
                #do sistema de coordenadas (canto inferior esquerdo do cubo)
                #change (deslocamento medio em relação a face anterior detectada)
                ch=compfaces(w,tc)
                
                #se teve mudança de deslocamento de uma face detectada para outra, armazena o menor valor de deslocamento e armazena os pontos que provocaram esse deslocamento
                #aqui estamos tentando encontrar o grid que é menos diferente em questao de distancia em relação ao detectado anteriormente, porque quanto menor a distancia
                #maior é a chance de estarmos tratando do mesmo grid, que foi detectado do zero antes e agora foi detectado novamente.
                if ch<minch:
                    minch=ch
                    minps= (p,p1,p2)

        #blz, agora se minps tem o grid detectado atual que é o mesmo grid detectado do zero anterior, o grid atual passa a ser o grid anterior para a proxima iteração do loopPrincipal
        if len(minps)>0:
            prevface=minps
            #print minch
            
            #se minimal change(deslocamento medio dos pontos do grid atual em relacao ao grid anterior) for menor que 10, consideraremos o grid atual como 
            #o mesmo grid detectado anteriormente
            if minch<10:
                #good enough!
                #a variavel succ conta o numero de vezes que encontramos o mesmo grid do zero, se esse numero for pelo menos 3 afirmaremos que esse grid não é um erro de 
                #detecção e inicializaremos o rastreameno Lucas-Kanade Optical Flow.
                succ+=1
                #a variavel pt recebe os pontos do grid atual
                pt=prevface
                #detectamos com sucesso o grid do cubo e a variavel detected é passada para 1
                detected=1
                
        else:
            succ=0
        
        #we matched a few times same grid
        #coincidence? I think NOT!!! Init LK tracker
        #a variavel succ conta o numero de vezes que encontramos o mesmo grid do zero, se esse numero for pelo menos 3 afirmaremos que esse grid não é um erro de 
        #detecção e inicializaremos o rastreameno Lucas-Kanade Optical Flow.
        if succ > 1:
            #initialize features for LK
            pt=[]
            #aqui para realizar o rastreio lucas kanade usa o ponto p (origem do sistema de coordenadas) e os vetores v1 e v2 que representam os eixos do sistema de coordenadas
            #onde v1 é o vetor que vai da origem até o ponto p1 (1, 0) do sistema de coordenadas.
            #onde v2 é o vetor que vai da origem até o ponto p2 (0, 1) do sistema de coordenadas.
            #a ideia é armazenar pt as posições das quatro cruzes que ficam no canto do sticker do centro
            #para isso movemos a origem usando os vetores dos eixos do sistema coordenadas por meio de combinação linear, onde as cruzes estao a 1/3 e 2/3 de cada eixo.
            #pt entao armazenara as cruzes do cubo de Rubik
            for i in [1.0/3, 2.0/3]:
                for j in [1.0/3, 2.0/3]:
                    pt.append((p0[0]+i*v1[0]+j*v2[0], p0[1]+i*v1[1]+j*v2[1]))
            
            #refine points slightly
            #quando for detectada tres vezes o cubo, passamos para o modo rastreamento no qual o lucas-kanade vai rastrear continuamente os pontos que detectamos
            #a cada novo frame do video, aqui armazenamos em features os 4 pontos das cruzes do cubo de Rubik, em relação ao sistema de coordenadas atual,
            #para que na proxima iteração o lucas-kanade pegue o frame antigo e o atual e esse conjunto de pontos das cruzes como pontos antigos e consiga 
            #calcular os novos pontos e manter o rastreamento ativo.
            features=pt
            tracking=1
            succ=0

def processInformedCharacter(c, cc):
    global selected, didassignments, assigned, extract, colors, dodetection, hsvs, onlyBlackCubes

    if 32 <= c and c < 128:
        cc = chr(c).lower()
    if cc== ' ':
        #EXTRACT COLORS!!!
        extract=True
    if cc=='r':
        #reset
        extract=False
        selected=0
        colors=[[] for i in range(6)]
        didassignments=False
        assigned=[[-1 for i in range(9)] for j in range(6)]
        for i in range(6):
            assigned[i][4]=i    
        didassignments=False
        
    if cc=='n':
        selected=selected-1
        if selected<0: selected=5
    if cc=='m':
        selected=selected+1
        if selected>5: selected=0
    
    if cc=='b':
        pass
        #onlyBlackCubes=not onlyBlackCubes
    if cc=='d':
        dodetection=not dodetection
    if cc=='q':
        print(colors)
    if cc=='p':
        #process!!!!
        processColors()
        try:
            strCoresFace = carregaStringCoresParaResolucao()
            solution = executaResolucaoCubo(strCoresFace)
            enviaParaArduino(solution)
        except Exception as e:
            print("Erro na execucao da resolucao, tente novamente: "+str(e))
    if cc=='u':
        didassignments=not didassignments
    if cc=='s':
        cv2.imwrite("C:\\ambiente\\pic"+str(time())+".jpg",sgc)

def carregaStringCoresParaResolucao():
    global assigned
    strCoresFace = []
    arrayStrCores = ["o", "g", "r", "b", "y", "w"]
    for i in range(6):
        strCores = ""
        for j in range(9):
            stickerFaceNumber = assigned[i][j]
            
            for faceIndex in range(6):
                if stickerFaceNumber == faceIndex:
                    strCores += arrayStrCores[faceIndex]
                    break

        strCoresFace.append(strCores)
    print("String de cores para resolução: ", strCoresFace)
    return strCoresFace
#realiza o mapeamento da configuração do cubo na deteccao por visao computacional para
#a detecção da configuração do cubo para a resolução kociemba
#Detecção por visão computacional: o topo deve ser a face amarela e voltada para frente da pessoa deve estar a face laranja
#Resolução Kociemba: o topo deve ser a face branca e voltada para para frente da pessoa deve estar a face verde
def executaResolucaoCubo(strCoresFace):
    strCoresMapeadas = []
    strCoresMapeadas.append(strCoresFace[5][::-1])
    strCoresMapeadas.append(strCoresFace[2][::-1])
    strCoresMapeadas.append(strCoresFace[1][::-1])
    strCoresMapeadas.append(strCoresFace[4])
    strCoresMapeadas.append(strCoresFace[0][::-1])
    strCoresMapeadas.append(strCoresFace[3][::-1])

    cubeDefinitionString = ""
    
    for faceStr in strCoresMapeadas:
        cubeDefinitionString += faceStr 

    #cubeDefinitionString = str(cubeDefinitionString)
    print(cubeDefinitionString)

    cubeDefinitionString = cubeDefinitionString.replace("y", "D")
    cubeDefinitionString = cubeDefinitionString.replace("g", "F")
    cubeDefinitionString = cubeDefinitionString.replace("w", "U")
    cubeDefinitionString = cubeDefinitionString.replace("r", "R")
    cubeDefinitionString = cubeDefinitionString.replace("o", "L")
    cubeDefinitionString = cubeDefinitionString.replace("b", "B")

    print(len(cubeDefinitionString))
    print(cubeDefinitionString)
    solution = kociemba.solve(cubeDefinitionString)
    print(solution)
    return solution

def abriConexaoSerialArduino():
    porta = 'COM5'
    velocidadeBaud = 115200

    print("Conectando na porta serial do Arduino")
    SerialArduino = serial.Serial(porta, velocidadeBaud, timeout=0.2)
    print("Conexao estabelecida!")

    lerSerialThread = threading.Thread(target = arduinoEvent, args=(SerialArduino,))
    lerSerialThread.start()
    return SerialArduino


def arduinoEvent(serialObj):
    while True:
        try: 
            reading = serialObj.readline().decode("utf-8")
            if reading != "":
                print("Dados recebidos: " + reading)
            if endArduinoEvent:
                break
        except:
            print("Encerrando thread de leitura continua da porta serial!");
            break

def enviaParaArduino(solution):

    global SerialArduino
    solution = str(solution).replace(" ", "")
    print(solution)
    print("Enviando solução para Arduino")
    try:
        solution += '\n'
        SerialArduino.write(solution.encode("utf-8"))
        time.sleep(2)
    except Exception as e:
        print("Erro ao enviar para o Arduino. Tente novamente:", str(e))

main()

endArduinoEvent = True