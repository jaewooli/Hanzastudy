import random
import time
import unicodedata

try:
    # 터미널 기본 줄 편집은 백스페이스로 한글(3바이트)을 1바이트만 지워 입력이 깨짐
    import readline  # noqa: F401
except ImportError:
    pass

import requests

import printhanza
import Downloadimage
import Deletehanza
import hanzadata
import hanjaart
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
    remaining = list(range(len(entries)))
    random.shuffle(remaining)
    # 틀린 한자: [인덱스, 다시 나오기까지 남은 문제 수]
    retry = []
    fails = {}
    # 새 한자가 남아 있으면 복습 문제 사이에 최소 이만큼 새 문제를 끼워 넣음
    min_new_between = 2
    since_retry = min_new_between
    is_download = False
    is_printimg = False
    while 1:
        due = [item for item in retry if item[1] <= 0]
        if due and (since_retry >= min_new_between or not remaining):
            # 가장 오래 기다린 한자부터
            item = min(due, key=lambda x: x[1])
        elif remaining:
            item = None
        elif retry:
            # 남은 문제가 없으면 가장 먼저 다시 나올 한자를 바로 출제
            item = min(retry, key=lambda x: x[1])
        else:
            print(f"{Fore.GREEN}{empty_message}{stylex}")
            break
        if item is not None:
            retry.remove(item)
            r = item[0]
            since_retry = 0
        else:
            r = remaining.pop()
            since_retry += 1
        for pending in retry:
            pending[1] -= 1
        hanja, means, grade = entries[r]
        print(hanjaart.best(hanja))
        A = unicodedata.normalize("NFC", input().strip())
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
                    print('')
                    break
                elif A in ("N", "n", "ㅜ"):
                    # 여러 번 틀릴수록 다시 나오는 간격을 늘림
                    fails[r] = fails.get(r, 0) + 1
                    gap = min(random.randint(8, 12) * 2 ** (fails[r] - 1), 40)
                    retry.append([r, gap])
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
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{Fore.GREEN}프로그램을 종료합니다.{stylex}")
