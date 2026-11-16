# راهنمای فارسی Workshop Vision AI

این یک نمونه‌کار Computer Vision برای GitHub است، نه نرم‌افزار نظارت بر عملکرد شخصی کارکنان.

## راه‌اندازی در Windows 11 و VS Code

داخل پوشه پروژه، ترمینال PowerShell را باز کن:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python make_demo.py
python monitor.py --detector demo
```

برای خروج از نمایش ویدئو کلید Q را بزن. برای داشبورد:

```powershell
python -m streamlit run dashboard.py
```

## اجرای دوربین واقعی

```powershell
python monitor.py --source 0 --detector yolo
```

مدل YOLO11n در اولین اجرا به اینترنت نیاز دارد. اگر وب‌کم دیگری استفاده می‌کنی، عدد 0 را به 1 تغییر بده. برای ویدئوی خودت:

```powershell
python monitor.py --source "C:\Videos\sample.mp4" --detector yolo
```

## معنی خروجی

- **visible_people**: تعداد افرادی که در همان لحظه در تصویر دیده شده‌اند؛ نه تعداد کل کارکنان شرکت.
- **moving_people**: تعداد افرادی که مکانشان در تصویر تغییر کرده است.
- **stationary_people**: تعداد افرادی که جابه‌جایی کمی داشته‌اند. این به معنی بیکار بودن نیست.
- **uncertain_people**: داده کافی برای بررسی حرکت وجود ندارد.
- **assembly / packaging / aisle**: تعداد افراد دیده‌شده در هر منطقه.
- **crowd_alert**: تعداد افراد دیده‌شده از حد تعیین‌شده بیشتر است.

مناطق موجود در `config/zones.json` برای دموی پروژه هستند؛ برای دوربین دیگر باید آن‌ها را تنظیم کنی. تصاویر یا ویدئوهای واقعی را داخل GitHub منتشر نکن. استفاده از دوربین در محیط کار نیازمند مجوزها و بررسی حقوقی مربوطه است.
