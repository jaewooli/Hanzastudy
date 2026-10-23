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

MENU = ["게임", "급수학습", "급수복습", "오답복습", "한자어", "골라맞히기", "등록", "사전", "삭제", "종료"]


# 문제를 풀 때는 한자의 뜻(예: '마칠 종료', '다음 차')과 겹치지 않도록 명령 앞에 '/'를 붙여 입력
COMMAND_PREFIX = ("/", "／")
QUIT = ("종료", "그만", "그만하기", "break")
SKIP = ("다음", "넘기기", "next")
RESULT = ("결과", "result")


def read(prompt=""):
    """터미널에 따라 한글이 자모 분리(NFD)되어 들어오므로 정규화하고 공백 제거"""
    return unicodedata.normalize("NFC", input(prompt)).strip()


def command_of(s):
    """'/종료' -> '종료'. 명령이 아니면 None."""
    if s.startswith(COMMAND_PREFIX):
        return s[1:].strip()
    return None


def is_quit(s):
    """뜻을 입력받는 곳이 아니므로 '/' 없이 입력해도 그만하기로 인정"""
    return s in QUIT or command_of(s) in QUIT


def ask_grade(allow_all=False):
    """급수(1~8)를 고른다. 취소하면 None, allow_all이면 엔터로 전체(0)."""
    while True:
        hint = "1~8, 전체: 엔터, 취소: /종료" if allow_all else "1~8, 취소: /종료"
        s = read(f"{Fore.GREEN}급수를 입력하세요 ({hint}){stylex}\n")
        if is_quit(s) or s == "취소":
            return None
        if allow_all and s == "":
            return 0
        if s.isdigit() and int(s) in VALID_GRADES:
            return int(s)
        print(f"{Fore.RED}1~8 사이의 숫자를 입력해주세요.{stylex}\n")


# 급수학습: 한 번에 새로 외우는 한자 수, 다음 묶음으로 넘어가려면 연속으로 맞혀야 하는 횟수
CHUNK_SIZE = 10
MASTERY_STREAK = 2
# 묶음 학습 중 이전에 외운 한자를 섞어 낼 확률
REVIEW_RATE = 0.2

DONT_KNOW = ("", "?", "모름")

HELP_LINE = "모르면 : 엔터 , 중간 결과 : /결과 , 건너뛰기 : /다음 , 그만하기 : /종료 (명령은 '/'를 붙여 입력)"

# 예시 한자어 뜻이 길면 이 글자 수에서 자름
WORD_MEAN_LIMIT = 40

# 틀린 적 있는 한자는 이만큼 연속으로 맞혀야 오답복습에서 빠짐
WEAK_STREAK = 3

# 문제 종류별 (문제 이름, 세는 단위)
# hanja: 한자 보고 뜻 쓰기, word: 한자어 보고 독음 쓰기, choice: 훈음 보고 한자 고르기
KIND_NAMES = {"hanja": ("한자", "자"), "word": ("한자어", "개"), "choice": ("한자", "자")}

CHOICE_COUNT = 4


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


PROGRESS_WIDTH = 20


def progress_bar(done, retry, total, unit="자"):
    """초록: 끝난 한자, 빨강: 다시 낼 오답, 회색: 아직 안 나온 한자"""
    green = done * PROGRESS_WIDTH // total
    red = (done + retry) * PROGRESS_WIDTH // total - green
    if retry and not red:
        red = 1
        green = min(green, PROGRESS_WIDTH - 1)
    gray = PROGRESS_WIDTH - green - red
    return (
        f"{Fore.GREEN}{'█' * green}{Fore.RED}{'█' * red}{Style.DIM}{'░' * gray}{stylex}"
        f" {Fore.GREEN}{done * 100 // total}%{stylex} ({done}/{total}{unit})"
        + (f"  {Fore.RED}다시 낼 오답 {retry}{stylex}" if retry else "")
    )


def mastery_dots(streaks):
    """묶음 한자마다 ●: 외움, ◐: 연속으로 맞히는 중, ○: 아직"""
    dots = []
    for s in sorted(streaks, reverse=True):
        if s >= MASTERY_STREAK:
            dots.append(f"{Fore.GREEN}●")
        elif s:
            dots.append(f"{Fore.YELLOW}◐")
        else:
            dots.append(f"{Style.DIM}○{Style.NORMAL}")
    return "".join(dots) + stylex


def print_result(title, entries, stats, kind="hanja"):
    asked, correct, fails = stats.asked, stats.correct, stats.fails
    name = KIND_NAMES[kind][0]
    print(f"{Fore.GREEN}===== {title} ====={stylex}")
    print(f"푼 문제 : {asked}  /  정답 : {Fore.GREEN}{correct}{stylex}  /  오답 : {Fore.RED}{asked - correct}{stylex}")
    if asked:
        print(f"정답률 : {correct * 100 // asked}%")
    if fails:
        print(f"{Fore.RED}틀린 {name}{stylex}")
        for r, count in sorted(fails.items(), key=lambda x: -x[1]):
            hanja, means, _ = entries[r]
            print(f"  {hanja} ({', '.join(means)}) : {Fore.RED}{count}번{stylex}")
    else:
        print(f"{Fore.GREEN}틀린 {name}가 없습니다!{stylex}")
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


_records = {}


def records(kind="hanja"):
    if kind not in _records:
        _records[kind] = hanzadata.load_records(kind)
    return _records[kind]


def record_answer(hanja, ok, kind="hanja"):
    rec = records(kind).setdefault(hanja, {"right": 0, "wrong": 0, "streak": 0})
    if ok:
        rec["right"] += 1
        rec["streak"] += 1
    else:
        rec["wrong"] += 1
        rec["streak"] = 0
    rec["last"] = int(time.time())
    hanzadata.save_records(records(kind), kind)


def is_weak(hanja, kind="hanja"):
    rec = records(kind).get(hanja)
    return bool(rec) and rec["wrong"] > 0 and rec["streak"] < WEAK_STREAK


def priority(hanja, kind="hanja"):
    """낮을수록 먼저 출제: 최근에 틀림 < 틀린 적 있음 < 처음 봄 < 잘 앎"""
    rec = records(kind).get(hanja)
    if rec is None:
        return 2
    if rec["streak"] == 0:
        return 0
    if is_weak(hanja, kind):
        return 1
    return 3


class Interrupt(Exception):
    """문제 도중 명령으로 문제를 끝냄. result는 ask가 돌려줄 값."""

    def __init__(self, result):
        super().__init__(result)
        self.result = result


def read_answer(entries, stats, kind, redraw):
    """명령을 처리하며 답을 읽는다. 문제를 끝내는 명령이면 Interrupt."""
    while 1:
        A = read()
        command = command_of(A)
        if command is None:
            return A
        if command in RESULT:
            print('')
            print_result("중간 결과", entries, stats, kind)
            redraw()
        elif command in ("등록", "save", "한자"):
            raise Interrupt("등록")
        elif command == "사전":
            raise Interrupt("사전")
        elif command in QUIT:
            raise Interrupt("종료")
        elif command in SKIP:
            print('')
            raise Interrupt(None)
        else:
            print(f"{Fore.RED}알 수 없는 명령입니다. {HELP_LINE}{stylex}")


def ask(entries, r, stats, progress="", kind="hanja"):
    """한 문제를 낸다. 맞으면 True, 틀리면 False, 넘기면 None, 메뉴 명령이면 '등록'/'사전'/'종료'."""
    if progress:
        print(progress)
    try:
        result = ASKERS[kind](entries, r, stats)
    except Interrupt as e:
        result = e.result
    if isinstance(result, bool):
        record_answer(entries[r][0], result, kind)
    return result


def _ask(entries, r, stats):
    hanja, means, _ = entries[r]
    print(hanjaart.best(hanja))
    A = read_answer(entries, stats, "hanja", lambda: print(hanjaart.best(hanja)))
    if A in means:
        print(f"{Fore.GREEN}정답입니다!{stylex}")
        show_hanja(hanja, means)
        print('')
        return True
    if A in DONT_KNOW:
        show_hanja(hanja, means)
        print('')
        return False
    print(f"{Fore.RED}오답입니다{stylex}\n해당 한자의 뜻입니다. 정답이라고 하시겠습니까? {Fore.GREEN}Y{stylex}/{Fore.RED}N{stylex}")
    print(", ".join(means))
    while 1:
        A = read()
        if is_quit(A):
            return "종료"
        if A in ("Y", "y", "ㅛ"):
            print('')
            show_hanja(hanja, means)
            print('')
            return True
        elif A in ("N", "n", "ㅜ"):
            print('')
            show_hanja(hanja, means)
            print('')
            return False
        else:
            print(f"{Fore.RED}Y 혹은 N을 입력해주세요{stylex}")


def char_means():
    """사전의 {한자: 훈음 목록}"""
    return {hanja: means for hanja, means, _ in hanzadata.load_all()}


def word_entries(grade):
    """사전에 등록된 글자로만 된 예시 한자어: [(한자어, [독음], 뜻)].
    grade가 0이 아니면 그 급수 한자가 들어간 것만."""
    all_entries = hanzadata.load_all()
    # 예시 한자어는 고른 급수 한자의 것만 받아 둠 (전체면 모두)
    fill_info(all_entries, [r for r, e in enumerate(all_entries) if not grade or e[2] == grade])
    registered = {e[0] for e in all_entries}
    grade_chars = {e[0] for e in all_entries if e[2] == grade}
    words = {}
    for hanja in registered:
        info = _info_cache.get(hanja)
        if not info:
            continue
        for word, reading, mean in info["words"]:
            if len(word) < 2 or word in words or not set(word) <= registered:
                continue
            if grade and not set(word) & grade_chars:
                continue
            words[word] = (word, [reading], re.sub(r"^\d+\.\s*", "", mean))
    return list(words.values())


def show_word(word, reading, mean, means_of):
    print(f"{Fore.YELLOW}{word}({reading}){stylex} {mean}")
    for c in word:
        print(f"  {c} : {display_means(means_of.get(c, []))}")


_char_means = None


def _ask_word(entries, r, stats):
    """한자어를 보여주고 독음을 입력받는다. 띄어쓰기는 무시."""
    global _char_means
    if _char_means is None:
        _char_means = char_means()
    word, readings, mean = entries[r]

    def draw():
        print(hanjaart.best_row(word))

    draw()
    A = read_answer(entries, stats, "word", draw)
    ok = A.replace(" ", "") in [x.replace(" ", "") for x in readings]
    if ok:
        print(f"{Fore.GREEN}정답입니다!{stylex}")
    elif A not in DONT_KNOW:
        print(f"{Fore.RED}오답입니다{stylex}")
    show_word(word, readings[0], mean, _char_means)
    print('')
    return ok


def sounds(means):
    """'학교 교', '풍길 효' -> {'교', '효'}"""
    return {m.split()[-1] for m in means if " " in m}


def radical_of(hanja):
    info = (_info_cache or {}).get(hanja)
    return info["radical"].split("(")[0] if info and info["radical"] else None


def choices_for(entries, r, pool):
    """정답과 헷갈리기 쉬운 보기: 같은 부수·같은 음 한자를 먼저, 모자라면 아무 한자나."""
    hanja, means, _ = entries[r]
    shown = set(display_means(means).split(", "))
    radical, sound = radical_of(hanja), sounds(means)
    similar, others = [], []
    for c, c_means, _ in pool:
        # 훈음이 겹치면 정답이 둘이 되므로 뺌
        if c == hanja or shown & set(c_means):
            continue
        if (radical and radical_of(c) == radical) or sound & sounds(c_means):
            similar.append(c)
        else:
            others.append(c)
    random.shuffle(similar)
    random.shuffle(others)
    picked = (similar + others)[:CHOICE_COUNT - 1] + [hanja]
    random.shuffle(picked)
    return picked


_choice_pool = None


def _ask_choice(entries, r, stats):
    """훈음을 보여주고 한자를 고르게 한다. 번호나 한자로 답한다."""
    global _choice_pool
    if _choice_pool is None:
        _choice_pool = hanzadata.load_all()
    hanja, means, _ = entries[r]
    choices = choices_for(entries, r, _choice_pool)

    def draw():
        print(f"{Fore.YELLOW}{display_means(means)}{stylex}")
        print(hanjaart.best_row(choices, [str(i) for i in range(1, len(choices) + 1)]))

    draw()
    while 1:
        A = read_answer(entries, stats, "choice", draw)
        if A.isdigit() and 1 <= int(A) <= len(choices):
            A = choices[int(A) - 1]
        if A in choices or A in DONT_KNOW:
            break
        print(f"{Fore.RED}1~{len(choices)} 사이의 번호를 입력해주세요.{stylex}")
    ok = A == hanja
    if ok:
        print(f"{Fore.GREEN}정답입니다!{stylex}")
    elif A not in DONT_KNOW:
        picked = next(e for e in _choice_pool if e[0] == A)
        print(f"{Fore.RED}오답입니다{stylex}  고른 한자 {A} : {display_means(picked[1])}")
    show_hanja(hanja, means)
    print('')
    return ok


ASKERS = {"hanja": _ask, "word": _ask_word, "choice": _ask_choice}


def run_command(command):
    if command == "등록":
        Downloadimage.main()
    elif command == "사전":
        printhanza.main()


def play(entries, empty_message, kind="hanja"):
    name, unit = KIND_NAMES[kind]
    remaining = list(range(len(entries)))
    random.shuffle(remaining)
    # 뒤에서부터 꺼내므로 먼저 낼 한자를 끝에 둠 (같은 순위 안에서는 섞인 순서 유지)
    remaining.sort(key=lambda r: priority(entries[r][0], kind), reverse=True)
    weak_count = sum(1 for e in entries if is_weak(e[0], kind))
    if weak_count:
        print(f"{Fore.GREEN}틀린 적 있는 {name} {weak_count}{unit}를 먼저 냅니다.{stylex}")
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
        # 지금 문제와 다시 낼 오답을 뺀 나머지는 끝난 한자
        done = len(entries) - len(remaining) - len(retry) - 1
        progress = "진행 " + progress_bar(done, len(retry), len(entries), unit)
        result = ask(entries, r, stats, progress, kind)
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
        print_result("최종 결과", entries, stats, kind)
    run_command(command)


def introduce(entries, chunk):
    """새 묶음의 한자를 한 글자씩 보여준다. 도중에 그만두면 False."""
    for i, r in enumerate(chunk, 1):
        hanja, means, _ = entries[r]
        print(hanjaart.best(hanja))
        show_hanja(hanja, means)
        A = read(f"({i}/{len(chunk)}) 다음 한자 : 엔터 , 그만하기 : /종료\n")
        if is_quit(A):
            return False
        print('')
    return True


def drill(entries, chunk, learned, stats, on_mastered, title=""):
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
        done = sum(1 for s in streak.values() if s >= MASTERY_STREAK)
        progress = f"{title}  {mastery_dots(streak.values())}  외운 한자 {done}/{len(streak)}자"
        result = ask(entries, r, stats, progress)
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
            f"(엔터 : {default + 1}번부터 , 그만하기 : /종료){stylex}\n"
        )
        if is_quit(A):
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
        command = drill(entries, chunk, learned, stats, mastered, title)
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


def word_quiz():
    grade = ask_grade(allow_all=True)
    if grade is None:
        return
    entries = word_entries(grade)
    if not entries:
        print(f"{Fore.RED}낼 수 있는 한자어가 없습니다. 먼저 한자를 더 등록해주세요.{stylex}\n")
        return
    print(f"{Fore.GREEN}한자어 {len(entries)}개 : 한자어를 보고 읽는 법(독음)을 한글로 입력하세요.{stylex}")
    play(entries, "한자어를 모두 풀었습니다!", "word")


def choice_quiz():
    grade = ask_grade(allow_all=True)
    if grade is None:
        return
    all_entries = hanzadata.load_all()
    entries = [e for e in all_entries if not grade or e[2] == grade]
    if len(all_entries) < CHOICE_COUNT or not entries:
        print(f"{Fore.RED}낼 수 있는 한자가 부족합니다. 먼저 한자를 더 등록해주세요.{stylex}\n")
        return
    # 오답 보기를 같은 부수로 고르려면 부수 정보가 필요 (다른 급수 한자는 받아 둔 것만 씀)
    fill_info(entries, range(len(entries)))
    print(f"{Fore.GREEN}훈음을 보고 알맞은 한자의 번호를 입력하세요.{stylex}")
    play(entries, "모든 한자를 풀었습니다!", "choice")


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
                "한자어 : 한자어를 보고 독음 쓰기\n"
                "골라맞히기 : 훈음을 보고 한자 고르기\n"
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
        elif A == '한자어':
            print('')
            word_quiz()
        elif A == '골라맞히기':
            print('')
            choice_quiz()
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
