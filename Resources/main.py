import random
import time

import requests

import printhanza
import Downloadimage
import Deletehanza
import hanzadata
from colorama import Fore, Style, init

init()
stylex = Style.RESET_ALL

VALID_GRADES = list(range(1, 9))


def ask_grade():
    while True:
        s = input(f"{Fore.GREEN}급수를 입력하세요 (1~8, 취소: 종료){stylex}\n")
        if s in ("종료", "취소"):
            return None
        if s.isdigit() and int(s) in VALID_GRADES:
            return int(s)
        print(f"{Fore.RED}1~8 사이의 숫자를 입력해주세요.{stylex}\n")


def play(entries, empty_message):
    hanzalen = len(entries)
    hanzalist = [0] * hanzalen
    is_breaking = False
    is_download = False
    is_printimg = False
    while 1:
        while 1:
            if 0 in hanzalist:
                r = random.randrange(0, hanzalen)
                if hanzalist[r]:
                    continue
                hanzalist[r] = 1
                break
            else:
                if is_breaking:
                    break
                print(f"{Fore.GREEN}{empty_message}{stylex}")
                is_breaking = True
                break
        if is_breaking:
            break
        hanja, means, grade = entries[r]
        print(hanja)
        A = input()
        if A == "등록" or A == "save" or A == "한자":
            is_download = True
            break
        if A == "사전":
            is_printimg = True
            break
        elif A == "종료" or A == "break":
            break
        elif A in means:
            print(f"{Fore.GREEN}정답입니다!\n{stylex}")
        else:
            print(f"{Fore.RED}오답입니다{stylex}\n해당 한자의 뜻입니다. 정답이라고 하시겠습니까? {Fore.GREEN}Y{stylex}/{Fore.RED}N{stylex}")
            print(", ".join(means))
            while 1:
                A = input()
                if A in ("Y", "y", "ㅛ"):
                    hanzalist[r] = 1
                    print('')
                    break
                elif A in ("N", "n", "ㅜ"):
                    hanzalist[r] = 0
                    print('')
                    break
                else:
                    print(f"{Fore.RED}Y 혹은 N을 입력해주세요{stylex}")
            print('')

    if is_download:
        Downloadimage.main()
    elif is_printimg:
        printhanza.main()


def game():
    entries = hanzadata.load_all()
    if not entries:
        print(f"{Fore.RED}등록된 한자가 없습니다. 먼저 한자를 등록해주세요.{stylex}\n")
        return
    play(entries, "학습한 모든 한자를 복습했습니다!")


def study_by_grade():
    grade = ask_grade()
    if grade is None:
        return
    print(f"{Fore.GREEN}{grade}급 한자 목록을 가져오는 중입니다...{stylex}")
    try:
        chars = Downloadimage.get_hanza_list_by_grade(grade)
    except requests.exceptions.RequestException:
        print(f"{Fore.RED}한자 목록을 가져오지 못했습니다. 인터넷 연결을 확인해주세요.{stylex}\n")
        return
    print(f"{Fore.GREEN}{grade}급 한자 {len(chars)}자를 사전에 등록하는 중입니다...{stylex}")
    for c in chars:
        Downloadimage.hanzasave1(c, 0, grade)
    entries = [e for e in hanzadata.load_all() if e[2] == grade]
    if not entries:
        print(f"{Fore.RED}{grade}급 한자를 가져오지 못했습니다.{stylex}\n")
        return
    play(entries, f"{grade}급 한자를 모두 학습했습니다!")


def review_by_grade():
    grade = ask_grade()
    if grade is None:
        return
    entries = [e for e in hanzadata.load_all() if e[2] == grade]
    if not entries:
        print(f"{Fore.RED}{grade}급으로 등록된 한자가 없습니다. 먼저 '급수학습'으로 등록해주세요.{stylex}\n")
        return
    play(entries, f"{grade}급 한자를 모두 복습했습니다!")


def main():
    if hanzadata.ensure_file():
        print(f"{Fore.GREEN}첫 설정을 하는 중입니다....{stylex}", end='', flush=True)
        for i in range(1, 9):
            time.sleep(0.5)
            print('\r', end='', flush=True)
            print('  ' * 20, end='', flush=True)
            print('\r', end='', flush=True)
            print(f'{Fore.GREEN}첫 설정을 하는 중입니다' + '.' * (i % 4) + stylex, end='', flush=True)
        print('\r', end='', flush=True)
        print(' ' * 20, end='', flush=True)
        print('\r', end='', flush=True)
        print(f"{Fore.GREEN}설정이 완료 되었습니다!\n{stylex}")

    while 1:
        A = input(
            f"무엇을 하시겠습니까?  {Fore.GREEN}(도움말 : help){stylex}\n"
            "게임 , 급수학습 , 급수복습 , 등록 , 사전 , 삭제 , 종료\n\n"
        )
        if A == "H" or A == 'h' or A == 'help':
            print(
                f"{Fore.GREEN}\n게임 : 등록된 한자 전체 복습\n"
                "급수학습 : 급수를 선택해 한자를 새로 등록하고 학습\n"
                "급수복습 : 이미 등록된 한자를 급수별로 복습\n"
                "등록 : 학습한 한자 등록\n사전 : 학습한 한자 보기\n"
                f"삭제 : 한자를 사전에서 삭제\n종료 : 프로그램을 종료합니다\n{stylex}"
            )
        if A == '게임':
            print('')
            game()
        elif A == '급수학습':
            print('')
            study_by_grade()
        elif A == '급수복습':
            print('')
            review_by_grade()
        elif A == '등록':
            print('')
            Downloadimage.main()
        elif A == '사전':
            print('')
            printhanza.main()
        elif A == '삭제':
            print('')
            Deletehanza.main()
        elif A == '종료' or A == '^C':
            print("종료합니다")
            break


if __name__ == "__main__":
    main()
