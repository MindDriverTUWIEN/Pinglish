"""
Clean wrapper around the 'finglish' library.

- Suppresses noisy import-time prints.
- Exposes simple API: convert() and convert_detailed().
- Easy to extend with custom user dictionary in the future.
"""
import os
import sys
from contextlib import contextmanager
from io import StringIO
from typing import List, Tuple

@contextmanager
def _suppress_stdout():
    """Temporarily suppress stdout (used to hide finglish's 'Loading ...' messages)."""
    old = sys.stdout
    sys.stdout = StringIO()
    try:
        yield
    finally:
        sys.stdout = old

# Import under suppression
with _suppress_stdout():
    from finglish import f2p as _f2p, f2p_list as _f2p_list, f2p_word as _f2p_word

# Re-export useful symbols
__all__ = [
    "convert",
    "convert_detailed",
    "convert_word",
    "apply_user_correction",
    "patch_count",
    "to_finglish",
    "persian_punctuation",
]

# -----------------------------------------------------------------------------
# Built-in patches for very common Finglish spellings.
# These are applied at the *word* level (preferred) so we don't feed Persian
# characters back into the Finglish engine.
# -----------------------------------------------------------------------------
BUILTIN_PATCHES = {
    "chetori": "چطوری",
    "chitori": "چطوری",
    "chetory": "چطوری",
    "khub": "خوب",
    "khoob": "خوب",
    "khubam": "خوبم",
    "khoobam": "خوبم",
    "khubi": "خوبی",
    "khoobi": "خوبی",
    "salam": "سلام",
    "khodafez": "خداحافظ",
    "khodahafez": "خداحافظ",
    "merci": "مرسی",
    "mersi": "مرسی",
    "sepas": "سپاس", "sepasgozar": "سپاسگزار", "sepasgozaram": "سپاسگزارم",
    "zahmat": "زحمت", "zahmate": "زحمتت", "zahmati": "زحمتی",
    "zahamat": "زحمات", "zahaamaat": "زحمات", "zahamate": "زحمات",
    "zahmatkeshan": "زحمتکشان", "zahmatkesh": "زحمتکش",
    "halet": "حالت",
    "haleton": "حالتون",
    "haletoon": "حالتون",
    "haletun": "حالتون",
    "chera": "چرا",
    "cheraa": "چرا",
    "bara": "برای",
    "baraye": "برای",
    "oon": "اون",
    "oona": "اونا",
    "ye": "یه",
    "yeki": "یکی",
    "hastam": "هستم",
    "hasti": "هستی",
    "haste": "هست",
    "nistam": "نیستم",
    # morekhassi family (مرخصی)
    "morekhasiam": "مرخصیام", "morkhasiam": "مرخصیام", "morakhkhasiam": "مرخصیام",
    "morekhassi": "مرخصی", "morakhkhassi": "مرخصی", "morkhasi": "مرخصی",
    "morekhasim": "مرخصیم", "morkhasim": "مرخصیم",
    # raees/rais family (رییس)
    "raees": "رییس", "rais": "رییس", "raais": "رییس", "raiis": "رییس",
    "raeesam": "رییسم", "raisam": "رییسم", "raaisam": "رییسم", "raiisam": "رییسم", "raaiisam": "رییسم",
    "raeeset": "رییست", "raiset": "رییست",
    "raeesesh": "رییسش", "raeesi": "رییسی",
    # Morning greeting family (صبح + تون)
    "sobh": "صبح",
    "sobhe": "صبح",
    "sobhetoon": "صبحتون",
    "sobhetun": "صبحتون",
    "sobheton": "صبحتون",
    "sobhton": "صبحتون",
    "sobhtoon": "صبحتون",
    "sobhet": "صبحت",
    # Good morning / good night variants
    "bekheir": "بخیر",
    "bekheyr": "بخیر",
    "be kheir": "بخیر",
    "be kheyr": "بخیر",
    "sobhetoon bekheir": "صبحتون بخیر",
    "sobhetun bekheir": "صبحتون بخیر",
    # Medical / specialty terms
    "orthopedie": "ارتوپدی",
    "orthopaedie": "ارتوپدی",
    "ortopedi": "ارتوپدی",
    "ortopedie": "ارتوپدی",
    "orthopedi": "ارتوپدی",
    "orthopedic": "ارتوپدیک",
    "orthopedics": "ارتوپدی",
    "orthopedist": "ارتوپد",
    "orthoped": "ارتوپد",
    "doktor": "دکتر", "doctor": "دکتر",
    "bimarestan": "بیمارستان",
    "darmangah": "درمانگاه",
    "darou": "دارو", "daru": "دارو",
    "darman": "درمان", "darmaan": "درمان",
    "mariz": "مریض", "bimar": "بیمار",
    "ameliyat": "عمل", "amaliyat": "عملیات",
    # Days of week
    "shanbeh": "شنبه", "shanbe": "شنبه", "shambe": "شنبه",
    "yekshanbeh": "یکشنبه", "yekshanbe": "یکشنبه",
    "doshanbeh": "دوشنبه", "doshanbe": "دوشنبه",
    "seshanbeh": "سه‌شنبه", "seshanbe": "سه‌شنبه",
    "chaharshanbeh": "چهارشنبه", "chaharshanbe": "چهارشنبه",
    "panjshanbeh": "پنجشنبه", "panjshanbe": "پنجشنبه",
    "jomeh": "جمعه", "jome": "جمعه", "jumeh": "جمعه",
    # Persian solar calendar months
    "farvardin": "فروردین",
    "ordibehesht": "اردیبهشت",
    "khordad": "خرداد",
    "mordad": "مرداد",
    "shahrivar": "شهریور",
    "mehr": "مهر",
    "aban": "آبان",
    "azar": "آذر",
    "dey": "دی", "dei": "دی",
    "bahman": "بهمن",
    "esfand": "اسفند", "esphand": "اسفند", "isfand": "اسفند",
    # Family
    "baba": "بابا", "maman": "مامان",
    "pedar": "پدر", "madar": "مادر",
    "baradar": "برادر",
    "khahar": "خواهر", "khaahar": "خواهر", "khaher": "خواهر",
    "pesar": "پسر", "pessar": "پسر",
    "dokhtar": "دختر",
    "shoohar": "شوهر", "shouhar": "شوهر", "shohar": "شوهر",
    "amoo": "عمو", "amu": "عمو",
    "ammeh": "عمه", "ameh": "عمه",
    "daee": "دایی", "dayi": "دایی", "daii": "دایی",
    "khaleh": "خاله", "khale": "خاله",
    "daadaash": "داداش", "dadash": "داداش", "dadaash": "داداش",
    "aabji": "آبجی", "abji": "آبجی",
    "bache": "بچه", "baacheh": "بچه",
    "bacheha": "بچه‌ها",
    "aroos": "عروس",
    "damaad": "داماد", "damad": "داماد",
    "nave": "نوه",
    "khanoom": "خانم", "khanoum": "خانم", "khanom": "خانم",
    "agha": "آقا", "aghaa": "آقا",
    "pedarbozorg": "پدربزرگ", "madarbozorg": "مادربزرگ",
    "pedar bozorg": "پدربزرگ", "madar bozorg": "مادربزرگ",
    "naneh": "ننه",
    # Body parts
    "sar": "سر",
    "moo": "مو",
    "cheshm": "چشم",
    "goosh": "گوش",
    "bini": "بینی",
    "dahaan": "دهان", "dahan": "دهان",
    "dandan": "دندان",
    "gardan": "گردن",
    "shoneh": "شانه", "shane": "شانه",
    "bazu": "بازو",
    "dast": "دست",
    "angosht": "انگشت",
    "sineh": "سینه",
    "shekam": "شکم",
    "kamar": "کمر",
    "paa": "پا",
    "zanu": "زانو",
    "poost": "پوست",
    "khoon": "خون",
    "ghalb": "قلب",
    "maghz": "مغز",
    "ostekhan": "استخوان", "ostokhan": "استخوان",
    "adele": "عضله",
    "mafsal": "مفصل",
    # Work / office
    "karmand": "کارمند", "kaarmand": "کارمند",
    "modir": "مدیر",
    "hamkar": "همکار", "hamkaar": "همکار",
    "jalaseh": "جلسه", "jalase": "جلسه",
    "gozaresh": "گزارش",
    "projeh": "پروژه", "proje": "پروژه",
    "daftar": "دفتر",
    "hoghoogh": "حقوق", "haqooq": "حقوق",
    "pishnahad": "پیشنهاد",
    "gharardad": "قرارداد", "ghardad": "قرارداد",
    "padash": "پاداش", "paadash": "پاداش",
    "darkhast": "درخواست",
    "bimeh": "بیمه", "biimeh": "بیمه",
    "parvande": "پرونده", "parvandeh": "پرونده",
    "arzyabi": "ارزیابی",
    "hazine": "هزینه", "hazineh": "هزینه",
    "budje": "بودجه", "budjeh": "بودجه",
    "ejaze": "اجازه", "ejazeh": "اجازه",
    "sherkat": "شرکت",
    "sazman": "سازمان",
    "edare": "اداره", "edareh": "اداره",
    "karkhane": "کارخانه",
    "bakhsh": "بخش",
    "sefaresh": "سفارش",
    "motakhasses": "متخصص",
    "karshenasi": "کارشناسی",
    "nameh": "نامه",
    "resid": "رسید",
    "madrak": "مدرک",
    # Colors
    "sefid": "سفید", "safid": "سفید",
    "siyah": "سیاه", "siaah": "سیاه",
    "ghermez": "قرمز",
    "zard": "زرد",
    "naranje": "نارنجی", "naranji": "نارنجی",
    "banafsh": "بنفش",
    "khakestari": "خاکستری",
    "nili": "نیلی",
    "talaee": "طلایی", "talai": "طلایی",
    "noghrei": "نقره‌ای",
    "ghahvei": "قهوه‌ای",
    # Adjectives
    "ghashang": "قشنگ", "ghasheng": "قشنگ",
    "zibaa": "زیبا", "ziba": "زیبا",
    "bad": "بد",
    "bozorg": "بزرگ",
    "kuchik": "کوچیک", "kochik": "کوچیک", "kuchak": "کوچک",
    "sard": "سرد",
    "garm": "گرم",
    "tarik": "تاریک", "taarik": "تاریک",
    "roshan": "روشن",
    "khali": "خالی",
    "rahat": "راحت", "raahat": "راحت",
    "asaan": "آسان", "asan": "آسان",
    "tang": "تنگ",
    "baland": "بلند",
    "kutah": "کوتاه", "kootah": "کوتاه",
    "daraz": "دراز", "daraaz": "دراز",
    "tond": "تند",
    "sangin": "سنگین",
    "jaleb": "جالب",
    "geron": "گرون",
    "arzan": "ارزان", "arzon": "ارزون",
    "khaste": "خسته",
    "goshne": "گشنه",
    "teshne": "تشنه",
    "heyf": "حیف",
    "ajab": "عجب",
    "mohim": "مهم",
    "lazem": "لازم",
    "momken": "ممکن",
    "sakht": "سخت",
    "narahat": "ناراحت",
    "khoshhal": "خوشحال",
    "ghamgin": "غمگین",
    "asabani": "عصبانی",
    # Numbers
    "yek": "یک", "yak": "یک",
    "seh": "سه",
    "chahar": "چهار",
    "panj": "پنج",
    "shish": "شش",
    "haft": "هفت",
    "hasht": "هشت",
    "dah": "ده",
    "yazdah": "یازده",
    "davazdah": "دوازده",
    "sizdah": "سیزده",
    "chahardah": "چهارده",
    "panzdah": "پانزده",
    "shanzdah": "شانزده",
    "hefdah": "هفده", "hivdah": "هفده",
    "hejdah": "هجده", "hijdah": "هجده",
    "nuzdah": "نوزده",
    "bist": "بیست",
    "chehel": "چهل",
    "panjah": "پنجاه",
    "shast": "شصت",
    "haftad": "هفتاد",
    "hashtad": "هشتاد",
    "navad": "نود",
    "hezar": "هزار", "hazar": "هزار",
    # More verb forms
    "neveshtam": "نوشتم", "neveshti": "نوشتی", "nevesht": "نوشت",
    "gereftam": "گرفتم", "gerefti": "گرفتی", "gereft": "گرفت",
    "bordam": "بردم", "bordi": "بردی", "bord": "برد",
    "avordam": "آوردم", "avordi": "آوردی", "avord": "آورد",
    "pokhtam": "پختم", "pokhti": "پختی", "pokht": "پخت",
    "khordam": "خوردم", "khordi": "خوردی", "khord": "خورد",
    "khabidam": "خوابیدم", "khabidi": "خوابیدی", "khabid": "خوابید",
    "khundam": "خوندم", "khundi": "خوندی", "khund": "خوند",
    "residam": "رسیدم", "residi": "رسیدی",
    "bezan": "بزن", "begir": "بگیر", "biar": "بیار",
    "bede": "بده", "bebr": "ببر",
    "nazan": "نزن", "nagir": "نگیر",
    "tamoom": "تموم", "tamam": "تمام",
    "shoro": "شروع", "shoroo": "شروع",
    # Common phrases
    "mamnoonam": "ممنونم",
    "khaste nabashi": "خسته نباشی",
    "movafagh bashi": "موفق باشی",
    "be salamati": "به سلامتی",
    "dast shoma dard nakone": "دست شما درد نکنه",
    "movazebet bash": "مواظبت باش",
    # Colloquial adjective forms the engine often mangles
    "bahale": "باحاله", "bahaale": "باحاله", "bahala": "باحال",
    "zahmate shoma": "زحمت شما", "zahmat shoma": "زحمت شما",
    "zahmate shomaa": "زحمت شما",
    "ghat": "قطع", "ghat shode": "قطع شده", "ghat shod": "قطع شد",
    "pulam": "پولم", "poolam": "پولم", "poulam": "پولم",
    "khoda hafez": "خداحافظ", "khoda haafaz": "خداحافظ",
    # خوش‌احوالید / خوش احوالید family
    "khoshahvalid": "خوش احوالید",
    "khosh ahvalid": "خوش احوالید",
    "khosh-ahvalid": "خوش احوالید",
    "khoshaahvalid": "خوش احوالید",
    "khoshahvaleed": "خوش احوالید",
    "khoshahvaleid": "خوش احوالید",
    "khosh ahvaleed": "خوش احوالید",
    "khoshahvali": "خوش احوالی",
    "khosh ahvali": "خوش احوالی",
    "khoshahvalam": "خوش احوالم",
    "khosh ahvalam": "خوش احوالم",
    "khoshahvalim": "خوش احوالیم",
    "khosh ahvalim": "خوش احوالیم",
}

# -----------------------------------------------------------------------------
# Community dictionary (bulk Finglish→Persian mappings)
#
# Load order (later wins on conflict):
#   1. data/community_dict.txt  — large community DB (2000+ entries)
#   2. community_patches.py     — live hand-curated additions
#   3. BUILTIN_PATCHES          — high-priority curated fixes (always win)
#
# Rebuild community_dict.txt with:  python scripts/build_community_dict.py
# -----------------------------------------------------------------------------
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent / "data"
_COMMUNITY_DICT_PATH = _DATA_DIR / "community_dict.txt"


def _load_community_dict_file(path: Path = _COMMUNITY_DICT_PATH) -> dict[str, str]:
    """
    Load community dict (supports multi-word Finglish keys).

    Preferred format (one entry per line):
        finglish key<TAB>persian value

    Falls back to first-whitespace split for older space-separated files
    (single-token keys only).
    """
    out: dict[str, str] = {}
    if not path.exists():
        return out
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "\t" in line:
                key, val = line.split("\t", 1)
            else:
                parts = line.split(None, 1)
                if len(parts) != 2:
                    continue
                key, val = parts
            key, val = key.strip().lower(), val.strip()
            if key and val:
                out[key] = val
    except OSError:
        pass
    return out


try:
    from community_patches import COMMUNITY_PATCHES
except ImportError:
    COMMUNITY_PATCHES = {}

_USER_CORRECTIONS_PATH = _DATA_DIR / "user_corrections.txt"


def _load_user_corrections(path: Path = _USER_CORRECTIONS_PATH) -> dict[str, str]:
    """User-chosen spellings from the Suggested Alternatives UI (highest priority)."""
    return _load_community_dict_file(path)


_FILE_PATCHES = _load_community_dict_file()
_USER_CORRECTIONS = _load_user_corrections()
# Merge: file → community → builtin → user corrections (user always wins)
_ALL_PATCHES: dict[str, str] = {
    **_FILE_PATCHES,
    **COMMUNITY_PATCHES,
    **BUILTIN_PATCHES,
    **_USER_CORRECTIONS,
}

# Split single-word vs multi-word (phrase) patches
_WORD_PATCHES = {k: v for k, v in _ALL_PATCHES.items() if " " not in k}
_PHRASE_PATCHES = {k: v for k, v in _ALL_PATCHES.items() if " " in k}
# Longest phrases first so "sobhetoon bekheir" beats shorter fragments
_PHRASE_KEYS_SORTED = sorted(_PHRASE_PATCHES.keys(), key=len, reverse=True)

import re
_word_re = re.compile(r"([A-Za-z']+)([^A-Za-z']*)")  # Latin Finglish tokens only


def _rebuild_patch_indexes() -> None:
    global _WORD_PATCHES, _PHRASE_PATCHES, _PHRASE_KEYS_SORTED, _REVERSE_WORDS
    _WORD_PATCHES = {k: v for k, v in _ALL_PATCHES.items() if " " not in k}
    _PHRASE_PATCHES = {k: v for k, v in _ALL_PATCHES.items() if " " in k}
    _PHRASE_KEYS_SORTED = sorted(_PHRASE_PATCHES.keys(), key=len, reverse=True)
    _REVERSE_WORDS = None
    _FINGLISH_CACHE.clear()


def apply_user_correction(finglish: str, persian: str) -> None:
    """
    Treat a Suggested Alternative as the correct spelling for this Finglish word.

    Updates the live dictionary and appends/updates data/user_corrections.txt
    so the choice is used as the default output from now on.
    """
    key = (finglish or "").strip().lower()
    val = (persian or "").strip()
    if not key or not val:
        return

    _USER_CORRECTIONS[key] = val
    _ALL_PATCHES[key] = val
    _rebuild_patch_indexes()

    # Persist: rewrite full user corrections file (small, simple)
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        lines = [
            "# User corrections from Suggested Alternatives (finglish<TAB>persian)",
            "# These override the engine and community dictionary.",
        ]
        for k in sorted(_USER_CORRECTIONS.keys()):
            lines.append(f"{k}\t{_USER_CORRECTIONS[k]}")
        _USER_CORRECTIONS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        pass


def patch_count() -> dict[str, int]:
    """Return dictionary size stats (for UI / debugging)."""
    return {
        "total": len(_ALL_PATCHES),
        "words": len(_WORD_PATCHES),
        "phrases": len(_PHRASE_PATCHES),
        "from_file": len(_FILE_PATCHES),
        "user_corrections": len(_USER_CORRECTIONS),
    }

def _apply_phrase_patches(text: str) -> str:
    """Replace known multi-word Finglish phrases (case-insensitive, whole words only)."""
    if not _PHRASE_KEYS_SORTED:
        return text
    working = text
    for phrase in _PHRASE_KEYS_SORTED:
        # Whole-phrase match: not embedded inside a longer Latin token
        # e.g. "kheili khub" must not match inside "kheili khubi"
        pattern = re.compile(
            rf"(?<![A-Za-z]){re.escape(phrase)}(?![A-Za-z])",
            re.IGNORECASE,
        )
        working, n = pattern.subn(_PHRASE_PATCHES[phrase], working)
        # continue so longer-then-shorter order still applies cleanly
    return working


def _convert_token(token: str, punct: str, cutoff: int = 3) -> str:
    """Convert or patch a single token + its trailing punctuation."""
    key = token.lower()
    if key in _WORD_PATCHES:
        return _WORD_PATCHES[key] + punct
    # Otherwise let the engine handle the token
    try:
        res = _f2p_word(token, cutoff=cutoff)
        if res:
            return res[0][0] + punct
    except Exception:
        pass
    return token + punct


def _convert_latin_runs(text: str, cutoff: int = 3) -> str:
    """Convert Latin-letter runs in a mixed string; leave Persian as-is."""
    out_parts: list[str] = []
    pos = 0
    for m in _word_re.finditer(text):
        # Preserve any non-Latin gap (including Persian from phrase patches)
        if m.start() > pos:
            out_parts.append(text[pos:m.start()])
        word, punct = m.group(1), m.group(2)
        out_parts.append(_convert_token(word, punct, cutoff))
        pos = m.end()
    if pos < len(text):
        out_parts.append(text[pos:])
    return "".join(out_parts)


_PERSIAN_MARKS = str.maketrans({"?": "؟", ";": "؛"})
_LATIN_COMMA = re.compile(r"(?<!\d),|,(?!\d)")  # 1,000 keeps its comma


def persian_punctuation(text: str) -> str:
    """Persian marks for Persian text: ? → ؟, , → ،, ; → ؛."""
    if not text:
        return text
    return _LATIN_COMMA.sub("،", text.translate(_PERSIAN_MARKS))


def convert(phrase: str, max_word_size: int = 15, cutoff: int = 3) -> str:
    """Convert a full Finglish phrase. Phrase then word patches take priority over the engine."""
    if not phrase or not phrase.strip():
        return ""
    # 1) multi-word community / builtin phrases
    after_phrases = _apply_phrase_patches(phrase)
    # 2) word-level patches + engine for remaining Latin tokens
    result = _convert_latin_runs(after_phrases, cutoff=cutoff)
    # Final safety: if result is empty or identical to input, fall back to original engine
    if not result.strip() or result.strip() == phrase.strip():
        try:
            return persian_punctuation(_f2p(phrase, max_word_size=max_word_size, cutoff=cutoff))
        except Exception:
            return phrase
    return persian_punctuation(result)


def convert_detailed(phrase: str, max_word_size: int = 15, cutoff: int = 3) -> List[List[Tuple[str, float]]]:
    if not phrase or not phrase.strip():
        return []
    # Prefer patched primary conversion; attach engine alternatives when available
    try:
        engine = _f2p_list(phrase, max_word_size=max_word_size, cutoff=cutoff)
    except Exception:
        engine = None
    words = [w for w in re.findall(r"[A-Za-z']+", phrase) if w]
    if not words:
        return engine or []
    detailed: List[List[Tuple[str, float]]] = []
    for w in words:
        key = w.lower()
        if key in _WORD_PATCHES:
            detailed.append([(_WORD_PATCHES[key], 1.0)])
        else:
            try:
                alts = _f2p_word(w, cutoff=cutoff) or [(w, 0.0)]
            except Exception:
                alts = [(w, 0.0)]
            detailed.append(alts)
    return detailed if detailed else (engine or [])


def convert_word(word: str, cutoff: int = 3) -> List[Tuple[str, float]]:
    if not word or not word.strip():
        return []
    key = word.lower()
    if key in _WORD_PATCHES:
        return [(_WORD_PATCHES[key], 1.0)]
    if key in _ALL_PATCHES:
        return [(_ALL_PATCHES[key], 1.0)]
    try:
        return _f2p_word(word, cutoff=cutoff)
    except Exception:
        return [(word, 0.0)]


# Example usage / quick manual test
if __name__ == "__main__":
    stats = patch_count()
    print(f"Dictionary: {stats['total']} total "
          f"({stats['words']} words, {stats['phrases']} phrases, "
          f"{stats['from_file']} from community file)")
    tests = [
        "salam chetori",
        "chetori halet khoobeh?",
        "man ye doost daram ke kheili bahale",
        "khodafez ta farda",
        "in yek test ast baraye tabdil finglish be farsi",
        "Sobhetoon bekheir",
        "sobhetoon bekheyr",
        "mikham beram khune",
        "lotfan komakam kon",
        "emrooz hava kheili garmast",
        "dooset daram",
        "mamnoon az zahmate shoma",
    ]
    for t in tests:
        print(f"IN : {t}")
        print(f"OUT: {convert(t)}")
        print("---")


# -----------------------------------------------------------------------------
# Persian → Finglish, for words heard by the microphone.
# The Finglish is written into Pinglish Input, so it must convert back into the
# same Persian word. Known words use the dictionaries above in reverse. Other
# words are spelled out letter by letter, and a spelling that converts back to
# the same word is preferred.
# -----------------------------------------------------------------------------

_REVERSE_WORDS = None  # persian -> finglish, built on first use
_FINGLISH_CACHE: dict[str, str] = {}

_PERSIAN_PUNCT = {"؟": "?", "،": ",", "؛": ";", "«": '"', "»": '"'}
_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_ARABIC_FORMS = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک", "ة": "ه", "ۀ": "ه"})
_DIACRITICS = re.compile("[ً-ٰٟـ]")
_CONSONANTS = {
    "ب": "b", "پ": "p", "ت": "t", "ث": "s", "ج": "j", "چ": "ch", "ح": "h",
    "خ": "kh", "د": "d", "ذ": "z", "ر": "r", "ز": "z", "ژ": "zh", "س": "s",
    "ش": "sh", "ص": "s", "ض": "z", "ط": "t", "ظ": "z", "غ": "gh", "ف": "f",
    "ق": "gh", "ک": "k", "گ": "g", "ل": "l", "م": "m", "ن": "n", "ه": "h",
}
_VOWEL_LETTERS = set("اآوی")


def _reverse_words() -> dict[str, str]:
    """One Finglish spelling per Persian word: user choices first, no "aa"."""
    global _REVERSE_WORDS
    if _REVERSE_WORDS is None:
        best: dict[str, tuple] = {}
        for order, (key, val) in enumerate(_ALL_PATCHES.items()):
            if " " in key or not re.fullmatch(r"[a-z']+", key):
                continue
            rank = (0 if key in _USER_CORRECTIONS else 1, key.count("aa"), order)
            if val not in best or rank < best[val][0]:
                best[val] = (rank, key)
        _REVERSE_WORDS = {val: key for val, (_rank, key) in best.items()}
    return _REVERSE_WORDS


def _spell_out(word: str, initial_vowel: str, waw: str, final_he: str) -> str:
    """Letter-by-letter Finglish. Short vowels are not written in Persian, so
    one is added after a word-initial consonant, where Persian always has one."""
    out: list[str] = []
    n = len(word)
    i = 0
    while i < n:
        ch = word[i]
        nxt = word[i + 1] if i + 1 < n else ""
        first, last = i == 0, i == n - 1
        prev_vowel = i > 0 and word[i - 1] in _VOWEL_LETTERS
        if ch == "آ":
            out.append("a")
        elif ch == "ا":
            if first and nxt in ("ی", "و"):
                out.append("")           # این → in, او → oo
            elif first:
                out.append(initial_vowel or "a")
            else:
                out.append("a")
        elif ch == "و":
            if first or nxt in ("ا", "ی") and not last or prev_vowel:
                if word[i - 1:i] == "خ" and nxt == "ا":
                    out.append("")       # خواب → khab
                else:
                    out.append("v")
            else:
                out.append(waw)
        elif ch == "ی":
            if first or prev_vowel or (nxt in ("ا", "و") and not last):
                out.append("y")
            else:
                out.append("i")
        elif ch == "ه" and last and i > 0:
            out.append("h" if prev_vowel else final_he)
        elif ch in ("ع", "ء", "أ", "ئ", "إ", "ؤ"):
            out.append({"ع": "a" if first else "'", "ء": "'", "أ": "a", "ئ": "e",
                        "إ": "e", "ؤ": "o"}[ch])
        elif ch == "م" and last and n >= 4 and not prev_vowel:
            out.append("am")             # ending "I …": دوستم → doostam, خریدم → kharidam
        elif ch in _CONSONANTS:
            out.append(_CONSONANTS[ch])
            if first and nxt and nxt not in _VOWEL_LETTERS and initial_vowel:
                out.append(initial_vowel)
        else:
            out.append("")
        i += 1
    return re.sub(r"'+", "'", "".join(out)).strip("'")


def _finglish_core(word: str) -> str:
    """Finglish for one Persian word without punctuation."""
    known = _reverse_words().get(word)
    if known:
        return known
    plain = word.replace("‌", "")
    known = _reverse_words().get(plain)
    if known:
        return known
    first_try = ""
    for initial_vowel in ("e", "a", "o", ""):
        for waw in ("oo", "o", "u"):
            for final_he in ("eh", "e"):
                cand = _spell_out(plain, initial_vowel, waw, final_he)
                if not cand:
                    continue
                first_try = first_try or cand
                try:
                    back = convert_word(cand)
                except Exception:
                    back = []
                if back and back[0][0] in (word, plain):
                    return cand
    return first_try


def to_finglish(word: str) -> str:
    """Finglish for one Persian word, keeping punctuation (گرونه. → gerooneh.).

    Latin text and digits are kept as they are.
    """
    if not word:
        return ""
    cached = _FINGLISH_CACHE.get(word)
    if cached is not None:
        return cached
    text = _DIACRITICS.sub("", word.translate(_ARABIC_FORMS)).translate(_PERSIAN_DIGITS)
    for fa, en in _PERSIAN_PUNCT.items():
        text = text.replace(fa, en)
    parts = re.split(r"([؀-ۿ‌]+)", text)
    out = "".join(_finglish_core(p) if re.match(r"[؀-ۿ]", p) else p for p in parts)
    if len(_FINGLISH_CACHE) > 5000:
        _FINGLISH_CACHE.clear()
    _FINGLISH_CACHE[word] = out
    return out
