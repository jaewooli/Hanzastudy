import os
from colorama import Fore, Style

def main():
    stylex = Style.RESET_ALL
    while 1:
        a= os.getcwd()
        f= open(f"{a}\\Hanza.txt",'r',-1,"utf-8")
        cnt =0
        A = input(f"{Fore.GREEN}찾는 한자, 또는 그 뜻을 입력하세요 : {stylex}\n")
        if A =="H"or A=='h'or A=='help':
            print(f"{Fore.GREEN}리스트{stylex} : 전체 단어 리스트\n{Fore.GREEN}예시:) 집 가{stylex}\n")
        elif A=="리스트" or A=="list":
            B=f.read()
            listf = B.split("\n")[:-1]
            print(B)
            f.close()
        elif A=="break" or A=="종료":
            f.close()
            break
        else:
            listf = f.read().split("\n")
            for line in listf:
                cnt+=1
                if A in line:
                    linea = line.split(":")
                    lineb = str(linea[1])
                    linea = str(linea[0])
                    print(linea,lineb)
                    print('')
                    break
                if cnt ==len(listf):
                    print(f"{Fore.RED}해당 한자가 사전에 등록되어있지 않습니다. 사전에 등록해주세요.{stylex}\n")
            f.close()
            
def fileopen():
    try:
        a= os.getcwd()
        f= open(f"{a}\\Hanza.txt",'r',-1,"utf-8")
        listf = f.read().split("\n")
        return len(listf)-1, listf
    except: 
        return "",""