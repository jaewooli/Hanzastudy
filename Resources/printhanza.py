import os

def findhanza():
    while 1:
        a= os.getcwd()
        a+="\\Hanzastudy"
        f= open(f"{a}/Hanza.txt",'r',-1,"utf-8")
        cnt =0
        A = input("찾는 한자, 또는 그 뜻을 입력하세요 :\n")
        if A =="H"or A=='h'or A=='help':
            print("리스트 : 전체 단어 리스트\n예시:) 집 가\n")
        elif A=="리스트" or A=="list":
            B=f.read()
            listf = B.split("\n")[:-1]
            print(B)
            f.close()
        elif A=="break" or A=="B":
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
                    print("해당 한자가 사전에 등록되어있지 않습니다. 사전에 등록해주세요.\n")
            f.close()
            
def fileopen():
    try:
        a= os.getcwd()
        a+="\\Hanzastudy"
        f= open(f"{a}/Hanza.txt",'r',-1,"utf-8")
        listf = f.read().split("\n")
        return len(listf)-1, listf
    except: 
        return 0,0