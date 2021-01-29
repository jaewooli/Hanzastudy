from bs4 import BeautifulSoup
import requests
import os
from colorama import Fore, Style

def does_save(hanzaimg,hanzamean,a):
    stylex = Style.RESET_ALL
    if a =="Y" or a=='y' or a=='ㅛ':
        a= os.getcwd()
        f= open(f"{a}\\Hanza.txt",'a',-1,"utf-8")
        f.write(f"{hanzaimg}: {hanzamean}\n")
        f.close()
        print(f'{Fore.GREEN}해당 한자를 저장합니다.{stylex}\n')
    elif a=="N" or a=='n' or a== 'ㅜ':
        pass
    else:
        a= input(f"{Fore.RED}Y 혹은 N 을 입력해주세요.{stylex}\n{Fore.GREEN}Y{stylex}/{Fore.GREEN}N{stylex} : ")
        does_save(hanzaimg,hanzamean,a)

def main():
    stylex = Style.RESET_ALL
    while 1:
        geaupsu = [8,7,6,5,4,3,2,1,0]
        hanza = u"{hanza}" .format(hanza = input(f"{Fore.GREEN}등록할 한자: {stylex}\n"))
        if hanza =='h' or hanza =="help" or hanza == "도움말":
            print(f"{Fore.GREEN}등록할 한자의 뜻을 입력해주세요!{stylex}\n{Fore.RED}나가기: 종료{stylex}")
        if hanza == '종료':
            break
        if hanza[-1]=='급' and len(hanza) ==2:
            if int(hanza[0]) in geaupsu:
                hanzasave2(int(hanza[0]),int(hanza[0]))
        else:
            hanzasave1(hanza)

def searchhanza(hanza):
    stylex = Style.RESET_ALL
    try:
        page = requests.get(f"https://hanja.dict.naver.com/search?query={hanza}")
        soup = BeautifulSoup(page.content, 'html.parser')
        hanzaimg =soup.find("div", {"class": "result_chn_chr"}).find("dl").find('dt').find('a').contents[0]
        hanzamean = soup.find("div", {"class": "result_chn_chr"}).find("dl").find('dd').find('a').find('span')
        try:
            hanzamean.b.unwrap()
        except:pass
        try:
            hanzamean.b.unwrap()
        except:pass
        try:
            hanzamean.b.unwrap()
        except:pass
        hanzamean = " ".join(hanzamean.contents)
        hanzamean = hanzamean.split(",")
        for i in range(len(hanzamean)):
            if hanzamean[i][-1]==" ":
                hanzamean[i]= hanzamean[i][:-1]
            if hanzamean[i][0]==" ":
                hanzamean[i]= hanzamean[i][1:]
        return hanzaimg, hanzamean
        
    except AttributeError:
            print(f'{Fore.RED}입력하신 한자를 찾을 수 없습니다.{stylex}',end='')
            return ";", ";"

def hanzasave1(hanza,group=1):
    stylex = Style.RESET_ALL
    a= os.getcwd()
    f= open(f"{a}\\Hanza.txt",'r',-1,"utf-8")
    if f'{hanza}' in f.read():
        print(f'{Fore.RED}해당 한자가 이미 저장되어 있습니다{stylex}')
        f.close()
    else:
        if group:
            hanzaimg, hanzamean = searchhanza(hanza)
            if type(hanzamean) != list:
                print('\n')
            else:
                if hanza not in hanzamean:
                    print(f"{Fore.RED}검색된 한자가 입력한 한자와 뜻이 다릅니다.{stylex}\n{Fore.GREEN}찾는 한자인가요?{stylex}")
                    print(hanzaimg)
                    print(",".join(hanzamean))
                    a =input(f"{Fore.GREEN}Y{stylex}/{Fore.RED}N{stylex} : ")
                    does_save(hanzaimg,hanzamean,a)
                else:
                    print(hanzaimg)
                    print(hanzamean)
                    a= input(f"{Fore.GREEN}저장할까요?\n\nY{stylex}/{Fore.RED}N{stylex} : ")
                    does_save(hanzaimg,hanzamean,a)
        else:
            hanzaimg, hanzamean = searchhanza(hanza)
            print(hanzaimg,':',hanzamean)
            a= os.getcwd()
            f= open(f"{a}\\Hanza.txt",'r',-1,"utf-8")
            if f'{hanza}' in f.read():
                print(f'{Fore.RED}해당 한자가 이미 저장되어 있습니다{stylex}')
                f.close()
            else:
                f.close()
                does_save(hanzaimg,hanzamean,'y')
            return 1
        

def hanzasave2(inpu,idx=0):
    a="https://namu.wiki/w/%ED%95%9C%EC%9E%90/%EB%AA%A9%EB%A1%9D/%EA%B8%89%EC%88%98%EB%B3%84?from=5%EA%B8%89%20%ED%95%9C%EC%9E%90#s-2.2.2"
    page = requests.get(a)
    geaupsus = ['0','12','11','9:10','7:8','5:6','3:4','1:2','0']
    soup = BeautifulSoup(page.content,'html.parser')
    hanzat = soup.find_all("div",{"class": "wiki-heading-content"})
    hanzat = hanzat[1]
    hanzat = hanzat.find('dd').find('div').find('table').find('tbody').find_all('tr')
    if len(geaupsus[inpu])==2:
        b= int(geaupsus[inpu])
    else:
        b=slice(int(geaupsus[inpu][0]),int(geaupsus[inpu][-1])+1,1)
    hanzat = hanzat[b]
    if type(hanzat)==list:   
        for line in range(len(hanzat)):
            hanzat[line] = hanzat[line].select('a')
        for line in hanzat:
            for c in line:
                hanzasave1(c.string,0)
    else:
        hanzat = hanzat.select('a')
        for c in hanzat:
            hanzasave1(c.string,0)