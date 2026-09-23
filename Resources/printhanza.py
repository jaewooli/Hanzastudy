import unicodedata

from colorama import Fore, Style

import hanzadata
import hanjaart


def _grade_label(grade):
    return f"{grade}급" if grade else "급수 미지정"


def main():
    stylex = Style.RESET_ALL
    while 1:
        A = unicodedata.normalize("NFC", input(f"{Fore.GREEN}찾는 한자, 또는 그 뜻을 입력하세요 : {stylex}\n").strip())
        if A == "H" or A == 'h' or A == 'help':
            print(f"{Fore.GREEN}리스트{stylex} : 전체 단어 리스트\n{Fore.GREEN}예시:) 집 가{stylex}\n")
        elif A == "리스트" or A == "list":
            entries = hanzadata.load_all()
            for hanja, means, grade in entries:
                print(f"{hanja} : {', '.join(means)} ({_grade_label(grade)})")
            print('')
        elif A == "break" or A == "종료":
            break
        else:
            entries = hanzadata.load_all()
            found = False
            for hanja, means, grade in entries:
                if A in hanja or any(A in m for m in means):
                    print(hanjaart.best(hanja))
                    print(hanja, ':', ', '.join(means), f"({_grade_label(grade)})")
                    print('')
                    found = True
                    break
            if not found:
                print(f"{Fore.RED}해당 한자가 사전에 등록되어있지 않습니다. 사전에 등록해주세요.{stylex}\n")
