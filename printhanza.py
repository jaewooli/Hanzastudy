def findhanza():
    f=open("Hanza.txt",'r',-1, 'utf-8')
    A = input("찾는 한자, 또는 그 뜻을 입력하세요 :")
    listf = f.read().split("\n")
    for line in listf:
        if A in line:
            linea = line.split(":")
            lineb = str(linea[1])
            linea = str(linea[0])
            return linea, lineb
def fileopen():
    f= open("Hanza.txt",'r',-1,"utf-8")
    listf = f.read().split("\n")
    return len(listf)-1, listf