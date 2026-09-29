import random
import re
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

MENU = ["게임", "급수학습", "급수복습", "등록", "사전", "삭제", "종료"]


def ask_grade():
    while True:
        s = input(f"{Fore.GREEN}급수를 입력하세요 (1~8, 취소: 종료){stylex}\n")
        if s in ("종료", "취소"):
            return None
        if s.isdigit() and int(s) in VALID_GRADES:
            return int(s)
        print(f"{Fore.RED}1~8 사이의 숫자를 입력해주세요.{stylex}\n")


# 급수학습: 한 번에 새로 외우는 한자 수, 다음 묶음으로 넘어가려면 연속으로 맞혀야 하는 횟수
CHUNK_SIZE = 10
MASTERY_STREAK = 2
# 묶음 학습 중 이전에 외운 한자를 섞어 낼 확률
REVIEW_RATE = 0.2

DONT_KNOW = ("", "?", "모름")

# 예시 한자어 뜻이 길면 이 글자 수에서 자름
WORD_MEAN_LIMIT = 40


class Stats:
    def __init__(self):
        self.asked = 0
        self.correct = 0
        self.fails = {}

    def record(self, r, ok):
        self.asked += 1
        if ok:
            self.correct += 1
        else:
            self.fails[r] = self.fails.get(r, 0) + 1


def print_result(title, entries, stats):
    asked, correct, fails = stats.asked, stats.correct, stats.fails
    print(f"{Fore.GREEN}===== {title} ====={stylex}")
    print(f"푼 문제 : {asked}  /  정답 : {Fore.GREEN}{correct}{stylex}  /  오답 : {Fore.RED}{asked - correct}{stylex}")
    if asked:
        print(f"정답률 : {correct * 100 // asked}%")
    if fails:
        print(f"{Fore.RED}틀린 한자{stylex}")
        for r, count in sorted(fails.items(), key=lambda x: -x[1]):
            hanja, means, _ = entries[r]
            print(f"  {hanja} ({', '.join(means)}) : {Fore.RED}{count}번{stylex}")
    else:
        print(f"{Fore.GREEN}틀린 한자가 없습니다!{stylex}")
    print('')


def display_means(means):
    """'학교 교'처럼 훈과 음이 붙은 것만 보여줌 (없으면 전체)"""
    return ", ".join([m for m in means if " " in m] or means)


_info_cache = None


def get_info(hanja):
    """부수·예시 한자어. 처음 볼 때만 사전에서 가져와 HanzaInfo.json에 저장해 둔다."""
    global _info_cache
    if _info_cache is None:
        _info_cache = hanzadata.load_info()
    if hanja not in _info_cache:
        try:
            _info_cache[hanja] = Downloadimage.fetch_hanza_info(hanja)
        except requests.exceptions.RequestException:
            return None
        hanzadata.save_info(_info_cache)
    return _info_cache[hanja]


def show_hanja(hanja, means):
    """훈음과 함께 부수, 그 한자가 들어간 한자어를 보여준다."""
    print(f"{Fore.YELLOW}{hanja} : {display_means(means)}{stylex}")
    info = get_info(hanja)
    if not info:
        return
    if info["radical"]:
        print(f"부수 : {info['radical']}")
    for word, reading, mean in info["words"]:
        mean = re.sub(r"^\d+\.\s*", "", mean)
        if len(mean) > WORD_MEAN_LIMIT:
            mean = mean[:WORD_MEAN_LIMIT] + "…"
        print(f"  {Fore.CYAN}{word}({reading}){stylex} {mean}")


def ask(entries, r, stats):
    """한 문제를 낸다. 맞으면 True, 틀리면 False, 메뉴 명령이면 '등록'/'사전'/'종료'."""
    hanja, means, _ = entries[r]
    print(hanjaart.best(hanja))
    A = unicodedata.normalize("NFC", input().strip())
    while A in ("결과", "result"):
        print('')
        print_result("중간 결과", entries, stats)
        print(hanjaart.best(hanja))
        A = unicodedata.normalize("NFC", input().strip())
    if A in ("등록", "save", "한자"):
        return "등록"
    if A == "사전":
        return "사전"
    if A in ("종료", "break"):
        return "종료"
    if A in means:
        print(f"{Fore.GREEN}정답입니다!\n{stylex}")
        return True
    if A in DONT_KNOW:
        show_hanja(hanja, means)
        print('')
        return False
    print(f"{Fore.RED}오답입니다{stylex}\n해당 한자의 뜻입니다. 정답이라고 하시겠습니까? {Fore.GREEN}Y{stylex}/{Fore.RED}N{stylex}")
    print(", ".join(means))
    while 1:
        A = input()
        if A in ("Y", "y", "ㅛ"):
            print('\n')
            return True
        elif A in ("N", "n", "ㅜ"):
            print('')
            show_hanja(hanja, means)
            print('')
            return False
        else:
            print(f"{Fore.RED}Y 혹은 N을 입력해주세요{stylex}")


def run_command(command):
    if command == "등록":
        Downloadimage.main()
    elif command == "사전":
        printhanza.main()


def play(entries, empty_message):
    remaining = list(range(len(entries)))
    random.shuffle(remaining)
    # 틀린 한자: [인덱스, 다시 나오기까지 남은 문제 수]
    retry = []
    stats = Stats()
    # 새 한자가 남아 있으면 복습 문제 사이에 최소 이만큼 새 문제를 끼워 넣음
    min_new_between = 2
    since_retry = min_new_between
    command = None
    last = None
    print(f"{Fore.GREEN}중간 결과 보기 : 결과 , 모르면 : 엔터 , 그만하기 : 종료{stylex}\n")
    while 1:
        # 방금 나온 한자가 곧바로 다시 나오지 않도록 (다른 후보가 있을 때만)
        candidates = [item for item in retry if item[0] != last] or retry
        due = [item for item in candidates if item[1] <= 0]
        if due and (since_retry >= min_new_between or not remaining):
            # 고정된 순서로 돌지 않도록 차례가 된 한자 중 무작위로
            item = random.choice(due)
        elif remaining:
            item = None
        elif retry:
            # 남은 문제가 없으면 틀린 한자 중 무작위로 출제
            item = random.choice(candidates)
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
        last = r
        result = ask(entries, r, stats)
        if isinstance(result, str):
            command = result
            break
        stats.record(r, result)
        if not result:
            # 여러 번 틀릴수록 다시 나오는 간격을 늘림
            gap = min(random.randint(8, 12) * 2 ** (stats.fails[r] - 1), 40)
            retry.append([r, gap])

    if stats.asked:
        print_result("최종 결과", entries, stats)
    run_command(command)


def introduce(entries, chunk):
    """새 묶음의 한자를 한 글자씩 보여준다. 도중에 그만두면 False."""
    for i, r in enumerate(chunk, 1):
        hanja, means, _ = entries[r]
        print(hanjaart.best(hanja))
        show_hanja(hanja, means)
        A = input(f"({i}/{len(chunk)}) 엔터 : 다음 , 종료 : 그만하기\n").strip()
        if A in ("종료", "break"):
            return False
        print('')
    return True


def drill(entries, chunk, learned, stats):
    """묶음 한자를 모두 연속 MASTERY_STREAK번 맞힐 때까지 출제. 다 외우면 None, 아니면 메뉴 명령."""
    streak = {r: 0 for r in chunk}
    last = None
    while 1:
        pending = [r for r, s in streak.items() if s < MASTERY_STREAK]
        if not pending:
            return None
        candidates = [r for r in pending if r != last]
        reviews = [r for r in learned if r != last and r not in streak]
        if reviews and (not candidates or random.random() < REVIEW_RATE):
            r = random.choice(reviews)
        elif candidates:
            r = random.choice(candidates)
        else:
            # 남은 한자가 방금 나온 한자뿐이면 이미 외운 한자를 사이에 끼움
            others = [r for r in streak if r != last]
            r = random.choice(others) if others else last
        last = r
        result = ask(entries, r, stats)
        if isinstance(result, str):
            return result
        stats.record(r, result)
        if result:
            if r in streak:
                streak[r] += 1
        else:
            # 이전 묶음 한자를 틀리면 이번 묶음에 넣어 다시 외움
            streak[r] = 0


def learn(entries, grade):
    learned_chars = hanzadata.load_learned(grade)
    if all(e[0] in learned_chars for e in entries):
        A = input(f"{Fore.GREEN}{grade}급 한자를 모두 학습했습니다. 처음부터 다시 할까요? {stylex}{Fore.GREEN}Y{stylex}/{Fore.RED}N{stylex}\n")
        if A not in ("Y", "y", "ㅛ"):
            return
        learned_chars = set()
        hanzadata.save_learned(grade, learned_chars)
    learned = [r for r, e in enumerate(entries) if e[0] in learned_chars]
    new = [r for r, e in enumerate(entries) if e[0] not in learned_chars]
    total_chunks = (len(entries) + CHUNK_SIZE - 1) // CHUNK_SIZE
    if learned:
        print(f"{Fore.GREEN}지난번에 이어서 학습합니다. ({len(learned)}/{len(entries)}자 완료){stylex}")
    print(
        f"{Fore.GREEN}{CHUNK_SIZE}자씩 먼저 보고, 모두 {MASTERY_STREAK}번 연속 맞히면 다음 묶음으로 넘어갑니다.\n"
        f"중간 결과 보기 : 결과 , 모르면 : 엔터 , 그만하기 : 종료{stylex}\n"
    )
    stats = Stats()
    command = None
    while new:
        chunk, new = new[:CHUNK_SIZE], new[CHUNK_SIZE:]
        chunk_no = len(learned) // CHUNK_SIZE + 1
        print(f"{Fore.GREEN}===== 묶음 {chunk_no}/{total_chunks} : 새 한자 보기 ====={stylex}\n")
        if not introduce(entries, chunk):
            break
        print(f"{Fore.GREEN}===== 묶음 {chunk_no}/{total_chunks} : 문제 ====={stylex}\n")
        command = drill(entries, chunk, learned, stats)
        if command is not None:
            break
        learned += chunk
        learned_chars.update(entries[r][0] for r in chunk)
        hanzadata.save_learned(grade, learned_chars)
        print(f"{Fore.GREEN}묶음 {chunk_no} 완료! ({len(learned)}/{len(entries)}자){stylex}\n")
    else:
        print(f"{Fore.GREEN}{grade}급 한자를 모두 학습했습니다!{stylex}\n")

    if stats.asked:
        print_result("최종 결과", entries, stats)
    run_command(command)


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
    registered = {e[0] for e in hanzadata.load_all()}
    missing = [c for c in chars if c not in registered]
    if missing:
        print(f"{Fore.GREEN}{grade}급 한자 {len(missing)}자를 사전에 등록하는 중입니다...{stylex}")
    for c in missing:
        Downloadimage.hanzasave1(c, 0, grade)
    entries = [e for e in hanzadata.load_all() if e[2] == grade]
    if not entries:
        print(f"{Fore.RED}{grade}급 한자를 가져오지 못했습니다.{stylex}\n")
        return
    learn(entries, grade)


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
            + " , ".join(f"{i}. {name}" for i, name in enumerate(MENU, 1))
            + "\n\n"
        ).strip()
        if A.isdigit() and 1 <= int(A) <= len(MENU):
            A = MENU[int(A) - 1]
        if A == "H" or A == 'h' or A == 'help':
            print(
                f"{Fore.GREEN}\n메뉴 이름이나 번호를 입력하세요\n"
                "게임 : 등록된 한자 전체 복습\n"
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
