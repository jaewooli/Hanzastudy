import random
import time
import printhanza
import Downloadimage
import Deletehanza
import os, sys
from colorama import Fore, Style, init

init()
stylex = Style.RESET_ALL

is_breaking = 0
is_breaking2 = 0
is_download = 0
is_printimg = 0

def game():
    hanzalen, dontneed =printhanza.fileopen()
    hanzalist = [0]*hanzalen
    global is_breaking
    global is_breaking2
    global is_download
    global is_printimg
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
                if is_breaking ==1 :
                    break
                elif is_breaking ==0:
                    print(f"{Fore.GREEN}학습한 모든 한자를 복습했습니다!{stylex}")
                    is_breaking = 1
                    break
        if is_breaking:
            break
        Hanza = listf[r]
        Hanzamean = Hanza[3:]
        Hanzaimg = Hanza[0]
        print(Hanzaimg)
        A = input()
        if A == "등록" or A=="save" or A=="한자":
            is_download = 1
            break
        if A=="사전":
            is_printimg = 1
            break
        elif A=="종료"or A=="break":
            is_breaking2 = 1
            break
        elif A in Hanzamean:
            print(f"{Fore.GREEN}정답입니다!\n{stylex}")
        elif A not in Hanzamean:
            print(f"{Fore.RED}오답입니다{stylex}\n해당 한자의 뜻입니다. 정답이라고 하시겠습니까? {Fore.GREEN}Y{stylex}/{Fore.RED}N{stylex}")
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
                    print(f"{Fore.RED}Y 혹은 N을 입력해주세요{stylex}")
            print('')
        
    if is_download:
        Downloadimage.main()
    elif is_printimg:
        printhanza.main()
    elif is_breaking2:
        pass


def main():
    try:
        a= os.getcwd()
        f= open(f"{a}\\Hanza.txt",'r',-1,"utf-8")
        f.close()
    except:
        a= os.getcwd()
        f= open(f"{a}\\Hanza.txt",'x',-1,"utf-8")
        print(f"{Fore.GREEN}첫 설정을 하는 중입니다....{stylex}",end='',flush=True)
        for i in range(1,9):
            time.sleep(0.5)
            print('\r',end='',flush=True)
            print('  '*20, end='', flush=True)
            print('\r', end='', flush=True)
            print(f'{Fore.GREEN}첫 설정을 하는 중입니다'+'.'*(i%4)+stylex,end='',flush=True)
        print('\r',end='',flush=True)
        print(' ' *20, end='', flush=True)
        print('\r', end='', flush=True)
        print(f"{Fore.GREEN}설정이 완료 되었습니다!\n{stylex}")
        f.close()
                
    global is_breaking
    global is_breaking2
    global is_download
    global is_printimg

    while 1:
        is_breaking = 0
        is_breaking2 = 0
        is_download = 0
        is_printimg = 0
        A = input(f"무엇을 하시겠습니까?  {Fore.GREEN}(도움말 : help){stylex}\n게임 , 등록 , 사전 , 삭제 ,종료\n\n")
        if A =="H"or A=='h'or A=='help':
            print(f"{Fore.GREEN}\n게임 : 한자 맞추기 게임\n등록 : 학습한 한자 등록\n사전 : 학습한 한자 보기\n삭제 : 한자를 사전에서 삭제\n종료 : 프로그램을 종료합니다\n{stylex}")
        if A =='게임':
            print('')
            game()
        elif A =='등록':
            print('')
            Downloadimage.main()
        elif A=='사전':
            print('')
            printhanza.main()
        elif A=="삭제":
            print('')
            Deletehanza.main()
        elif A=='종료'or A=='^C':
            print("종료합니다")
            break


if __name__ == "__main__":
    main() 