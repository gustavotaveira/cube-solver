#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver board1 = Adafruit_PWMServoDriver(0x40);       // called this way, it uses the default address 0x40   
  
#define SERVOMIN  125                                                 // this is the 'minimum' pulse length count (out of 4096)
#define SERVOMAX  625                                                 // this is the 'maximum' pulse length count (out of 4096)

int ROTATE_FRONT_SERVO = 8;
int TRANSLATE_FRONT_SERVO = 11;
  
int ROTATE_LEFT_SERVO = 12;
int TRANSLATE_LEFT_SERVO = 15;
  
int ROTATE_RIGHT_SERVO = 4;
int TRANSLATE_RIGHT_SERVO = 7;
  
int ROTATE_BACK_SERVO = 0;
int TRANSLATE_BACK_SERVO = 3;

int pos;

const int DELAY_DEFAULT = 900;
//garras ajustadas para que o angulo 70 seja sua posição inicial
const int ANGLE_DEFAULT = 70;
const int ANGLE_HORARIO = 165;
const int ANGLE_HORARIO2 = 175;
const int ANGLE_ANTIHORARIO = 55;
const int ANGLE_MAX_TRANSLATE_FRONT_SERVO = 130;

String inputString = "";
bool stringComplete = false;

void setup() {
  Serial.begin(115200);
  inputString.reserve(200);
  
  board1.begin();
  board1.setPWMFreq(60);                  // Analog servos run at ~60 Hz updates

  //calibrando servos para suas posições iniciais
  digitalWrite(TRANSLATE_FRONT_SERVO, ANGLE_MAX_TRANSLATE_FRONT_SERVO);
  digitalWrite(TRANSLATE_LEFT_SERVO, 180);
  digitalWrite(TRANSLATE_RIGHT_SERVO, 180);
  digitalWrite(TRANSLATE_BACK_SERVO, 180);

  delay(2000);
 
  digitalWrite(ROTATE_FRONT_SERVO, ANGLE_DEFAULT);
  digitalWrite(ROTATE_LEFT_SERVO, ANGLE_DEFAULT);
  digitalWrite(ROTATE_RIGHT_SERVO, ANGLE_DEFAULT);
  digitalWrite(ROTATE_BACK_SERVO, ANGLE_DEFAULT);

  delay(2000);
}

void write(int servo, int angle){
  digitalWrite(servo, angle);  
}

void agarrarCubo(){
  write(TRANSLATE_FRONT_SERVO, 0);
  write(TRANSLATE_LEFT_SERVO,0);
  write(TRANSLATE_RIGHT_SERVO,0);
  write(TRANSLATE_BACK_SERVO,0);
  delay(2000);  
}

void soltarCubo(){
  write(TRANSLATE_FRONT_SERVO, ANGLE_MAX_TRANSLATE_FRONT_SERVO);
  write(TRANSLATE_LEFT_SERVO, 180);
  write(TRANSLATE_RIGHT_SERVO, 180);
  write(TRANSLATE_BACK_SERVO, 180);
  delay(DELAY_DEFAULT);
}

//s5 - ROTATE_RIGHT_SERVO
void rightHorario(){
  write(ROTATE_BACK_SERVO, ANGLE_DEFAULT);
  write(ROTATE_FRONT_SERVO, ANGLE_DEFAULT);
  write(ROTATE_RIGHT_SERVO, ANGLE_HORARIO);
  delay(DELAY_DEFAULT);
  rightParaTras();
  write(ROTATE_RIGHT_SERVO, ANGLE_DEFAULT);
  delay(DELAY_DEFAULT);
  rightParaFrente();
}

//s3 rotate front
void frontHorario(){
  //write(TRANSLATE_LEFT_SERVO, 60);
  //write(TRANSLATE_RIGHT_SERVO, 60);
  //delay(500);
  //write(ROTATE_FRONT_SERVO, 10);
  //delay(DELAY_DEFAULT);
  //write(ROTATE_FRONT_SERVO, 40);
  //delay(DELAY_DEFAULT);
  //write(ROTATE_FRONT_SERVO, 70);
  //delay(DELAY_DEFAULT);
  //write(ROTATE_FRONT_SERVO, 100);
  //delay(DELAY_DEFAULT);
  //write(ROTATE_FRONT_SERVO, 120);
  //delay(DELAY_DEFAULT);
  //write(ROTATE_FRONT_SERVO, 80);
  //delay(DELAY_DEFAULT);
  write(ROTATE_RIGHT_SERVO, ANGLE_DEFAULT);
  write(ROTATE_LEFT_SERVO, ANGLE_DEFAULT);
  write(ROTATE_FRONT_SERVO, ANGLE_HORARIO);
  delay(DELAY_DEFAULT);
  //write(TRANSLATE_LEFT_SERVO, 0);
  //write(TRANSLATE_RIGHT_SERVO, 0);
  frontParaTras();
  write(ROTATE_FRONT_SERVO, ANGLE_DEFAULT);
  delay(DELAY_DEFAULT);
  frontParaFrente();
}

//s7 rotate back
void backHorario(){ 
  write(ROTATE_RIGHT_SERVO, ANGLE_DEFAULT);
  write(ROTATE_LEFT_SERVO, ANGLE_DEFAULT);
  write(ROTATE_BACK_SERVO, ANGLE_HORARIO2);
  delay(DELAY_DEFAULT);
  backParaTras();
  write(ROTATE_BACK_SERVO, ANGLE_DEFAULT);
  delay(DELAY_DEFAULT);
  backParaFrente();
}

//s9 rotate left
void leftHorario(){
  write(ROTATE_BACK_SERVO, ANGLE_DEFAULT);
  write(ROTATE_FRONT_SERVO, ANGLE_DEFAULT);
  write(ROTATE_LEFT_SERVO, ANGLE_HORARIO2);
  delay(DELAY_DEFAULT);
  leftParaTras();
  write(ROTATE_LEFT_SERVO, ANGLE_DEFAULT);
  delay(DELAY_DEFAULT);
  leftParaFrente();
}

//s6 translate back
void backParaTras(){
  //---ajuste para não deixar a garra puxar o cubo
  write(ROTATE_LEFT_SERVO, 80);
  //delay(DELAY_DEFAULT);

  //-------------------------------------------
  write(TRANSLATE_BACK_SERVO, 180);
  delay(DELAY_DEFAULT);
  //voltando ajuste para posicao original
  write(ROTATE_LEFT_SERVO, ANGLE_DEFAULT);
  //delay(DELAY_DEFAULT);
  //-------------------------------------------
}

//S4 - TRANSLATE_RIGHT_SERVO
void rightParaTras(){
  //---ajuste para não deixar a garra puxar o cubo
  write(ROTATE_BACK_SERVO, 80);
  //delay(DELAY_DEFAULT);
  //-------------------------------------------
  write(TRANSLATE_RIGHT_SERVO, 180);
  delay(DELAY_DEFAULT);
  //-------------------------------------------
  //voltando ajuste para posicao original
  write(ROTATE_BACK_SERVO, ANGLE_DEFAULT);
  //delay(DELAY_DEFAULT);
  //-------------------------------------------
}

void frontParaTras(){
  //---ajuste para não deixar a garra puxar o cubo
  write(ROTATE_LEFT_SERVO, 80);
  //delay(DELAY_DEFAULT);
  //-------------------------------------------
  write(TRANSLATE_FRONT_SERVO, ANGLE_MAX_TRANSLATE_FRONT_SERVO);
  delay(DELAY_DEFAULT);  
  //-------------------------------------------
  //voltando ajuste para posicao original
  write(ROTATE_LEFT_SERVO, ANGLE_DEFAULT);
  //delay(DELAY_DEFAULT);
  //-------------------------------------------
}


//s8 translate left
void leftParaTras(){
  //---ajuste para não deixar a garra puxar o cubo
  write(ROTATE_BACK_SERVO, 55);
  //write(ROTATE_FRONT_SERVO, 80);
  //delay(DELAY_DEFAULT);
  //-------------------------------------------
  write(TRANSLATE_LEFT_SERVO, 180);
  delay(DELAY_DEFAULT);
  //-------------------------------------------
  //voltando ajuste para posicao original
  write(ROTATE_BACK_SERVO, ANGLE_DEFAULT);
  //write(ROTATE_FRONT_SERVO, ANGLE_DEFAULT);
  //delay(DELAY_DEFAULT);
  //-------------------------------------------
}


void rightParaFrente(){
  write(TRANSLATE_RIGHT_SERVO, 0);
  delay(DELAY_DEFAULT);
}

void rightNaHorizontal(){
  rightParaTras();
  write(ROTATE_RIGHT_SERVO, ANGLE_DEFAULT);
  delay(DELAY_DEFAULT);
  write(ROTATE_RIGHT_SERVO, ANGLE_HORARIO);
  delay(DELAY_DEFAULT);
  rightParaFrente();
}

void rightNaVertical(){
  rightParaTras();
  write(ROTATE_RIGHT_SERVO, ANGLE_DEFAULT);
  delay(DELAY_DEFAULT);
  rightParaFrente();
}

void rightAntihorario(){ 
  rightParaTras();
  write(ROTATE_RIGHT_SERVO, 160);
  delay(DELAY_DEFAULT);
  rightParaFrente();
  write(ROTATE_RIGHT_SERVO, 55);
  delay(DELAY_DEFAULT);  
}

void frontAntihorario(){
  frontParaTras();
  write(ROTATE_FRONT_SERVO, 160);
  delay(DELAY_DEFAULT);
  frontParaFrente();
  write(ROTATE_RIGHT_SERVO, ANGLE_DEFAULT);
  write(ROTATE_LEFT_SERVO, ANGLE_DEFAULT);
  //write(TRANSLATE_LEFT_SERVO, 60);
  //write(TRANSLATE_RIGHT_SERVO, 60);
  //delay(500);
  write(ROTATE_FRONT_SERVO, 55);
  //write(TRANSLATE_LEFT_SERVO, 0);
  //write(TRANSLATE_RIGHT_SERVO, 0);
  delay(DELAY_DEFAULT);
  write(ROTATE_FRONT_SERVO, ANGLE_DEFAULT);
}

void leftAntihorario(){
  leftParaTras();
  write(ROTATE_LEFT_SERVO, 160);
  delay(DELAY_DEFAULT);
  leftParaFrente();
  write(ROTATE_LEFT_SERVO, 55);
  delay(DELAY_DEFAULT);
}

void backAntihorario(){
  backParaTras();
  write(ROTATE_BACK_SERVO, 160);
  delay(DELAY_DEFAULT);
  backParaFrente();
  write(ROTATE_BACK_SERVO, 55);
  delay(DELAY_DEFAULT);
}

//s3 - rotate front
void frontNaHorizontal(){
  frontParaTras();
  write(ROTATE_FRONT_SERVO, ANGLE_HORARIO);
  delay(DELAY_DEFAULT);
  frontParaFrente();
}

void frontNaVertical(){
  frontParaTras();
  write(ROTATE_FRONT_SERVO, ANGLE_DEFAULT);
  delay(DELAY_DEFAULT);
  frontParaFrente();
}
//s2 translate front
void frontParaFrente(){
   write(TRANSLATE_FRONT_SERVO, 0);
   //delay(1200);
   delay(DELAY_DEFAULT);  
}


void frontDuplo(){
  frontHorario();
  frontHorario();
}

void leftParaFrente(){
  write(TRANSLATE_LEFT_SERVO, 0);
  delay(DELAY_DEFAULT);
}

void backParaFrente(){
  write(TRANSLATE_BACK_SERVO, 0);
  delay(DELAY_DEFAULT);
}

void leftGarraNaHorizontalParaGirarSentidoHorario(){
  leftParaTras();
  write(ROTATE_LEFT_SERVO, ANGLE_HORARIO);
  delay(DELAY_DEFAULT);
  leftParaFrente();
}

//gira como se todo o cubo fosse R
void girarEixoXHorario(){
  leftGarraNaHorizontalParaGirarSentidoHorario();

  write(TRANSLATE_FRONT_SERVO, ANGLE_MAX_TRANSLATE_FRONT_SERVO);
  write(TRANSLATE_BACK_SERVO, 180);
  delay(DELAY_DEFAULT);

  write(ROTATE_RIGHT_SERVO, ANGLE_HORARIO);
  write(ROTATE_LEFT_SERVO, ANGLE_DEFAULT);
  delay(DELAY_DEFAULT);

  write(TRANSLATE_FRONT_SERVO, 0);
  write(TRANSLATE_BACK_SERVO, 0);
  delay(DELAY_DEFAULT);

  rightParaTras();
  write(ROTATE_RIGHT_SERVO, ANGLE_DEFAULT);
  delay(DELAY_DEFAULT);
  rightParaFrente();
}

void rightGarraNaHorizontalParaGirarNoSentidoAntihorario(){
  rightParaTras();
  write(ROTATE_RIGHT_SERVO, ANGLE_HORARIO);  
  delay(DELAY_DEFAULT);
  rightParaFrente();
}

void girarEixoXAntihorario(){
  rightGarraNaHorizontalParaGirarNoSentidoAntihorario();

  write(TRANSLATE_FRONT_SERVO, ANGLE_MAX_TRANSLATE_FRONT_SERVO);
  write(TRANSLATE_BACK_SERVO, 180);
  delay(DELAY_DEFAULT);

  write(ROTATE_RIGHT_SERVO,ANGLE_DEFAULT);
  write(ROTATE_LEFT_SERVO, ANGLE_HORARIO);
  delay(DELAY_DEFAULT);

  write(TRANSLATE_FRONT_SERVO, 0);
  write(TRANSLATE_BACK_SERVO, 0);
  delay(DELAY_DEFAULT);

  leftParaTras();
  write(ROTATE_LEFT_SERVO, ANGLE_DEFAULT);
  delay(DELAY_DEFAULT);
  leftParaFrente();
}

void downHorario(){
  girarEixoXHorario();
  frontHorario();
  girarEixoXAntihorario();
}

void downAntiHorario(){
  girarEixoXHorario();
  frontAntihorario();
  girarEixoXAntihorario();
}

void upHorario(){
  girarEixoXAntihorario();
  frontHorario();
  girarEixoXHorario();
}

void upAntiHorario(){
  girarEixoXAntihorario();
  frontAntihorario();
  girarEixoXHorario();
}
void downDuplo(){
  girarEixoXHorario();
  frontDuplo();
  girarEixoXAntihorario();
}

void upDuplo(){
  girarEixoXAntihorario();
  frontDuplo();
  girarEixoXHorario();
}


void executaResolucao(String stringSolucao){
  if(stringSolucao == NULL || stringSolucao.length() == 0){
   return;  
  }
  int contadorMovimentos = 0;
  for(int i = 0; i<stringSolucao.length(); i++){

     if(stringSolucao[i] == '\'' || stringSolucao[i] == '2'){
        continue;
     }
     contadorMovimentos++;
  }

  int parcial = 100/contadorMovimentos;
  int progresso = 0;
  
  for(int i = 0; i<stringSolucao.length(); i++){
     
     String avaliar= "A2";

     if(stringSolucao[i] == '\'' || stringSolucao[i] == '2'){
        continue;
     }
     
     progresso += parcial;
     Serial.println((String)"Progresso: "+progresso+"%");
     
     avaliar[0] = stringSolucao[i];
     avaliar[1] = '3';

    if((i+1) < stringSolucao.length()){
      if(stringSolucao[i+1] == '\'' || stringSolucao[i+1] == '2'){
        avaliar[1] = stringSolucao[i+1];
      } 
    }

    if (avaliar == "F3") {
        Serial.println("Executando F...");
        frontHorario();
    } else if (avaliar == "F'") {
        Serial.println("Executando F'...");
        frontAntihorario();
    } else if (avaliar == "F2") {
      Serial.println("Executando F2...");
       frontDuplo();
    } else if (avaliar == "R3") {
        Serial.println("Executando R...");
        rightHorario();
    } else if (avaliar == "R'") {
      Serial.println("Executando R'...");
        rightAntihorario();
    } else if (avaliar == "R2") {
        Serial.println("Executando R2...");
        rightHorario();
        rightHorario();
    } else if (avaliar == "B3") {
      Serial.println("Executando B...");
        backHorario();
    } else if (avaliar == "B'") {
        Serial.println("Executando B'...");
        backAntihorario();
    } else if (avaliar == "B2") {
      Serial.println("Executando B2...");
        backHorario();
        backHorario();
    } else if (avaliar == "L3") {
      Serial.println("Executando L...");
        leftHorario();
    } else if (avaliar == "L'") {
      Serial.println("Executando L'...");
        leftAntihorario();
    } else if (avaliar == "L2") {
        Serial.println("Executando L2...");
        leftHorario();
        leftHorario();
    } else if (avaliar == "U3") {
      Serial.println("Executando U...");
        upHorario();
    } else if (avaliar == "U'") {
      Serial.println("Executando U'...");
        upAntiHorario();
    } else if (avaliar == "U2") {
      Serial.println("Executando U2...");
        upDuplo();
    } else if (avaliar == "D3") {
      Serial.println("Executando D...");
        downHorario();
    } else if (avaliar == "D'") {
      Serial.println("Executando D'...");
        downAntiHorario();
    } else if (avaliar == "D2") {
      Serial.println("Executando D2...");
        downDuplo();
    }
  }
  Serial.write("Resolvido: 100%");
}

int angleToPulse(int ang){                             //gets angle in degree and returns the pulse width
     int pulse = map(ang,0, 180, SERVOMIN,SERVOMAX);  // map angle of 0 to 180 to Servo min and Servo max 
     //Serial.print("Angle: ");Serial.print(ang);
     //Serial.print(" pulse: ");Serial.println(pulse);
     return pulse;
}

void digitalWrite(int servo, int ang){
  board1.setPWM(servo, 0, angleToPulse(ang));
}

void loop() {
  delay(10000);
  if(stringComplete){
    agarrarCubo();
    //executaResolucao("R'DF2BLF'R'U2F2U2B2U'L2F2D2B2U'");
    executaResolucao(inputString);
    //executaCalibracao();
    soltarCubo();    
    inputString = "";
  }
  stringComplete = false;
}

void executaCalibracao(){
    frontHorario();
    delay(1000);
    frontAntihorario();
    delay(1000);
}

void serialEvent(){
  Serial.print("<Arduino: Evento serial recebido, lendo dados vindos da porta serial...>");
  while (Serial.available()){
    char inChar = (char)Serial.read();
    inputString += inChar;
    if(inChar == '\n'){
      stringComplete = true;
    }
  }
  Serial.print("Arduino: Dados lidos. String recebida: ");
  Serial.print(inputString);
}
