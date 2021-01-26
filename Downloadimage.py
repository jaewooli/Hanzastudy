from bs4 import BeautifulSoup
import requests
def does_save(hanzaimg,hanzamean,a):
    if a =="Y" or a=='y' or a=='ㅛ':
        f= open("Hanza.txt",'a',-1,"utf-8")
        f.write(f"{hanzaimg}: {hanzamean}\n")
        f.close()
        print('해당 한자를 저장합니다')
    elif a=="N" or a=='n' or a== 'ㅜ':
        pass
    else:
        a= input("Y 혹은 N 을 입력해주세요.\nY/N : ")
        does_save(hanzaimg,hanzamean,a)
def hanzasave():
    while 1:
        hanza = u"{hanza}".format(hanza = input("등록할 한자:"))
        if hanza =='B'or hanza == "Break" or hanza == 'break':
            break
        f= open("Hanza.txt",'r',-1,"utf-8")
        if f'{hanza}' in f.read():
            print('해당 한자가 이미 저장되어 있습니다')
        else:
            try:
                page = requests.get(f"https://hanja.dict.naver.com/search?query={hanza}")
                soup = BeautifulSoup(page.content, 'html.parser')
                hanzaimg =soup.find("div", {"class": "result_chn_chr"}).find("dl").find('dt').find('a').contents[0]
                f= open("Hanza.txt",'r',-1,"utf-8")
                if f'{hanzaimg}' in f.read():
                    print('해당 한자가 이미 저장되어 있습니다')
                else:
                    hanzamean = soup.find("div", {"class": "result_chn_chr"}).find("dl").find('dd').find('a').find('span')
                    hanzamean.b.unwrap()
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
                    if hanza not in hanzamean:
                        print("검색된 한자가 입력한 한자와 뜻이 다릅니다.\n찾는 한자인가요?")
                        print(hanzaimg)
                        print(",".join(hanzamean))
                        a =input("Y/N : ")
                        does_save(hanzaimg,hanzamean,a)
                    else:
                        print(hanzaimg)
                        print(hanzamean)
                        a= input("저장할까요?\nY/N : ")
                        does_save(hanzaimg,hanzamean,a)
            except AttributeError:
                print("입력하신 한자를 찾을 수 없습니다")