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

MENU = ["게임", "급수학습", "급수복습", "오답복습", "등록", "사전", "삭제", "종료"]


# 그만하기·다음 명령 (안내문에 나온 단어를 그대로 입력해도 동작하도록)
QUIT = ("종료", "그만", "그만하기", "break")
SKIP = ("다음", "넘기기", "next")


def read(prompt=""):
    """터미널에 따라 한글이 자모 분리(NFD)되어 들어오므로 정규화하고 공백 제거"""
    return unicodedata.normalize("NFC", input(prompt)).strip()


def ask_grade():
    while True:
        s = read(f"{Fore.GREEN}급수를 입력하세요 (1~8, 취소: 종료){stylex}\n")
        if s in QUIT or s == "취소":
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

HELP_LINE = "중간 결과 보기 : '결과' 입력 , 모르면 : 엔터 , 건너뛰기 : '다음' 입력 , 그만하기 : '종료' 입력"

# 예시 한자어 뜻이 길면 이 글자 수에서 자름
WORD_MEAN_LIMIT = 40

# 틀린 적 있는 한자는 이만큼 연속으로 맞혀야 오답복습에서 빠짐
WEAK_STREAK = 3


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


_records = None


def records():
    global _records
    if _records is None:
        _records = hanzadata.load_records()
    return _records


def record_answer(hanja, ok):
    rec = records().setdefault(hanja, {"right": 0, "wrong": 0, "streak": 0})
    if ok:
        rec["right"] += 1
        rec["streak"] += 1
    else:
        rec["wrong"] += 1
        rec["streak"] = 0
    rec["last"] = int(time.time())
    hanzadata.save_records(records())


def is_weak(hanja):
    rec = records().get(hanja)
    return bool(rec) and rec["wrong"] > 0 and rec["streak"] < WEAK_STREAK


def priority(hanja):
    """낮을수록 먼저 출제: 최근에 틀림 < 틀린 적 있음 < 처음 봄 < 잘 앎"""
    rec = records().get(hanja)
    if rec is None:
        return 2
    if rec["streak"] == 0:
        return 0
    if is_weak(hanja):
        return 1
    return 3


def ask(entries, r, stats):
    """한 문제를 낸다. 맞으면 True, 틀리면 False, 넘기면 None, 메뉴 명령이면 '등록'/'사전'/'종료'."""
    result = _ask(entries, r, stats)
    if isinstance(result, bool):
        record_answer(entries[r][0], result)
    return result


def _ask(entries, r, stats):
    hanja, means, _ = entries[r]
    print(hanjaart.best(hanja))
    A = read()
    while A in ("결과", "result"):
        print('')
        print_result("중간 결과", entries, stats)
        print(hanjaart.best(hanja))
        A = read()
    if A in ("등록", "save", "한자"):
        return "등록"
    if A == "사전":
        return "사전"
    if A in QUIT:
        return "종료"
    if A in SKIP:
        print('')
        return None
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
        A = read()
        if A in QUIT:
            return "종료"
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
    # 뒤에서부터 꺼내므로 먼저 낼 한자를 끝에 둠 (같은 순위 안에서는 섞인 순서 유지)
    remaining.sort(key=lambda r: priority(entries[r][0]), reverse=True)
    weak_count = sum(1 for e in entries if is_weak(e[0]))
    if weak_count:
        print(f"{Fore.GREEN}틀린 적 있는 한자 {weak_count}자를 먼저 냅니다.{stylex}")
    # 틀린 한자: [인덱스, 다시 나오기까지 남은 문제 수]
    retry = []
    stats = Stats()
    # 새 한자가 남아 있으면 복습 문제 사이에 최소 이만큼 새 문제를 끼워 넣음
    min_new_between = 2
    since_retry = min_new_between
    command = None
    last = None
    print(f"{Fore.GREEN}{HELP_LINE}{stylex}\n")
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
        if result is None:
            # 넘긴 한자는 맨 뒤로 보내 나중에 다시 냄
            if item is not None:
                retry.append(item)
            else:
                remaining.insert(0, r)
            continue
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
        A = read(f"({i}/{len(chunk)}) 다음 한자 : 엔터 , 그만하기 : '종료' 입력\n")
        if A in QUIT:
            return False
        print('')
    return True


def drill(entries, chunk, learned, stats, on_mastered):
    """묶음 한자를 다 외울 때까지 출제. 다 외우면 None, 아니면 메뉴 명령.
    모든 한자는 MASTERY_STREAK번 연속 맞혀야 끝.
    외운 한자는 바로 on_mastered로 알려 중간에 그만둬도 다시 나오지 않게 한다."""
    streak = {r: 0 for r in chunk}
    # 이전 묶음 한자는 틀린 적 있는 것만, 묶음마다 한 번씩만 섞어 냄
    reviews = [r for r in learned if is_weak(entries[r][0])]
    random.shuffle(reviews)

    last = None
    while 1:
        pending = [r for r, s in streak.items() if s < MASTERY_STREAK]
        if not pending:
            return None
        candidates = [r for r in pending if r != last]
        if reviews and (not candidates or random.random() < REVIEW_RATE):
            r = reviews.pop()
        elif candidates:
            r = random.choice(candidates)
        else:
            # 남은 한자가 방금 나온 한자뿐이면 이미 맞힌 한자를 끼우지 않고 바로 다시 냄
            r = last
        last = r
        result = ask(entries, r, stats)
        if isinstance(result, str):
            return result
        if result is None:
            continue
        stats.record(r, result)
        if result:
            if r in streak:
                streak[r] += 1
                if streak[r] == MASTERY_STREAK:
                    on_mastered(r)
        else:
            # 이전 묶음 한자를 틀리면 이번 묶음에 넣어 다시 외움
            streak[r] = 0


def fill_info(entries, rs):
    """부수·예시 한자어가 저장되지 않은 한자의 정보를 미리 받아 둔다."""
    global _info_cache
    if _info_cache is None:
        _info_cache = hanzadata.load_info()
    missing = [entries[r][0] for r in rs if entries[r][0] not in _info_cache]
    if not missing:
        return
    print(f"{Fore.GREEN}한자 {len(missing)}자의 부수·예시 한자어를 받아오는 중입니다...{stylex}")
    for hanja in missing:
        get_info(hanja)


def choose_chunk(entries, chunks, learned_chars):
    """시작할 묶음 번호(0부터)를 고른다. 엔터면 아직 다 못 외운 첫 묶음, 취소하면 None."""
    done = [sum(1 for r in c if entries[r][0] in learned_chars) for c in chunks]
    default = next((i for i, c in enumerate(chunks) if done[i] < len(c)), 0)
    print(f"{Fore.GREEN}===== 묶음 목록 ({sum(done)}/{len(entries)}자 완료) ====={stylex}")
    for i, c in enumerate(chunks):
        if done[i] == len(c):
            status = f"{Fore.GREEN}완료{stylex}"
        elif done[i]:
            status = f"{Fore.YELLOW}{done[i]}/{len(c)}{stylex}"
        else:
            status = "-"
        mark = " ◀" if i == default else ""
        print(f"{i + 1:>4}. {''.join(entries[r][0] for r in c)}  {status}{mark}")
    while 1:
        A = read(
            f"{Fore.GREEN}시작할 묶음 번호를 입력하세요 "
            f"(엔터 : {default + 1}번부터 , 그만하기 : '종료' 입력){stylex}\n"
        )
        if A in QUIT:
            return None
        if A == "":
            return default
        if A.isdigit() and 1 <= int(A) <= len(chunks):
            return int(A) - 1
        print(f"{Fore.RED}1~{len(chunks)} 사이의 숫자를 입력해주세요.{stylex}")


def learn(entries, grade):
    learned_chars = hanzadata.load_learned(grade)
    chunks = [list(range(i, min(i + CHUNK_SIZE, len(entries)))) for i in range(0, len(entries), CHUNK_SIZE)]
    start = choose_chunk(entries, chunks, learned_chars)
    if start is None:
        return
    print(
        f"\n{Fore.GREEN}{CHUNK_SIZE}자씩 먼저 보고, 모두 맞히면 다음 묶음으로 넘어갑니다.\n"
        f"고른 묶음은 처음부터 다시 하고, 이후 묶음은 아직 못 외운 한자만 나옵니다.\n"
        f"한자마다 {MASTERY_STREAK}번 연속 맞혀야 하고, 틀리면 처음부터 다시 셉니다.\n"
        f"{HELP_LINE}{stylex}\n"
    )
    # 이전 묶음에서 외운 한자 (틀린 적 있는 것만 복습으로 섞어 냄)
    learned = [r for c in chunks[:start] for r in c if entries[r][0] in learned_chars]
    fill_info(entries, learned)
    stats = Stats()
    command = None

    def mastered(r):
        if r not in learned:
            learned.append(r)
        learned_chars.add(entries[r][0])
        hanzadata.save_learned(grade, learned_chars)

    for no in range(start, len(chunks)):
        chunk = chunks[no] if no == start else [r for r in chunks[no] if entries[r][0] not in learned_chars]
        if not chunk:
            continue
        fill_info(entries, chunk)
        title = f"묶음 {no + 1}/{len(chunks)}"
        print(f"{Fore.GREEN}===== {title} : 새 한자 보기 ====={stylex}\n")
        if not introduce(entries, chunk):
            break
        print(f"{Fore.GREEN}===== {title} : 문제 ====={stylex}\n")
        command = drill(entries, chunk, learned, stats, mastered)
        if command is not None:
            break
        print(f"{Fore.GREEN}{title} 완료! ({len(learned_chars)}/{len(entries)}자){stylex}\n")
    else:
        if all(e[0] in learned_chars for e in entries):
            print(f"{Fore.GREEN}{grade}급 한자를 모두 학습했습니다!{stylex}\n")
        else:
            print(f"{Fore.GREEN}마지막 묶음까지 학습했습니다. 앞쪽에 남은 한자는 묶음 번호를 골라 학습하세요.{stylex}\n")

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


def review_weak():
    entries = [e for e in hanzadata.load_all() if is_weak(e[0])]
    if not entries:
        print(f"{Fore.GREEN}복습할 오답이 없습니다!{stylex}\n")
        return
    print(f"{Fore.GREEN}{WEAK_STREAK}번 연속으로 맞히면 오답 목록에서 빠집니다.{stylex}")
    play(entries, "오답을 모두 복습했습니다!")
    left = sum(1 for e in entries if is_weak(e[0]))
    print(f"{Fore.GREEN}남은 오답 : {left}자{stylex}\n")


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
        A = read(
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
                "오답복습 : 틀린 적 있는 한자만 복습\n"
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
        elif A == '오답복습':
            print('')
            review_weak()
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
