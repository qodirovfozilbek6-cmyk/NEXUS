NEXUS — ishga tushirish (Windows)

1. Python 3.11 yoki 3.12 o‘rnatilgan bo‘lsin.
2. .env.example faylidan nusxa olib, nusxasini .env deb nomla.
3. .env faylida BOT_TOKEN va NEXUS_OWNER_ID qiymatlarini to‘ldir.
   Tokenni hech kimga yuborma va GitHub'ga yuklama.
5. NEXUS papkasida terminal/CMD ochib quyidagilarni bajar:

   py -3.11 -m venv .venv
   .venv\Scripts\python -m pip install --upgrade pip
   .venv\Scripts\pip install -r requirements.txt
   .venv\Scripts\uvicorn nexus.main:app --host 0.0.0.0 --port 8000

6. Tekshirish:
   http://127.0.0.1:8000/health
   Mini App: http://127.0.0.1:8000/app/

ESLATMA:
- Telegram Mini App autentifikatsiyasi uchun HTTPS domen kerak. Bot ishga tushganda
  .env dagi WEBAPP_URL asosida chat menyusi va /start tugmasi sozlanadi.
- Lokal HTTP manzili oddiy brauzerda dizaynni tekshirishga yaraydi,
  lekin autentifikatsiyalangan API funksiyalari Telegram initData talab qiladi.
- SQLite bazasi birinchi ishga tushishda avtomatik yaratiladi.
- ZIP ichiga shaxsiy .env, tokenlar va lokal ma’lumotlar bazasi kiritilmagan.
