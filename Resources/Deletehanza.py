import os
import Downloadimage

def main():
    while 1:
        content = input("사전에서 삭제할 한자를 입력하세요.\n")
        if content =="H"or content=='h'or content=='help':
            print("사전에서 삭제할 한자를 입력해주세요!\n종료 : 한자 삭제를 종료합니다")
        elif content == "종료":
            break
        else:
            deletehanza(content)

def deletehanza(content):
    a= os.getcwd()
    hanzaimg, hanzamean = Downloadimage.searchhanza(content)
    f= open(f"{a}\\Hanza.txt",'r',-1,"utf-8")
    reading = f.readlines()
    f.close()
    is_readed = 0
    for line in range(len(reading)):
        if hanzaimg in reading[line]:
            print("해당 한자를 삭제합니다")
            print(hanzaimg,':',hanzamean,"\n")
            reading[line] = ""
            is_readed = 1
            """if line > 0:
                reading[line-1] = reading[line-1][:-1]"""
            break
    f=open(f"{a}\\Hanza.txt",'w',-1,"utf-8")
    for i in reading:
        f.write(i+'')
    if not is_readed:
        print('\r',end='',flush=True)
        print('  '*20, end='', flush=True)
        print('\r', end='', flush=True)
        print("해당 한자가 사전에 등록되어있지 않습니다.\n")