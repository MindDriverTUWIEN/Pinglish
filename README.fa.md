<div align="center">

<img src="assets/icon.png" alt="آیکون Pinglish" width="96">

# Pinglish

[English](README.md) | **فارسی**

![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078D6)
![Python](https://img.shields.io/badge/python-3.11%2B-3776AB)
![UI](https://img.shields.io/badge/UI-Flet%200.85-02569B)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

<div dir="rtl">

**فارسی را با حروف لاتین تایپ کنید یا فقط آن را بگویید، و متن درست فارسی بگیرید.**

یک برنامهٔ دسکتاپ ویندوز که پینگلیش / فینگلیش (`salam chetori?`) را هنگام تایپ
به فارسی (`سلام چطوری؟`) تبدیل می‌کند، اجازه می‌دهد هر کلمه را از فهرست
املاهای جایگزین اصلاح کنید، و گفتار فارسی را به‌صورت زنده به متن تبدیل می‌کند.

---

## فهرست

- [امکانات](#features)
- [پیش‌نیازها](#requirements)
- [نصب](#installation)
- [استفاده](#usage)
- [کلید گفتار](#speech-key)
- [استفاده از کلید Google Cloud خودتان](#own-cloud-key)
- [تنظیمات و فایل‌های داده](#data-files)
- [نحوهٔ کار](#how-it-works)
- [ساختار پروژه](#project-structure)
- [بهبود واژه‌نامه](#dictionary)
- [ساخت نسخهٔ مستقل](#building)
- [رفع مشکلات](#troubleshooting)
- [حریم خصوصی](#privacy)
- [مشارکت](#contributing)
- [قدردانی](#credits)
- [مجوز](#license)

<a id="features"></a>
## امکانات

- **تبدیل زنده.** بخش Persian Output با هر کلید به‌روز می‌شود.
- **املاهای پیشنهادی.** روی هر کلمه در Persian Output کلیک کنید تا املاهای
  دیگر را ببینید و درستش را انتخاب کنید. انتخاب شما از آن به بعد به خاطر سپرده می‌شود.
- **نشانه‌گذاری فارسی.** نشانه‌های `?` `,` `;` در متن فارسی به `؟` `،` `؛`
  تبدیل می‌شوند، ولی عددهایی مثل `1,000` ویرگول خود را نگه می‌دارند.
- **گفتار به متن (fa-IR).** دکمهٔ میکروفون را بزنید و فارسی صحبت کنید. کلمه‌ها
  همزمان با صحبت‌تان ظاهر می‌شوند و هر عبارت با نتیجهٔ نهایی تشخیص جایگزین می‌شود.
  - گفتهٔ شما به‌صورت پینگلیش در Pinglish Input هم نوشته می‌شود
    (`این هدفونی که گرفتی خیلی گرونه` → `in hedfooni ke gerefti kheili gerooneh`)
    تا بتوانید بعد از آن ادامهٔ متن را تایپ کنید.
  - نشانه‌گذاری با صدا: برای `؟` بگویید **علامت سوال**، برای `!` بگویید
    **علامت تعجب**، برای `.` بگویید **نقطه** و برای فاصله بگویید **فاصله**.
- **ابزارهای کلیپ‌بورد.** متن کلیپ‌بورد را تبدیل کنید، متن فارسی (یا هر دو متن)
  را کپی کنید، یا نتیجه را مستقیم در برنامه‌ای که با آن کار می‌کردید بچسبانید.
- **اجرا در پس‌زمینه.** بستن پنجره آن را به سینی سیستم (system tray) می‌برد.
  یک کلید میان‌بر سراسری آن را از هر برنامه‌ای برمی‌گرداند.
- **سازگار با نوار وظیفه.** با نام *Pinglish* و آیکون خودش سنجاق (pin) می‌شود.

<a id="requirements"></a>
## پیش‌نیازها

- ویندوز ۱۰ یا ۱۱ (برنامه از صدای WASAPI و رابط‌های پنجرهٔ Win32 استفاده می‌کند)
- پایتون 3.11 یا جدیدتر
- فقط برای گفتار: میکروفون و اتصال اینترنت

<a id="installation"></a>
## نصب

```powershell
git clone https://github.com/MindDriverTUWIEN/Pinglish.git
cd Pinglish

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

نسخهٔ وابستگی‌ها ثابت شده است. رابط کاربری برای Flet 0.85 نوشته شده و با
Flet 1.x سازگار نیست.

<a id="usage"></a>
## استفاده

برنامه را با یکی از این‌ها اجرا کنید:

| اجراکننده | چه زمانی |
|---|---|
| `launch-hidden.vbs` | استفادهٔ روزمره، بدون پنجرهٔ کنسول |
| `create-desktop-shortcut.ps1` | یک بار اجرا کنید تا میان‌بری برای اجراکنندهٔ بالا روی دسکتاپ ساخته شود |
| `run.bat` | عیب‌یابی؛ خطاها را در کنسول نشان می‌دهد |
| `python main.py` | از داخل محیط مجازی فعال‌شده |

پنجره از بالا به پایین سه بخش دارد:

1. **Pinglish Input**: فارسی با حروف لاتین را تایپ یا جای‌گذاری کنید.
2. **Suggested Alternatives**: تا روی کلمه‌ای در Persian Output کلیک نکنید
   خالی است. املای درست را از فهرست کشویی انتخاب کنید.
3. **Persian Output**: متن تبدیل‌شده، با دکمهٔ میکروفون در عنوان آن.

کلید **Live convert** هر بار که برنامه شروع می‌شود روشن است. اگر خاموشش کنید،
تبدیل فقط با زدن **Convert** انجام می‌شود.

### کلیدهای میان‌بر

| میان‌بر | کار |
|---|---|
| `Ctrl` + `D` (`Strg` + `D`) | نمایش پنجره از هر برنامه‌ای |
| `Esc` | توقف میکروفون |
| `Ctrl` + `Shift` + `Q` | خروج کامل (دکمهٔ X فقط پنجره را به سینی سیستم می‌برد) |

### صحبت کردن

دکمهٔ میکروفون را بزنید و صبر کنید تا نوار وضعیت **Listening on …** را نشان
دهد. هدست بلوتوث حدود یک ثانیه وقت لازم دارد تا به حالت تماس برود. طبیعی صحبت
کنید: یک مکث کوتاه عبارت را تمام می‌کند و میکروفون روشن می‌ماند تا دوباره آن را
بزنید یا `Esc` را فشار دهید. آخرین کلمه‌ها پیش از توقف هم حفظ می‌شوند.

<a id="speech-key"></a>
## کلید گفتار

تشخیص گفتار صدا را به `www.google.com/speech-api/v2/recognize` (`fa-IR`)
می‌فرستد؛ همان سرویس مستندنشده‌ای که Chrome برای دیکتهٔ خودش به کار می‌برد.
این سرویس، Speech-to-Text پولی Google Cloud نیست.

**نیازی به تنظیم نیست: میکروفون بلافاصله پس از نصب کار می‌کند.** این سرویس فقط
یک پارامتر کلید می‌خواهد و برنامه کلید عمومی Chromium را در خود دارد
(`_DEFAULT_SPEECH_KEY` در `speech_fa.py`). این همان کلید پیش‌فرضی است که
کتابخانهٔ متن‌باز [SpeechRecognition](https://github.com/Uberi/speech_recognition)
برای `recognize_google()` استفاده می‌کند. به حساب Google شما یا هیچ‌کس دیگری
وصل نیست، پس هزینه‌ای ایجاد نمی‌شود. نه حساب Google لازم دارید و نه کلید شخصی.

برای استفاده از کلید دیگری برای این سرویس (جایگزین کلید داخلی می‌شود):

```powershell
# Option 1: a local file that git ignores
Set-Content data\speech_key.txt "another-key"

# Option 2: an environment variable
setx GOOGLE_SPEECH_KEY "another-key"
```

> [!NOTE]
> این سرویس غیررسمی است. Google هیچ محدودیت یا تضمینی برای آن منتشر نکرده و
> ممکن است هر زمان آن را محدود یا خاموش کند. در آن صورت میکروفون کار نمی‌کند،
> ولی تبدیل متن آسیبی نمی‌بیند و می‌توانید به
> [کلید Google Cloud خودتان](#own-cloud-key) بروید.

تبدیل متن کاملاً آفلاین کار می‌کند.

<a id="own-cloud-key"></a>
## استفاده از کلید Google Cloud خودتان

اگر سرویس رایگان از کار بیفتد، یا سرویس رسمی را ترجیح دهید، برنامه می‌تواند از
[Speech-to-Text API](https://cloud.google.com/speech-to-text) گوگل کلاد با کلید
خودتان استفاده کند. وقتی این کلید تنظیم شده باشد، همیشه به‌جای سرویس رایگان به
کار می‌رود.

1. در [کنسول Google Cloud](https://console.cloud.google.com/) یک پروژه بسازید یا
   انتخاب کنید و **Cloud Speech-to-Text API** را فعال کنید. حتی برای سهمیهٔ
   رایگان هم یک حساب پرداخت (billing) لازم است.
2. در **APIs & Services → Credentials** گزینهٔ **Create credentials → API key**
   را بزنید. کلید را به Cloud Speech-to-Text API محدود کنید.
3. کلید را به یکی از این دو روش اضافه کنید و برنامه را دوباره اجرا کنید:

   ```powershell
   # Option 1: a local file that git ignores
   Set-Content data\google_cloud_key.txt "your-cloud-key"

   # Option 2: an environment variable
   setx GOOGLE_CLOUD_SPEECH_KEY "your-cloud-key"
   ```

برای بازگشت به سرویس رایگان، فایل `data\google_cloud_key.txt` یا آن متغیر را
حذف کنید. اگر Google کلید شما را نپذیرد، نوار وضعیت دلیلش را نشان می‌دهد؛ مثلاً
*API key not valid*.

> [!WARNING]
> **هزینه‌ها.** Google Cloud سهمیهٔ رایگان ماهانه‌ای از دقیقه‌های Speech-to-Text
> دارد و بعد از آن برای هر دقیقهٔ صدا هزینه می‌گیرد؛
> [قیمت‌های Google](https://cloud.google.com/speech-to-text/pricing) را ببینید.
> هنگام صحبت، برنامه برای هر به‌روزرسانی زنده عبارتِ در حال رشد را دوباره
> می‌فرستد، پس صدای محاسبه‌شده چند برابرِ زمانی است که واقعاً صحبت می‌کنید.
> در پروژه‌تان یک [هشدار بودجه](https://cloud.google.com/billing/docs/how-to/budgets)
> تنظیم کنید و هرگز کلیدتان را منتشر نکنید.

<a id="data-files"></a>
## تنظیمات و فایل‌های داده

همه‌چیز در `data/` به‌جز واژه‌نامهٔ همراه برنامه روی کامپیوتر شما ساخته می‌شود
و git آن را نادیده می‌گیرد.

| فایل | محتوا |
|---|---|
| `data/community_dict.txt` | واژه‌نامهٔ اصلی پینگلیش ← فارسی (همراه برنامه) |
| `data/user_corrections.txt` | املاهایی که در Suggested Alternatives انتخاب کرده‌اید |
| `data/settings.json` | کلید میان‌بر، کپی خودکار و اندازهٔ پنجره |
| `data/speech_key.txt` | اختیاری: جایگزین کلید داخلی سرویس رایگان |
| `data/google_cloud_key.txt` | اختیاری: کلید Google Cloud خودتان |
| `data/finglish_launch.log` | گزارش راه‌اندازی و میکروفون برای عیب‌یابی |

<a id="how-it-works"></a>
## نحوهٔ کار

**تبدیل متن** در سه لایه انجام می‌شود و لایه‌های بعدی اولویت دارند:

1. موتور قاعده‌ها و بسامد واژه‌های [finglish](https://github.com/elektito/finglish)
2. واژه‌نامهٔ جمعی در `data/community_dict.txt` (حدود ۲٬۷۰۰ مدخل)
3. اصلاحیه‌های داخلی و اصلاح‌های خود شما

**گفتار** با `sounddevice` در حالت اشتراکی WASAPI ضبط می‌شود و هدست اولویت
دارد. یک دروازهٔ تشخیص صدا آن را به عبارت‌ها تقسیم می‌کند؛ نتیجه‌های موقت و
نهایی از سرویس تشخیص می‌آیند و همان لحظه روی حلقهٔ رویداد Flet نمایش داده
می‌شوند. فارسیِ تشخیص‌داده‌شده با `to_finglish()` در `converter.py` دوباره به
پینگلیش برگردانده می‌شود؛ این تابع واژه‌نامه‌ها را برعکس به کار می‌برد و بررسی
می‌کند که هر املا دوباره به همان کلمه تبدیل شود.

<a id="project-structure"></a>
## ساختار پروژه

```text
Pinglish/
├── main.py                    # Flet UI, tray icon, hotkeys, mic wiring
├── converter.py               # Pinglish ⇄ Persian conversion and punctuation
├── speech_fa.py               # Microphone capture and Persian speech recognition
├── community_patches.py       # Hand-curated spellings merged at runtime
├── data/
│   ├── community_dict.txt     # Shipped dictionary
│   └── community_dict_meta.json
├── assets/                    # Icons and the Vazirmatn font
├── scripts/
│   └── build_community_dict.py
├── launch-hidden.vbs          # Console-free launcher
├── create-desktop-shortcut.ps1
├── run.bat / run.ps1          # Launchers with a console, for debugging
├── build_windows.ps1          # Standalone build with flet build
└── requirements.txt
```

<a id="dictionary"></a>
## بهبود واژه‌نامه

برای اصلاح یک املا برای خودتان، روی کلمه در Persian Output کلیک کنید و املای
درست را انتخاب کنید. برای بهبود آن برای همه:

- یک خط `finglish<TAB>persian` به `data/community_dict.txt` اضافه کنید، یا
- مدخل‌ها را به `community_patches.py` یا `EXTRA_ENTRIES` در
  `scripts/build_community_dict.py` اضافه کنید و دوباره بسازید:

```powershell
python scripts/build_community_dict.py
```

<a id="building"></a>
## ساخت نسخهٔ مستقل

```powershell
.\.venv\Scripts\Activate.ps1
.\build_windows.ps1
```

خروجی در `build/windows/` بدون نصب پایتون اجرا می‌شود.

<a id="troubleshooting"></a>
## رفع مشکلات

| مشکل | راه‌حل |
|---|---|
| تایپ کاری نمی‌کند | مطمئن شوید **Live convert** روشن است، یا **Convert** را بزنید. |
| اولین کلمه‌ای که می‌گویید جا می‌افتد | پیش از صحبت صبر کنید تا **Listening on …** ظاهر شود. |
| «… sends no sound» | هدست را از جعبه‌اش دربیاورید یا دوباره وصلش کنید. |
| «Google's free speech service refused the request» | اتصال اینترنت را بررسی کنید، یا از [کلید Google Cloud خودتان](#own-cloud-key) استفاده کنید. |
| «Your Google Cloud key was refused: …» | کلید، فعال بودن Speech-to-Text API و تنظیم حساب پرداخت را بررسی کنید. |
| در شروع چیزی نمایش داده نمی‌شود | `run.bat` را اجرا کنید تا خطاها را ببینید، و `data/finglish_launch.log` را بخوانید. |
| سنجاق قدیمی «Flet description» نشان می‌دهد | آن را از نوار وظیفه بردارید، برنامه را اجرا کنید و دوباره سنجاقش کنید. |

<a id="privacy"></a>
## حریم خصوصی

- تبدیل متن کاملاً روی کامپیوتر شما انجام می‌شود.
- وقتی از میکروفون استفاده می‌کنید، صدای شما برای تشخیص به سرویس گفتار Google
  فرستاده می‌شود. وقتی میکروفون خاموش است چیزی فرستاده نمی‌شود.
- اصلاح‌ها و تنظیمات در `data/` روی کامپیوتر شما می‌مانند.

<a id="contributing"></a>
## مشارکت

گزارش مشکل (issue) و pull request خوش‌آمدند؛ به‌ویژه اصلاح‌های واژه‌نامه. لطفاً
بنویسید چه پینگلیشی تایپ کردید، چه نتیجه‌ای گرفتید و چه انتظاری داشتید.

<a id="credits"></a>
## قدردانی

- موتور تبدیل و فهرست پایهٔ واژه‌ها:
  [elektito/finglish](https://github.com/elektito/finglish) (MIT)
- رابط کاربری: [Flet](https://flet.dev/)
- قلم: [Vazirmatn](https://github.com/rastikerdar/vazirmatn)
  (SIL Open Font License، فایل `assets/fonts/OFL.txt` را ببینید)
- صدا: [python-sounddevice](https://github.com/spatialaudio/python-sounddevice)
- سینی سیستم و ابزارهای کمکی: pystray، Pillow، pyperclip، keyboard، pyautogui

<a id="license"></a>
## مجوز

منتشرشده تحت [مجوز MIT](LICENSE).

</div>
