import random
import time
import printhanza
import Downloadimage
import os

hanzalen, dontneed =printhanza.fileopen()
hanzalist = [0]*hanzalen
breaking = 0
breaking2 = 0
download = 0
printimg = 0

def game():
    global breaking
    global breaking2
    global download
    global printimg
    while 1:
        length, listf = printhanza.fileopen()
        while 1:
            if 0 in hanzalist:
                r = random.randrange(0,length)
                if hanzalist[r]:
                    continue
                else:
                    hanzalist[r]=1 
                    break
            elif 0 not in hanzalist:
                if breaking ==1 :
                    break
                elif breaking ==0:
                    print("학습한 모든 한자를 복습했습니다!")
                    breaking = 1
                    break
        if breaking:
            break
        Hanza = listf[r]
        Hanzamean = Hanza[3:]
        Hanzaimg = Hanza[0]
        print(Hanzaimg)
        A = input()
        if A == "등록" or A=="save" or A=="한자":
            download = 1
            break
        if A=="사전":
            printimg = 1
            break
        elif A=='ㅠ' or A=='b' or A=='B' or A=='break':
            breaking2 = 1
            break
        elif A in Hanzamean:
            print("정답입니다!\n")
            game()
        elif A not in Hanzamean:
            print("오답입니다\n해당 한자의 뜻입니다. 정답이라고 하시겠습니까? Y/N")
            print(Hanzamean)
            while 1:
                A= input()
                if A =="Y"or A=='y'or A=='ㅛ':
                    hanzalist[r] = 1
                    print('')
                    break
                elif A=='N'or A=="n"or A=='ㅜ':
                    hanzalist[r] =0
                    print('')
                    break
                else:
                    print("Y 혹은 N을 입력해주세요")
            print('')
            game()
        
    if download:
        Downloadimage.hanzasave()
    elif printimg:
        printhanza.findhanza()
    elif breaking2:
        pass


def main():
    try:
        a= os.getcwd()
        a+="\\Hanzastudy"
        f= open(f"{a}/Hanza.txt",'r',-1,"utf-8")
        f.close()
    except:
        a= os.getcwd()
        a+="\\Hanzastudy"
        f= open(f"{a}/Hanza.txt",'w',-1,"utf-8")
        print("첫 설정을 하는 중입니다....",end='',flush=True)
        for i in range(1,9):
            time.sleep(1)
            print('\r',end='',flush=True)
            print('  '*20, end='', flush=True)
            print('\r', end='', flush=True)
            print('첫 설정을 하는 중입니다'+'.'*(i%4),end='',flush=True)
        print('\r',end='',flush=True)
        print(' ' *20, end='', flush=True)
        print('\r', end='', flush=True)
        print("설정이 완료 되었습니다!\n")
        f.close()
                
    global breaking
    global breaking2
    global download
    global printimg
    while 1:
        breaking = 0
        breaking2 = 0
        download = 0
        printimg = 0
        A = input("무엇을 하시겠습니까?  (도움말 : help)\n게임 , 등록 , 사전 , 종료\n\n")
        if A =="H"or A=='h'or A=='help':
            print("\n게임 : 한자 맞추기 게임\n등록 : 학습한 한자 등록\n사전 : 학습한 한자 보기\n종료 : 프로그램을 종료합니다\n")
        if A =='게임':
            print('')
            game()
        elif A =='등록':
            print('')
            Downloadimage.hanzasave()
        elif A=='사전':
            print('')
            printhanza.findhanza()
        elif A=='종료':
            print("종료합니다")
            break


if __name__ == "__main__":
    main() 