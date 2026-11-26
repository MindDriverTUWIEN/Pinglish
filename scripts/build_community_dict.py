# -*- coding: utf-8 -*-
"""
Build a large community Finglish→Persian dictionary for offline conversion.

Sources (priority low → high; later wins on conflict):
  1. elektito/finglish f2p-dict.txt  (community dictionary shipped with the engine)
  2. community_patches.py           (hand-curated bulk vocabulary)
  3. EXTRA_ENTRIES below            (expanded everyday / colloquial spellings)

Output: data/community_dict.txt  (one "finglish persian" pair per line)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "community_dict.txt"
META = ROOT / "data" / "community_dict_meta.json"

# ---------------------------------------------------------------------------
# Large expansion: common Finglish spellings not covered well by the engine.
# Multiple Latin variants map to the same Persian form on purpose.
# ---------------------------------------------------------------------------
EXTRA_ENTRIES: dict[str, str] = {
    # --- Core pronouns / particles ---
    "man": "من", "to": "تو", "u": "او", "ou": "او", "oo": "او",
    "ma": "ما", "maa": "ما", "shoma": "شما", "shomaa": "شما",
    "anha": "آنها", "onha": "اونا", "oonha": "اونا",
    "in": "این", "oon": "اون", "an": "آن", "aan": "آن",
    "ke": "که", "va": "و", "o": "و", "ya": "یا", "yaa": "یا",
    "agar": "اگر", "age": "اگه", "ageh": "اگه",
    "vali": "ولی", "amma": "اما", "ama": "اما",
    "pas": "پس", "chon": "چون", "choun": "چون", "chonke": "چونکه",
    "ta": "تا", "taa": "تا", "ham": "هم", "hamchenin": "همچنین",
    "hamin": "همین", "hamoon": "همون", "hamun": "همون",
    "digar": "دیگر", "digarha": "دیگران",
    "hich": "هیچ", "hichkas": "هیچ‌کس", "hichki": "هیچکی",
    "hame": "همه", "hameh": "همه", "hamegi": "همگی",
    "har": "هر", "harche": "هرچه", "har chi": "هر چی",
    "kasi": "کسی", "chizi": "چیزی", "jaei": "جایی", "jaayi": "جایی",
    "vaghti": "وقتی", "vaghtike": "وقتی‌که", "key": "کی", "koja": "کجا",
    "chera": "چرا", "chetor": "چطور", "chetori": "چطوری",
    "chand": "چند", "cheghadr": "چقدر", "cheghader": "چقدر",
    "kodam": "کدام", "kodom": "کدوم", "koom": "کدوم",

    # --- To be / have ---
    "hast": "هست", "hastam": "هستم", "hasti": "هستی", "hastim": "هستیم",
    "hastid": "هستید", "hastan": "هستن", "hastand": "هستند",
    "nist": "نیست", "nistam": "نیستم", "nisti": "نیستی", "nistim": "نیستیم",
    "nistid": "نیستید", "nistan": "نیستن", "nistand": "نیستند",
    "ast": "است", "bud": "بود", "bood": "بود", "boud": "بود",
    "budam": "بودم", "boodam": "بودم", "budi": "بودی", "boodi": "بودی",
    "budim": "بودیم", "boodim": "بودیم", "budand": "بودند", "boodan": "بودن",
    "bash": "باش", "basham": "باشم", "bashi": "باشی", "bashe": "باشه",
    "basheh": "باشه", "bashim": "باشیم", "bashid": "باشید", "bashan": "باشن",
    "nabash": "نباش", "nabashe": "نباشه",
    "shod": "شد", "shodam": "شدم", "shodi": "شدی", "shodim": "شدیم",
    "shodand": "شدند", "shodan": "شدن",
    "misham": "میشم", "mishi": "میشی", "mishe": "میشه", "misheh": "میشه",
    "mishim": "میشیم", "mishid": "میشید", "mishan": "میشن",
    "nemisham": "نمیشم", "nemishe": "نمیشه", "nemisheh": "نمیشه",
    "besham": "بشم", "beshi": "بشی", "beshe": "بشه", "besheh": "بشه",
    "darad": "دارد", "dare": "داره", "daram": "دارم", "dari": "داری",
    "darim": "داریم", "darid": "دارید", "daran": "دارن", "darand": "دارند",
    "nadaram": "ندارم", "nadari": "نداری", "nadare": "نداره",
    "nadarim": "نداریم", "nadarid": "ندارید", "nadaran": "ندارن",
    "dasht": "داشت", "dashtam": "داشتم", "dashti": "داشتی",
    "dashtim": "داشتیم", "dashtand": "داشتند",
    "dashte": "داشته", "dashteh": "داشته",

    # --- Go / come ---
    "raft": "رفت", "raftam": "رفتم", "rafti": "رفتی", "raftim": "رفتیم",
    "raftid": "رفتید", "raftand": "رفتند", "raftan": "رفتن",
    "miram": "میرم", "miri": "میری", "mire": "میره", "mireh": "میره",
    "mirim": "میریم", "mirid": "میرید", "miran": "میرن",
    "beram": "برم", "beri": "بری", "bere": "بره", "bereh": "بره",
    "berim": "بریم", "berid": "برید", "beran": "برن",
    "naram": "نرم", "nari": "نری", "nare": "نره",
    "amad": "آمد", "amadam": "آمدم", "amadi": "آمدی", "amadan": "آمدن",
    "oomad": "اومد", "oomadam": "اومدم", "oomadi": "اومدی", "oomadan": "اومدن",
    "umad": "اومد", "umadam": "اومدم",
    "miam": "میام", "miay": "میای", "miad": "میاد", "miyad": "میاد",
    "miayim": "میایم", "miayn": "میاین", "miyan": "میان",
    "biam": "بیام", "biay": "بیای", "biad": "بیاد", "biayim": "بیایم",
    "bia": "بیا", "biya": "بیا", "biaid": "بیایید", "biyayid": "بیایید",
    "nayad": "نیاید", "nayad": "نیاد", "nia": "نیا", "niya": "نیا",

    # --- Say / speak ---
    "goft": "گفت", "goftam": "گفتم", "gofti": "گفتی", "goftim": "گفتیم",
    "goftand": "گفتند", "goftan": "گفتن", "gofte": "گفته",
    "migam": "میگم", "migi": "میگی", "mige": "میگه", "migeh": "میگه",
    "migim": "میگیم", "migid": "میگید", "migan": "میگن",
    "begam": "بگم", "begi": "بگی", "bege": "بگه", "begim": "بگیم",
    "begid": "بگید", "began": "بگن", "bego": "بگو", "begoo": "بگو",
    "nagam": "نگم", "nagi": "نگی", "nage": "نگه",
    "harf": "حرف", "harf zadan": "حرف زدن", "sohbat": "صحبت",
    "gap": "گپ", "dastan": "داستان", "dastaan": "داستان",

    # --- See / look / know ---
    "did": "دید", "didam": "دیدم", "didi": "دیدی", "didim": "دیدیم",
    "didand": "دیدند", "didan": "دیدن", "dide": "دیده",
    "mibinam": "می‌بینم", "mibini": "می‌بینی", "mibine": "می‌بینه",
    "mibinim": "می‌بینیم", "mibinin": "می‌بینین", "mibinan": "می‌بینن",
    "bebinam": "ببینم", "bebini": "ببینی", "bebine": "ببینه",
    "bebin": "ببین", "bebinid": "ببینید", "bebinin": "ببینین",
    "negah": "نگاه", "nega": "نگاه", "nega kon": "نگاه کن",
    "midunam": "میدونم", "miduni": "میدونی", "midune": "میدونه",
    "midunim": "میدونیم", "midunin": "میدونین", "midunan": "میدونن",
    "midanam": "می‌دانم", "midani": "می‌دانی", "midanad": "می‌داند",
    "bedunam": "بدونم", "beduni": "بدونی", "bedun": "بدون",
    "nedunam": "ندونم", "nemidunam": "نمیدونم", "nemiduni": "نمیدونی",
    "fahmidam": "فهمیدم", "fahmidi": "فهمیدی", "fahmid": "فهمید",
    "mifahmam": "میفهمم", "mifahmi": "میفهمی", "mifahme": "میفهمه",
    "befahm": "بفهم", "befahmam": "بفهمم",

    # --- Want / can / must ---
    "mikham": "می‌خوام", "mikhai": "می‌خوای", "mikhad": "می‌خواد",
    "mikhaym": "می‌خوایم", "mikhayn": "می‌خواین", "mikhan": "می‌خوان",
    "mikhaham": "می‌خواهم", "mikhahi": "می‌خواهی", "mikhahad": "می‌خواهد",
    "bekham": "بخوام", "bekhai": "بخوای", "bekhad": "بخواد",
    "nemikham": "نمی‌خوام", "nemikhad": "نمی‌خواد",
    "mitunam": "می‌تونم", "mituni": "می‌تونی", "mitune": "می‌تونه",
    "mitunim": "می‌تونیم", "mitunin": "می‌تونین", "mitunan": "می‌تونن",
    "mitavanam": "می‌توانم", "mitavani": "می‌توانی", "mitavanad": "می‌تواند",
    "betunam": "بتونم", "betuni": "بتونی", "betune": "بتونه",
    "betavanam": "بتوانم", "nemitunam": "نمی‌تونم", "nemituni": "نمی‌تونی",
    "bayad": "باید", "bayad": "باید", "lazem": "لازم", "lazeme": "لازمه",
    "majbur": "مجبور", "majboor": "مجبور", "majburam": "مجبورم",
    "momkene": "ممکنه", "momkeneh": "ممکنه", "emkan": "امکان",
    "shayad": "شاید", "shaayad": "شاید", "momken": "ممکن",

    # --- Do / make / give / take ---
    "kard": "کرد", "kardam": "کردم", "kardi": "کردی", "kardim": "کردیم",
    "kardand": "کردند", "kardan": "کردن", "karde": "کرده",
    "mikonam": "می‌کنم", "mikoni": "می‌کنی", "mikone": "می‌کنه",
    "mikonim": "می‌کنیم", "mikonin": "می‌کنین", "mikonan": "می‌کنن",
    "bekonam": "بکنم", "bekoni": "بکنی", "bekone": "بکنه",
    "bekon": "بکن", "bekonid": "بکنید", "nakon": "نکن", "nakonam": "نکنم",
    "dad": "داد", "dadam": "دادم", "dadi": "دادی", "dadim": "دادیم",
    "dadand": "دادند", "dadan": "دادن",
    "midam": "میدم", "midi": "میدی", "mide": "میده", "mideh": "میده",
    "midim": "میدیم", "midin": "میدین", "midan": "میدن",
    "bedam": "بدم", "bedi": "بدی", "bede": "بده", "bedim": "بدیم",
    "bedid": "بدید", "bedan": "بدن", "nade": "نده", "nadam": "ندم",
    "gereft": "گرفت", "gereftam": "گرفتم", "gerefti": "گرفتی",
    "gereftim": "گرفتیم", "gereftand": "گرفتند", "gereftan": "گرفتن",
    "migiram": "می‌گیرم", "migiri": "می‌گیری", "migire": "می‌گیره",
    "migirim": "می‌گیریم", "migirin": "می‌گیرین", "migiran": "می‌گیرن",
    "begiram": "بگیرم", "begiri": "بگیری", "begire": "بگیره",
    "begir": "بگیر", "begirid": "بگیرید", "nagir": "نگیر",

    # --- Eat / drink / sleep / sit / stand ---
    "khord": "خورد", "khordam": "خوردم", "khordi": "خوردی",
    "khordim": "خوردیم", "khordan": "خوردن",
    "mikhoram": "می‌خورم", "mikhori": "می‌خوری", "mikhore": "می‌خوره",
    "bokhoram": "بخورم", "bokhori": "بخوری", "bokhor": "بخور",
    "nakhor": "نخور", "nokhordam": "نخوردم",
    "nushid": "نوشید", "nushidan": "نوشیدن",
    "minusham": "می‌نوشم", "benush": "بنوش",
    "khabid": "خوابید", "khabidam": "خوابیدم", "khabidan": "خوابیدن",
    "mikhabam": "می‌خوابم", "mikhabi": "می‌خوابی", "mikhabe": "می‌خوابه",
    "bekhabam": "بخوابم", "bekhab": "بخواب", "nakhab": "نخواب",
    "neshast": "نشست", "neshastam": "نشستم", "neshastan": "نشستن",
    "mineshinam": "می‌نشینم", "mineshini": "می‌نشینی",
    "beshinam": "بشینم", "beshin": "بشین", "beshinid": "بشینید",
    "istadam": "ایستادم", "istadan": "ایستادن", "mistad": "می‌ایستد",
    "vaysa": "وایسا", "vayssa": "وایسا", "beist": "بایست",

    # --- Write / read / work / play ---
    "nevesht": "نوشت", "neveshtam": "نوشتم", "neveshti": "نوشتی",
    "neveshtan": "نوشتن", "neveshte": "نوشته",
    "minevisam": "می‌نویسم", "minevisi": "می‌نویسی", "minevise": "می‌نویسه",
    "benevisam": "بنویسم", "benevis": "بنویس", "benevisid": "بنویسید",
    "khand": "خواند", "khandam": "خواندم", "khandan": "خواندن",
    "khund": "خوند", "khundam": "خوندم", "khundan": "خوندن",
    "mikhunam": "می‌خونم", "mikhuni": "می‌خونی", "mikhune": "می‌خونه",
    "bekhunam": "بخونم", "bekhun": "بخون", "bekhunid": "بخونید",
    "kar": "کار", "kaar": "کار", "kar kardan": "کار کردن",
    "mikonam kar": "کار می‌کنم", "kar mikonam": "کار می‌کنم",
    "bazi": "بازی", "baazi": "بازی", "bazi kardan": "بازی کردن",
    "mibazam": "می‌بازم", "bebaz": "بباز",

    # --- Love / like / think / feel ---
    "doost": "دوست", "dust": "دوست", "dooset": "دوستت", "duset": "دوستت",
    "doosetdaram": "دوستت‌دارم", "dooset daram": "دوستت دارم",
    "duset daram": "دوستت دارم", "doosesh daram": "دوستش دارم",
    "doost daram": "دوست دارم", "dust daram": "دوست دارم",
    "ashegh": "عاشق", "asheq": "عاشق", "ashegham": "عاشقم",
    "fekr": "فکر", "fekr mikonam": "فکر می‌کنم", "fekr kon": "فکر کن",
    "mifekram": "می‌فکرم", "befekr": "به‌فکر",
    "ehsas": "احساس", "ehsas mikonam": "احساس می‌کنم",
    "delam": "دلم", "delam mikhad": "دلم می‌خواد", "delam tang": "دلم تنگ",
    "delam tang shode": "دلم تنگ شده", "deltang": "دلتنگ",

    # --- Greetings & politeness ---
    "salam": "سلام", "salaam": "سلام", "dorood": "درود", "dorud": "درود",
    "khodafez": "خداحافظ", "khodahafez": "خداحافظ", "khodahaafaz": "خداحافظ",
    "befarma": "بفرما", "befarmayid": "بفرمایید", "befarmaeed": "بفرمایید",
    "lotfan": "لطفاً", "lotfanan": "لطفاً", "khahesh": "خواهش",
    "khaheshmikonam": "خواهش می‌کنم", "khahesh mikonam": "خواهش می‌کنم",
    "mamnoon": "ممنون", "mamnun": "ممنون", "mamnoonam": "ممنونم",
    "motshakeram": "متشکرم", "moteshakeram": "متشکرم",
    "merci": "مرسی", "mersi": "مرسی", "sepas": "سپاس",
    "bebakhshid": "ببخشید", "bebakhsh": "ببخش", "ozr": "عذر",
    "ozr mikham": "عذر می‌خوام", "moteassefam": "متأسفم", "motesefam": "متأسفم",
    "khaste nabashi": "خسته نباشی", "khaste nabashid": "خسته نباشید",
    "dastet dard nakone": "دستت درد نکنه", "dastetoon dard nakone": "دستتون درد نکنه",
    "ghorbanet": "قربانت", "ghorboonet": "قربونت", "ghorbanat": "قربانت",
    "movafagh bashi": "موفق باشی", "movafagh bashid": "موفق باشید",
    "be salamati": "به سلامتی", "nushe jan": "نوش جان", "nooshe jan": "نوش جان",
    "ghabool": "قبول", "ghabul": "قبول", "ghabool kon": "قبول کن",

    # --- Family (extra variants) ---
    "zan": "زن", "mard": "مرد", "adam": "آدم", "aadam": "آدم",
    "ensaan": "انسان", "ensan": "انسان", "mardom": "مردم",
    "dust": "دوست", "doostan": "دوستان", "dustan": "دوستان",
    "hamsaye": "همسایه", "hamsayeh": "همسایه",
    "mehman": "مهمان", "mehmun": "مهمون", "mehmoon": "مهمون",
    "mehmuni": "مهمونی", "mehmooni": "مهمونی",
    "aroosi": "عروسی", "arusi": "عروسی", "tavalod": "تولد",
    "tavalodet mobarak": "تولدت مبارک", "tavalodetoon mobarak": "تولدتون مبارک",

    # --- Body (extra) ---
    "del": "دل", "dil": "دل", "rooh": "روح", "ruh": "روح",
    "jan": "جان", "jaan": "جان", "joon": "جون", "jun": "جون",
    "lab": "لب", "zaban": "زبان", "zaboon": "زبون",
    "rish": "ریش", "sibil": "سبیل", "abr u": "ابرو", "abru": "ابرو",
    "pishoni": "پیشونی", "pishani": "پیشانی",
    "shane": "شانه", "shone": "شونه", "baghal": "بغل",
    "sina": "سینه", "seene": "سینه", "soorekh": "سورخ",

    # --- Home life ---
    "khane": "خانه", "khaneh": "خانه", "khoone": "خونه", "khune": "خونه",
    "khooneh": "خونه", "khuneh": "خونه",
    "dar": "در", "daar": "دار", "ghofl": "قفل", "kelid": "کلید",
    "asansor": "آسانسور", "asansoor": "آسانسور",
    "parking": "پارکینگ", "anbari": "انباری",
    "ashpazkhaneh": "آشپزخانه", "ashpazkhoone": "آشپزخونه",
    "sobhane": "صبحانه", "nahar": "ناهار", "sham": "شام",
    "ghaza": "غذا", "ghazaa": "غذا", "khorak": "خوراک",
    "ab": "آب", "aab": "آب", "abjo": "آبجو", "sharab": "شراب",
    "chay": "چای", "chaee": "چای", "chai": "چای",
    "ghahve": "قهوه", "sharbat": "شربت", "abmive": "آبمیوه",
    "nan": "نان", "noon": "نون", "berenj": "برنج", "makaroni": "ماکارونی",
    "pizza": "پیتزا", "pitza": "پیتزا", "sandwich": "ساندویچ",
    "hamburger": "همبرگر", "sibzamini": "سیب‌زمینی",
    "salad": "سالاد", "sup": "سوپ", "ash": "آش", "aash": "آش",

    # --- Weather / nature (extra) ---
    "garmast": "گرمه", "garme": "گرمه", "sarde": "سرده", "sardast": "سرده",
    "baruni": "بارونی", "barooni": "بارونی", "aftabi": "آفتابی",
    "abri": "ابری", "meh": "مه", "meh alood": "مه‌آلود",
    "rad": "رعد", "bargh": "برق", "setare": "ستاره",
    "zamin": "زمین", "zameen": "زمین", "jahan": "جهان", "jahaan": "جهان",
    "donya": "دنیا", "donyaa": "دنیا", "alam": "عالم",

    # --- Time (extra) ---
    "emrooz": "امروز", "emruz": "امروز", "dirooz": "دیروز", "diruz": "دیروز",
    "farda": "فردا", "fardaa": "فردا", "pasfarda": "پس‌فردا",
    "emshab": "امشب", "dishab": "دیشب", "fardashab": "فرداشب",
    "sobh": "صبح", "zohr": "ظهر", "asr": "عصر", "shab": "شب",
    "alan": "الان", "alaan": "الان", "hala": "حالا", "halaa": "حالا",
    "baadan": "بعداً", "badan": "بعداً", "ghabla": "قبلاً", "ghablan": "قبلاً",
    "zood": "زود", "zud": "زود", "dir": "دیر", "deer": "دیر",
    "hanuz": "هنوز", "hanooz": "هنوز", "dige": "دیگه", "digeh": "دیگه",
    "hamishe": "همیشه", "hamisheh": "همیشه", "hichvaght": "هیچ‌وقت",
    "bazioght": "بعضی‌وقت", "bazi vaght": "بعضی وقت",
    "saat": "ساعت", "daghighe": "دقیقه", "saniye": "ثانیه",
    "rooz": "روز", "ruz": "روز", "hafte": "هفته", "mah": "ماه",
    "sal": "سال", "saal": "سال", "gharne": "قرن", "gharn": "قرن",
    "fasl": "فصل", "bahar": "بهار", "tabestan": "تابستان",
    "paeez": "پاییز", "zemestan": "زمستان",

    # --- Numbers (extra / colloquial) ---
    "sefr": "صفر", "sefr": "صفر", "yek": "یک", "yeki": "یکی", "ye": "یه",
    "do": "دو", "dota": "دوتا", "doo": "دو",
    "se": "سه", "seh": "سه", "seta": "سه‌تا",
    "chahar": "چهار", "char": "چار", "charta": "چارتا",
    "panj": "پنج", "panjta": "پنج‌تا", "shish": "شش", "shesh": "شش",
    "haft": "هفت", "hasht": "هشت", "noh": "نه", "no": "نه",
    "dah": "ده", "yazdah": "یازده", "davazdah": "دوازده",
    "bist": "بیست", "si": "سی", "sih": "سی", "chehel": "چهل",
    "panjah": "پنجاه", "shast": "شصت", "haftad": "هفتاد",
    "hashtad": "هشتاد", "navad": "نود", "sad": "صد", "saad": "صد",
    "devist": "دویست", "divist": "دویست", "sisad": "سیصد",
    "hezar": "هزار", "hazar": "هزار", "milion": "میلیون", "milyun": "میلیون",
    "miliard": "میلیارد", "milyard": "میلیارد",
    "aval": "اول", "avval": "اول", "dovom": "دوم", "dovvom": "دوم",
    "sevom": "سوم", "sevvom": "سوم", "akhar": "آخر", "aakhar": "آخر",
    "akharin": "آخرین", "avaliin": "اولین", "avalin": "اولین",

    # --- Adjectives (extra) ---
    "khub": "خوب", "khoob": "خوب", "khube": "خوبه", "khoobe": "خوبه",
    "bad": "بد", "bade": "بده", "ali": "عالی", "aali": "عالی",
    "bahal": "باحال", "bahaal": "باحال", "bahale": "باحاله", "bahaale": "باحاله",
    "kheili": "خیلی", "kheyli": "خیلی", "khili": "خیلی", "kheli": "خیلی",
    "ziad": "زیاد", "ziyad": "زیاد", "kam": "کم", "kami": "کمی",
    "bishtar": "بیشتر", "kamtar": "کمتر", "behtar": "بهتر", "badtar": "بدتر",
    "behtarin": "بهترین", "badtarin": "بدترین",
    "bozorg": "بزرگ", "kuchik": "کوچیک", "kochik": "کوچیک", "kuchak": "کوچک",
    "kuchek": "کوچک", "gonde": "گنده", "gondeh": "گنده",
    "taze": "تازه", "kohneh": "کهنه", "jadid": "جدید", "ghadimi": "قدیمی",
    "ziba": "زیبا", "zibaa": "زیبا", "ghashang": "قشنگ", "zesht": "زشت",
    "sard": "سرد", "garm": "گرم", "dagh": "داغ", "daagh": "داغ",
    "sardard": "سردرد", "dard": "درد", "dardam": "دردم",
    "rahat": "راحت", "asakht": "آسخت", "sakht": "سخت", "asan": "آسان",
    "sangin": "سنگین", "sabok": "سبک", "tond": "تند", "ahaste": "آهسته",
    "yavash": "یواش", "boland": "بلند", "kutah": "کوتاه", "kootah": "کوتاه",
    "pahn": "پهن", "barik": "باریک", "koloft": "کلفت", "nazok": "نازک",
    "por": "پر", "khali": "خالی", "tamiz": "تمیز", "kasif": "کثیف",
    "khoshk": "خشک", "khis": "خیس", "tar": "تر",
    "roshan": "روشن", "tarik": "تاریک", "mahtab": "مهتاب",
    "arzan": "ارزان", "arzon": "ارزون", "geran": "گران", "geroon": "گرون",
    "garon": "گرون", "geriun": "گرون",
    "mohem": "مهم", "lazem": "لازم", "kafi": "کافی", "kaafi": "کافی",
    "sahih": "صحیح", "dorost": "درست", "eshtbah": "اشتباه", "eshtebah": "اشتباه",
    "vaghei": "واقعی", "vaghean": "واقعاً", "vaghean": "واقعاً",
    "jad": "جد", "jedi": "جدی", "shukhi": "شوخی", "shookhi": "شوخی",
    "khoshhal": "خوشحال", "khoshhaal": "خوشحال", "narahat": "ناراحت",
    "ghamgin": "غمگین", "asabani": "عصبانی", "khaste": "خسته",
    "goshne": "گشنه", "gosne": "گسنه", "teshne": "تشنه",
    "mariz": "مریض", "bimar": "بیمار", "salem": "سالم", "saalem": "سالم",
    "ghavi": "قوی", "zaeef": "ضعیف", "zaif": "ضعیف",
    "javan": "جوان", "javaan": "جوان", "pir": "پیر", "peer": "پیر",
    "zende": "زنده", "zendeh": "زنده", "morde": "مرده", "mordeh": "مرده",

    # --- Common nouns (life) ---
    "zendegi": "زندگی", "zendegie": "زندگی", "marg": "مرگ",
    "eshgh": "عشق", "eshq": "عشق", "alaghe": "علاقه", "alagheh": "علاقه",
    "omid": "امید", "omidvar": "امیدوار", "omidvaram": "امیدوارم",
    "tars": "ترس", "mitarsam": "می‌ترسم", "betars": "بترس",
    "khande": "خنده", "khandeh": "خنده", "gerye": "گریه", "geryeh": "گریه",
    "sedaa": "صدا", "seda": "صدا", "sedaye": "صدای",
    "rang": "رنگ", "shekl": "شکل", "andaze": "اندازه", "andazeh": "اندازه",
    "ravesh": "روش", "raah": "راه", "rah": "راه", "masir": "مسیر",
    "nazar": "نظر", "nazaram": "نظرم", "aghide": "عقیده",
    "soal": "سؤال", "sual": "سؤال", "javab": "جواب", "pasokh": "پاسخ",
    "moshkel": "مشکل", "moshkelat": "مشکلات", "rahhal": "راه‌حل",
    "komak": "کمک", "komak kon": "کمک کن", "komakam kon": "کمکم کن",
    "niaz": "نیاز", "niaz daram": "نیاز دارم", "ehtiaj": "احتیاج",
    "forsat": "فرصت", "zaman": "زمان", "zamaan": "زمان", "vaght": "وقت",
    "ja": "جا", "jaa": "جا", "makan": "مکان", "makaan": "مکان",
    "shahr": "شهر", "deh": "ده", "roosta": "روستا", "rusta": "روستا",
    "keshvar": "کشور", "mellat": "ملت", "dolat": "دولت", "hokumat": "حکومت",
    "ghanun": "قانون", "ghanoon": "قانون", "hagh": "حق", "haq": "حق",
    "azadi": "آزادی", "azadii": "آزادی", "solh": "صلح", "jang": "جنگ",
    "amniat": "امنیت", "amniyat": "امنیت", "khatar": "خطر",
    "khabar": "خبر", "akhbar": "اخبار", "ettelaat": "اطلاعات",
    "etelaat": "اطلاعات", "etela": "اطلاع",

    # --- School / work (extra) ---
    "kar": "کار", "shoghl": "شغل", "shoghli": "شغلی",
    "sherkat": "شرکت", "edare": "اداره", "edareh": "اداره",
    "modir": "مدیر", "raees": "رییس", "rais": "رییس",
    "hamkar": "همکار", "karmand": "کارمند", "kargar": "کارگر",
    "hoghoogh": "حقوق", "padash": "پاداش", "ezafe": "اضافه",
    "tatil": "تعطیل", "tatilat": "تعطیلات", "morekhasi": "مرخصی",
    "jalase": "جلسه", "jalaseh": "جلسه", "mosahebe": "مصاحبه",
    "proje": "پروژه", "projeh": "پروژه", "gozaresh": "گزارش",
    "email": "ایمیل", "imeil": "ایمیل", "payam": "پیام",
    "telefon": "تلفن", "telephone": "تلفن", "zang": "زنگ",
    "call": "تماس", "tamas": "تماس", "tamas begir": "تماس بگیر",

    # --- Health ---
    "salamati": "سلامتی", "salamat": "سلامت", "darmangah": "درمانگاه",
    "bimarestan": "بیمارستان", "daru": "دارو", "darou": "دارو",
    "doctor": "دکتر", "doktor": "دکتر", "pezeshk": "پزشک",
    "parastar": "پرستار", "dandanpezeshk": "دندان‌پزشک",
    "dard": "درد", "tab": "تب", "sorfe": "سرفه", "sorfeh": "سرفه",
    "capsole": "کپسول", "ghors": "قرص", "ampul": "آمپول",
    "amaliyat": "عملیات", "ameliyat": "عمل", "jarahi": "جراحی",
    "vaksin": "واکسن", "vaccine": "واکسن", "mask": "ماسک",
    "virus": "ویروس", "anfluanza": "آنفلوآنزا", "sarmakhordegi": "سرماخوردگی",

    # --- Money / shopping (extra) ---
    "pul": "پول", "pool": "پول", "poul": "پول",
    "toman": "تومان", "tooman": "تومن", "tuman": "تومن",
    "dolar": "دلار", "dollar": "دلار", "yuro": "یورو", "euro": "یورو",
    "gheymat": "قیمت", "arzan": "ارزان", "geran": "گران",
    "kharid": "خرید", "forush": "فروش", "foroosh": "فروش",
    "kharidan": "خریدن", "forukhtan": "فروختن",
    "mikharam": "می‌خرم", "bekhar": "بخر", "befrush": "بفروش",
    "takhfif": "تخفیف", "aghsat": "اقساط", "vam": "وام",
    "bank": "بانک", "hesab": "حساب", "kart": "کارت",
    "ramz": "رمز", "password": "پسورد", "pass": "پس",
    "resid": "رسید", "factor": "فاکتور", "factor": "فاکتور",
    "maghaze": "مغازه", "forushgah": "فروشگاه", "bazar": "بازار",

    # --- Transport (extra) ---
    "mashin": "ماشین", "maashin": "ماشین", "otombil": "اتومبیل",
    "ranandegi": "رانندگی", "ranande": "راننده",
    "trafik": "ترافیک", "traffic": "ترافیک", "jadde": "جاده",
    "otoban": "اتوبان", "bozorgrah": "بزرگراه",
    "park": "پارک", "parking": "پارکینگ",
    "benzin": "بنزین", "gaz": "گاز", "naft": "نفت",
    "bilit": "بلیط", "belit": "بلیط", "ticket": "تیکت",
    "safar": "سفر", "mosafirat": "مسافرت", "mosaferat": "مسافرت",
    "mosafer": "مسافر", "tourist": "توریست", "gardeshgar": "گردشگر",

    # --- Tech (extra) ---
    "internet": "اینترنت", "net": "نت", "wifi": "وای‌فای", "wi fi": "وای‌فای",
    "site": "سایت", "websayt": "وب‌سایت", "website": "وب‌سایت",
    "app": "اپ", "barname": "برنامه", "barnameh": "برنامه",
    "download": "دانلود", "upload": "آپلود", "install": "اینستال",
    "password": "پسورد", "username": "یوزرنیم", "login": "لاگین",
    "online": "آنلاین", "offline": "آفلاین",
    "file": "فایل", "folder": "فولدر", "link": "لینک",
    "video": "ویدیو", "vido": "ویدئو", "photo": "فوتو", "aks": "عکس",
    "camera": "دوربین", "durbin": "دوربین", "doorbin": "دوربین",
    "printer": "پرینتر", "scaner": "اسکنر", "scanner": "اسکنر",
    "battery": "باتری", "bateri": "باتری", "sharzh": "شارژ",
    "screen": "اسکرین", "safhe": "صفحه", "safheh": "صفحه",
    "keyboard": "کیبورد", "mouse": "ماوس", "maus": "ماوس",
    "speaker": "اسپیکر", "headphone": "هدفون", "mikrofon": "میکروفون",

    # --- Media / social ---
    "instagram": "اینستاگرام", "insta": "اینستا", "telegram": "تلگرام",
    "whatsapp": "واتساپ", "vatsap": "واتساپ", "twitter": "توییتر",
    "youtube": "یوتیوب", "facebook": "فیسبوک", "tiktok": "تیک‌تاک",
    "post": "پست", "story": "استوری", "storye": "استوری",
    "like": "لایک", "comment": "کامنت", "share": "شیر",
    "follow": "فالو", "follower": "فالوور", "unfollow": "آنفالو",
    "channel": "چنل", "kanal": "کانال", "group": "گروه", "goruh": "گروه",
    "chat": "چت", "voice": "ویس", "vois": "ویس", "voice message": "ویس",

    # --- Sports ---
    "varzesh": "ورزش", "footbal": "فوتبال", "football": "فوتبال",
    "futbal": "فوتبال", "gol": "گل", "toop": "توپ", "tup": "توپ",
    "tim": "تیم", "team": "تیم", "bazi": "بازی", "mosabeghe": "مسابقه",
    "gahreman": "قهرمان", "ghahreman": "قهرمان", "borde": "برده",
    "bakht": "باخت", "bord": "برد", "mosavi": "مساوی",
    "valibal": "والیبال", "basketbal": "بسکتبال", "tennis": "تنیس",
    "shena": "شنا", "koshti": "کشتی", "boxe": "بوکس", "box": "بوکس",
    "varzeshgah": "ورزشگاه", "stadium": "استادیوم",

    # --- Religion / culture ---
    "khoda": "خدا", "khodaa": "خدا", "allah": "الله",
    "namaz": "نماز", "rooze": "روزه", "ruze": "روزه",
    "ghoran": "قرآن", "quran": "قرآن", "masjed": "مسجد",
    "emam": "امام", "peyghambar": "پیغمبر", "payambar": "پیامبر",
    "eid": "عید", "eyd": "عید", "ramazan": "رمضان", "moharram": "محرم",
    "ashura": "عاشورا", "noruz": "نوروز", "nowruz": "نوروز", "norouz": "نوروز",
    "yalda": "یلدا", "chaharshanbe suri": "چهارشنبه‌سوری",
    "hafte sin": "هفت‌سین", "haftsin": "هفت‌سین",

    # --- Colors (extra) ---
    "sefid": "سفید", "siyah": "سیاه", "siah": "سیاه", "meshki": "مشکی",
    "ghermez": "قرمز", "zard": "زرد", "abi": "آبی", "abie": "آبی",
    "sabz": "سبز", "naranji": "نارنجی", "banafsh": "بنفش",
    "surati": "صورتی", "soorati": "صورتی", "ghahvei": "قهوه‌ای",
    "khakestari": "خاکستری", "talaei": "طلایی", "noghreii": "نقره‌ای",
    "abi kamrang": "آبی کمرنگ", "abi tire": "آبی تیره",

    # --- Common phrase chunks ---
    "che khabar": "چه خبر", "chekhabar": "چه‌خبر", "che khabari": "چه خبری",
    "khubi": "خوبی", "khoobi": "خوبی", "khubam": "خوبم", "khoobam": "خوبم",
    "bad nistam": "بد نیستم", "badnistam": "بدنیستم",
    "chetori": "چطوری", "chetor i": "چطوری", "halet chetore": "حالت چطوره",
    "hale shoma": "حال شما", "hale shoma chetore": "حال شما چطوره",
    "sobh bekheir": "صبح بخیر", "sobhetoon bekheir": "صبحتون بخیر",
    "shab bekheir": "شب بخیر", "shabetoon bekheir": "شبتون بخیر",
    "asretun bekheir": "عصرتون بخیر", "asreton bekheir": "عصرتون بخیر",
    "khosh amadid": "خوش آمدید", "khosh amadi": "خوش آمدی",
    "khoshgel shodi": "خوشگل شدی", "bahal budi": "باحال بودی",
    "dast shoma dard nakone": "دست شما درد نکنه",
    "ghorban dastet": "قربان دستت", "ghorboone dastet": "قربون دستت",
    "che ghashang": "چه قشنگ", "che ziba": "چه زیبا",
    "are": "آره", "aare": "آره", "areh": "آره", "bale": "بله", "baleh": "بله",
    "na": "نه", "nakheyr": "نخیر", "nah": "نه",
    "bashe": "باشه", "basheh": "باشه", "kheili khub": "خیلی خوب",
    "eyval": "ایول", "eyvallah": "ایوالله", "damet garm": "دمت گرم",
    "dametoon garm": "دم‌تون گرم", "dastetoon dard nakone": "دستتون درد نکنه",
    "agha": "آقا", "khanom": "خانم", "khanoom": "خانم", "khanoum": "خانم",
    "jenab": "جناب", "sarkar": "سرکار", "haj agha": "حاج‌آقا",
    "haj khanom": "حاج‌خانم",

    # --- Common verbs more conjugations ---
    "resid": "رسید", "residam": "رسیدم", "residi": "رسیدی", "residan": "رسیدن",
    "miresam": "می‌رسم", "miresi": "می‌رسی", "mirese": "می‌رسه",
    "beresam": "برسم", "beres": "برس", "beresid": "برسید",
    "mord": "مرد", "mordam": "مردم", "mordan": "مردن",
    "zende shod": "زنده شد", "zende shodam": "زنده شدم",
    "avord": "آورد", "avordam": "آوردم", "avordan": "آوردن",
    "miyaram": "می‌یارم", "miyari": "می‌یاری", "miyare": "می‌یاره",
    "biar": "بیار", "biyar": "بیار", "biarid": "بیارید",
    "bord": "برد", "bordam": "بردم", "bordan": "بردن",
    "mibaram": "می‌برم", "mibari": "می‌بری", "mibare": "می‌بره",
    "bebar": "ببر", "bebarid": "ببرید", "nabar": "نبر",
    "gozasht": "گذاشت", "gozashtam": "گذاشتم", "gozashtan": "گذاشتن",
    "mizaram": "می‌ذارم", "mizari": "می‌ذاری", "mizare": "می‌ذاره",
    "bezar": "بذار", "bezar id": "بذارید", "nazar": "نذار",
    "oftad": "افتاد", "oftadam": "افتادم", "oftadan": "افتادن",
    "mioftam": "می‌افتم", "bioft": "بیفت",
    "parid": "پرید", "paridan": "پریدن", "miparam": "می‌پرم",
    "david": "دوید", "davidan": "دویدن", "midavam": "می‌دوم", "bodo": "بدو",
    "khandid": "خندید", "khandidan": "خندیدن", "mikhandam": "می‌خندم",
    "bekhand": "بخند", "gerye kard": "گریه کرد", "migeryam": "می‌گریم",
    "tarsid": "ترسید", "tarsidan": "ترسیدن", "mitarsam": "می‌ترسم",
    "shenid": "شنید", "shenidam": "شنیدم", "shenidan": "شنیدن",
    "mishnavam": "می‌شنوم", "mishnavi": "می‌شنوی", "beshnav": "بشنو",
    "boosid": "بوسید", "boosidan": "بوسیدن", "mibusam": "می‌بوسم",
    "bebus": "ببوس", "baghal kard": "بغل کرد",

    # --- Education subjects / campus ---
    "daneshgah": "دانشگاه", "daneshjoo": "دانشجو", "ostad": "استاد",
    "moallem": "معلم", "dars": "درس", "kelas": "کلاس",
    "emtehan": "امتحان", "nomre": "نمره", "mashgh": "مشق",
    "tamrin": "تمرین", "pajuhesh": "پژوهش", "tahghigh": "تحقیق",
    "payanname": "پایان‌نامه", "tez": "تز", "maghale": "مقاله",
    "ketab": "کتاب", "daftar": "دفتر", "ghalam": "قلم", "medad": "مداد",
    "pakkon": "پاک‌کن", "khodkar": "خودکار", "marker": "ماژیک",
    "takhtesiah": "تخته‌سیاه", "board": "برد", "proyektor": "پروژکتور",
    "konkur": "کنکور", "konkoor": "کنکور", "diplom": "دیپلم",
    "lisans": "لیسانس", "foghlisans": "فوق‌لیسانس", "doctori": "دکتری",

    # --- Food more ---
    "kabab": "کباب", "joojeh": "جوجه", "juje": "جوجه",
    "gheyme": "قیمه", "gheimeh": "قیمه", "ghorme": "قرمه",
    "fesenjoon": "فسنجون", "fesenjan": "فسنجان",
    "zereshk": "زرشک", "zereshk polo": "زرشک‌پلو",
    "baghali": "باقالی", "baghali polo": "باقالی‌پلو",
    "lubia": "لوبیا", "adas": "عدس", "nokhod": "نخود",
    "mast": "ماست", "khiar": "خیار", "goje": "گوجه",
    "piaz": "پیاز", "sir": "سیر", "namak": "نمک", "felfel": "فلفل",
    "roghan": "روغن", "kare": "کره", "kareh": "کره",
    "moraba": "مربا", "asal": "عسل", "shekar": "شکر",
    "tokhme morgh": "تخم‌مرغ", "tokhm": "تخم", "tokhme": "تخمه",
    "paneer": "پنیر", "panir": "پنیر", "kalbas": "کالباس",
    "sos": "سس", "mayonnaise": "مایونز", "ketchup": "کچاپ",
    "chips": "چیپس", "pofak": "پفک", "shokolat": "شکلات",
    "shirini": "شیرینی", "cake": "کیک", "keik": "کیک",
    "bastani": "بستنی", "abnabat": "آبنبات", "noghl": "نقل",
    "gaz": "گز", "sohan": "سوهان", "zulbia": "زولبیا", "bamie": "بامیه",

    # --- Clothes more ---
    "lebas": "لباس", "pirahan": "پیراهن", "tshirt": "تیشرت",
    "tee shirt": "تی‌شرت", "shirt": "شرت", "shalvar": "شلوار",
    "jean": "جین", "jeans": "جین", "koton": "کتان",
    "kot": "کت", "palto": "پالتو", "kapshan": "کاپشن",
    "kafsh": "کفش", "sandali kafsh": "صندل", "boot": "بوت",
    "jorab": "جوراب", "kolah": "کلاه", "topi": "کلاه",
    "eynak": "عینک", "saats": "ساعت", "angoshtar": "انگشتر",
    "dastband": "دستبند", "gardanband": "گردنبند",
    "kif": "کیف", "kif dasti": "کیف دستی", "kooleh": "کوله",
    "chador": "چادر", "roosari": "روسری", "maghnae": "مقنعه",
    "manto": "مانتو", "shal": "شال",

    # --- Iran geography more ---
    "tehran": "تهران", "tehran": "تهران", "isfahan": "اصفهان",
    "esfahan": "اصفهان", "shiraz": "شیراز", "mashhad": "مشهد",
    "tabriz": "تبریز", "karaj": "کرج", "ahvaz": "اهواز",
    "qom": "قم", "ghom": "قم", "kerman": "کرمان",
    "yazd": "یزد", "rasht": "رشت", "sari": "ساری",
    "urmia": "ارومیه", "orumiye": "ارومیه", "hamadan": "همدان",
    "kermanshah": "کرمانشاه", "zanjan": "زنجان", "ardabil": "اردبیل",
    "bandarabbas": "بندرعباس", "bandar abbas": "بندرعباس",
    "bushehr": "بوشهر", "zahedan": "زاهدان", "sanandaj": "سنندج",
    "khorasan": "خراسان", "azarbaijan": "آذربایجان",
    "fars": "فارس", "gilan": "گیلان", "mazandaran": "مازندران",
    "kish": "کیش", "qeshm": "قشم", "gheshm": "قشم",
    "caspian": "خزر", "khalij fars": "خلیج فارس",
    "damavand": "دماوند", "alborz": "البرز", "zagros": "زاگرس",

    # --- Countries more ---
    "iran": "ایران", "iraan": "ایران", "tehran": "تهران",
    "amrika": "آمریکا", "amrica": "آمریکا", "usa": "آمریکا",
    "kanada": "کانادا", "canada": "کانادا",
    "alman": "آلمان", "faranse": "فرانسه", "engelis": "انگلیس",
    "engelestan": "انگلستان", "britain": "بریتانیا",
    "italia": "ایتالیا", "espania": "اسپانیا", "portugal": "پرتغال",
    "torkiye": "ترکیه", "turkey": "ترکیه", "yunan": "یونان",
    "arabestan": "عربستان", "emarat": "امارات", "dubai": "دبی",
    "ghatar": "قطر", "qatar": "قطر", "kuwait": "کویت",
    "arag": "عراق", "iraq": "عراق", "afghanestan": "افغانستان",
    "pakistan": "پاکستان", "hend": "هند", "chin": "چین",
    "japon": "ژاپن", "kore": "کره", "kore jonoobi": "کره جنوبی",
    "rusiye": "روسیه", "ukrain": "اوکراین", "australia": "استرالیا",
    "brazil": "برزیل", "argantin": "آرژانتین", "mesr": "مصر",
    "egypt": "مصر", "afrika": "آفریقا", "orupa": "اروپا",
    "asiya": "آسیا", "america": "آمریکا",

    # --- Abstract / academic ---
    "elmi": "علمی", "elam": "اعلام", "elmiyat": "علمیت",
    "danesh": "دانش", "elm": "علم", "fan": "فن", "fanavari": "فناوری",
    "technology": "تکنولوژی", "teknoloji": "تکنولوژی",
    "honar": "هنر", "adabiyat": "ادبیات", "sher": "شعر", "shaer": "شاعر",
    "roman": "رمان", "dastan": "داستان", "film": "فیلم",
    "mosighi": "موسیقی", "ahang": "آهنگ", "sorud": "سرود",
    "naghashi": "نقاشی", "akkasi": "عکاسی", "sinama": "سینما",
    "teatr": "تئاتر", "theater": "تئاتر", "namayesh": "نمایش",
    "khabar": "خبر", "matn": "متن", "neveshte": "نوشته",
    "kalame": "کلمه", "kalameh": "کلمه", "jomle": "جمله", "jomleh": "جمله",
    "zabane farsi": "زبان فارسی", "farsi": "فارسی", "parsi": "پارسی",
    "englisi": "انگلیسی", "english": "انگلیسی", "arabi": "عربی",

    # --- Common mis-conversions people report ---
    "mikonam": "می‌کنم", "mikoni": "می‌کنی", "mikone": "می‌کنه",
    "mikonim": "می‌کنیم", "mikonin": "می‌کنین", "mikonan": "می‌کنن",
    "nemikonam": "نمی‌کنم", "nemikoni": "نمی‌کنی", "nemikone": "نمی‌کنه",
    "mikham": "می‌خوام", "mikhad": "می‌خواد", "mikhan": "می‌خوان",
    "midunam": "میدونم", "miduni": "میدونی", "midune": "میدونه",
    "mitunam": "می‌تونم", "mituni": "می‌تونی", "mitune": "می‌تونه",
    "migoft": "می‌گفت", "migoftam": "می‌گفتم", "migam": "میگم",
    "miram": "میرم", "miam": "میام", "miad": "میاد",
    "mibinam": "می‌بینم", "mishnavam": "می‌شنوم",
    "mikhoram": "می‌خورم", "mikhabam": "می‌خوابم",
    "mizanam": "می‌زنم", "mizani": "می‌زنی", "mizane": "می‌زنه",
    "bezan": "بزن", "bezanam": "بزنم", "nazan": "نزن",
    "zadan": "زدن", "zad": "زد", "zadam": "زدم", "zadi": "زدی",
    "khandan": "خواندن", "neveshtan": "نوشتن", "didan": "دیدن",
    "goftan": "گفتن", "raftan": "رفتن", "amadan": "آمدن",
    "kardan": "کردن", "shodan": "شدن", "budan": "بودن",
    "dashtan": "داشتن", "bordan": "بردن", "avordan": "آوردن",
    "gereftan": "گرفتن", "dadan": "دادن", "gozashtan": "گذاشتن",
    "oftadan": "افتادن", "residan": "رسیدن", "khabidan": "خوابیدن",
    "khordan": "خوردن", "nushidan": "نوشیدن", "pushidan": "پوشیدن",
    "shostan": "شستن", "mishoram": "می‌شورم", "beshur": "بشور",
    "sakhte": "ساخته", "sakhtan": "ساختن", "misazam": "می‌سازم",
    "besaz": "بساز", "kharab": "خراب", "kharab shod": "خراب شد",
    "tamir": "تعمیر", "tamir kon": "تعمیر کن",
    "baz": "باز", "baste": "بسته", "basteh": "بسته",
    "baz kon": "باز کن", "bebass": "ببند", "beband": "ببند",
    "roshan kon": "روشن کن", "khamush": "خاموش", "khamoosh": "خاموش",
    "khamush kon": "خاموش کن", "khamoosh kon": "خاموش کن",

    # --- Interjections / fillers ---
    "vaye": "وای", "vay": "وای", "ay": "آی", "ahi": "آخی",
    "of": "اوف", "oh": "اوه", "aha": "آها", "aha": "آها",
    "hmm": "هم", "ee": "ای", "eh": "اه",
    "baabaa": "بابا", "vay khoda": "وای خدا", "ya allah": "یاالله",
    "enshalla": "ان‌شاءالله", "enshallah": "ان‌شاءالله",
    "mashalla": "ماشاءالله", "mashallah": "ماشاءالله",
    "alhamdulillah": "الحمدلله", "yaali": "یاعلی",
    "besmellah": "بسم‌الله", "bismillah": "بسم‌الله",

    # --- Modal particles / speech markers ---
    "dige": "دیگه", "digeh": "دیگه", "ke": "که", "ha": "ها",
    "haa": "ها", "na": "نه", "are": "آره", "khob": "خب", "khoob": "خوب",
    "khob": "خب", "xob": "خب", "kheili khob": "خیلی خب",
    "masalan": "مثلاً", "yani": "یعنی", "yani ke": "یعنی که",
    "hatman": "حتماً", "aslan": "اصلاً", "belakhare": "بالاخره",
    "faghat": "فقط", "tanha": "تنها", "tanhaha": "تنها",
    "hamishe": "همیشه", "hichvaght": "هیچ‌وقت", "gahgahi": "گهگاهی",
    "alan": "الان", "hala": "حالا", "baad": "بعد", "ghabli": "قبلی",
    "badi": "بعدی", "baadi": "بعدی", "avali": "اولی",

    # --- Possession colloquial ---
    "male man": "مال من", "maleman": "مال‌من", "maleto": "مال تو",
    "malesh": "مالش", "malemoon": "مال‌مون", "maletoon": "مال‌تون",
    "maleshoon": "مال‌شون", "male kieh": "مال کیه", "male kie": "مال کیه",

    # --- Days / months already partly covered — ensure variants ---
    "shanbe": "شنبه", "shanbeh": "شنبه", "yekshanbe": "یکشنبه",
    "doshanbe": "دوشنبه", "seshanbe": "سه‌شنبه",
    "chaharshanbe": "چهارشنبه", "panjshanbe": "پنجشنبه",
    "jome": "جمعه", "jomeh": "جمعه",
    "farvardin": "فروردین", "ordibehesht": "اردیبهشت",
    "khordad": "خرداد", "tir": "تیر", "mordad": "مرداد",
    "shahrivar": "شهریور", "mehr": "مهر", "aban": "آبان",
    "azar": "آذر", "dey": "دی", "bahman": "بهمن", "esfand": "اسفند",

    # --- Misc high-frequency ---
    "esmesh": "اسمش", "esmam": "اسمم", "esmet": "اسمت",
    "esme": "اسم", "esm": "اسم", "nam": "نام", "naam": "نام",
    "sen": "سن", "senet": "سنت", "chand salete": "چند سالته",
    "kojayi": "کجایی", "kojayi": "کجایی", "ahles koja": "اهل کجا",
    "zendegi mikonam": "زندگی می‌کنم", "saken": "ساکن",
    "shoghl et chie": "شغلت چیه", "kar mikoni": "کار می‌کنی",
    "mojarad": "مجرد", "mojarrad": "مجرد", "motahel": "متأهل",
    "ezdevaj": "ازدواج", "talagh": "طلاق",
    "bache": "بچه", "bacheha": "بچه‌ها", "bachehaa": "بچه‌ها",
    "pesar": "پسر", "dokhtar": "دختر", "mard": "مرد", "zan": "زن",
}


def load_f2p_dict() -> dict[str, str]:
    """Load dictionary shipped with the installed finglish package."""
    try:
        import finglish
        base = Path(finglish.__file__).parent
        path = base / "f2p-dict.txt"
    except Exception:
        path = ROOT / "data" / "community" / "f2p-dict.txt"
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        k, v = parts[0].strip().lower(), parts[1].strip()
        if k and v:
            out[k] = v
    return out


def load_community_patches() -> dict[str, str]:
    sys.path.insert(0, str(ROOT))
    try:
        from community_patches import COMMUNITY_PATCHES
        return {str(k).lower(): str(v) for k, v in COMMUNITY_PATCHES.items()}
    except Exception:
        return {}


def load_builtin_from_converter() -> dict[str, str]:
    """Read BUILTIN_PATCHES without importing finglish (noisy)."""
    text = (ROOT / "converter.py").read_text(encoding="utf-8")
    # crude but safe: only used for meta counts; not required for output
    return {}


def normalize_key(k: str) -> str:
    k = k.strip().lower()
    k = re.sub(r"\s+", " ", k)
    return k


def build() -> dict[str, str]:
    merged: dict[str, str] = {}

    f2p = load_f2p_dict()
    for k, v in f2p.items():
        merged[normalize_key(k)] = v

    patches = load_community_patches()
    for k, v in patches.items():
        merged[normalize_key(k)] = v

    for k, v in EXTRA_ENTRIES.items():
        merged[normalize_key(k)] = v

    # Drop multi-word keys that the word-level converter cannot use unless
    # they contain only letters/spaces (kept for phrase patching later).
    # Keep single-token keys primarily; multi-word still stored for phrase map.
    return merged


def write_dict(d: dict[str, str]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # TAB-separated so multi-word Finglish keys stay intact:
    #   finglish key<TAB>persian value
    lines = [f"{k}\t{v}" for k, v in sorted(d.items(), key=lambda kv: kv[0])]
    header = (
        "# Community Finglish → Persian dictionary\n"
        "# Format: finglish<TAB>persian  (one entry per line)\n"
        "# Rebuild: python scripts/build_community_dict.py\n"
    )
    OUT.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    single = sum(1 for k in d if " " not in k)
    multi = len(d) - single
    meta = {
        "total_entries": len(d),
        "single_word": single,
        "multi_word": multi,
        "format": "tab-separated (finglish\\tpersian)",
        "sources": [
            "elektito/finglish f2p-dict.txt (MIT)",
            "community_patches.py",
            "scripts/build_community_dict.py EXTRA_ENTRIES",
        ],
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} ({len(d)} entries; {single} single-word, {multi} multi-word)")


if __name__ == "__main__":
    write_dict(build())
