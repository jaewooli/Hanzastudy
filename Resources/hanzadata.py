import json
import os

FIELD_SEP = "\t"


def file_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "Hanza.txt")


def ensure_file():
    """Create Hanza.txt if missing. Returns True if it just created it."""
    path = file_path()
    if not os.path.exists(path):
        with open(path, "x", encoding="utf-8") as f:
            f.write("")
        return True
    return False


def _parse_old_format(line):
    hanja, means_str = line.split(":", 1)
    hanja = hanja.strip()
    means_str = means_str.strip().strip("[]")
    means = [m.strip(" '\"") for m in means_str.split(",") if m.strip(" '\"")]
    return hanja, means, 0


def _parse_line(line):
    if FIELD_SEP in line:
        hanja, means_str, grade_str = line.split(FIELD_SEP)
        means = means_str.split(",")
        try:
            grade = int(grade_str)
        except ValueError:
            grade = 0
        return hanja, means, grade
    return _parse_old_format(line)


def _format_line(hanja, means, grade=0):
    return f"{hanja}{FIELD_SEP}{','.join(means)}{FIELD_SEP}{grade}\n"


def load_all():
    """Return list of (hanja, means, grade). Migrates old-format lines in place."""
    ensure_file()
    path = file_path()
    with open(path, "r", encoding="utf-8") as f:
        raw_lines = [line for line in f.read().split("\n") if line.strip()]
    entries = []
    needs_migration = False
    for line in raw_lines:
        if FIELD_SEP not in line:
            needs_migration = True
        entries.append(_parse_line(line))
    if needs_migration:
        save_all(entries)
    return entries


def save_all(entries):
    path = file_path()
    with open(path, "w", encoding="utf-8") as f:
        for hanja, means, grade in entries:
            f.write(_format_line(hanja, means, grade))


def append_entry(hanja, means, grade=0):
    ensure_file()
    path = file_path()
    with open(path, "a", encoding="utf-8") as f:
        f.write(_format_line(hanja, means, grade))


def find_entry(hanja):
    for entry in load_all():
        if entry[0] == hanja:
            return entry
    return None


def delete_entry(hanja):
    entries = load_all()
    remaining = [e for e in entries if e[0] != hanja]
    if len(remaining) == len(entries):
        return False
    save_all(remaining)
    return True


def clear_all():
    save_all([])


def learned_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "Learned.txt")


def _load_learned_all():
    path = learned_path()
    if not os.path.exists(path):
        return {}
    learned = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f.read().split("\n"):
            if FIELD_SEP not in line:
                continue
            grade_str, chars = line.split(FIELD_SEP, 1)
            if grade_str.isdigit():
                learned[int(grade_str)] = set(chars)
    return learned


def load_learned(grade):
    """급수학습에서 묶음을 다 외운 한자 집합."""
    return _load_learned_all().get(grade, set())


def save_learned(grade, chars):
    learned = _load_learned_all()
    learned[grade] = set(chars)
    with open(learned_path(), "w", encoding="utf-8") as f:
        for g in sorted(learned):
            f.write(f"{g}{FIELD_SEP}{''.join(sorted(learned[g]))}\n")


def info_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "HanzaInfo.json")


def load_info():
    """한자별 부수·예시 한자어 캐시: {한자: {"radical": ..., "words": [[한자어, 읽기, 뜻], ...]}}"""
    path = info_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_info(info):
    with open(info_path(), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)


def record_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "Record.json")


def load_records():
    """한자별 풀이 기록: {한자: {"right": 맞힌 수, "wrong": 틀린 수, "streak": 연속 정답, "last": 마지막 풀이 시각}}"""
    path = record_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_records(records):
    with open(record_path(), "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=1)
