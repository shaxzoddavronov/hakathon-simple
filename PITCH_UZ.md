# QueryMind AI — Startup Pitch (O'zbekiston)

> **Bir jumlada:** Ma'lumotlaringizni mamlakatdan tashqariga chiqarmasdan, oddiy o'zbek tilida savol berib, ma'lumotlar bazangizdan tahliliy javob va grafik oling. To'liq o'z serveringizda ishlaydi — hech qanday tashqi sun'iy intellekt xizmatiga ulanmaydi.

---

## 1. Muammo

O'zbekistonda korxonalar — banklar, savdo tarmoqlari, telekom, logistika va davlat tashkilotlari — ulkan hajmdagi ma'lumotni yig'moqda. Ammo bu ma'lumotdan **qaror qabul qilish uchun foydalanish** hali ham qiyin:

- **Har bir savolga analitik kerak.** "Bu oy qaysi filial eng ko'p sotdi?" degan oddiy savolga javob olish uchun rahbar IT yoki analitik bo'limga murojaat qiladi va kunlab kutadi.
- **SQL biladigan kadr tanqis.** Ma'lumotlar bazasidan to'g'ridan-to'g'ri so'rov yozadigan mutaxassislar kam va qimmat.
- **Ma'lumot maxfiyligi — qizil chiziq.** Bank, soliq, sog'liqni saqlash va davlat ma'lumotlarini ChatGPT yoki boshqa xorijiy AI xizmatlariga yuborish **qonunan va xavfsizlik nuqtai nazaridan mumkin emas**. "Ma'lumotlarni lokalizatsiya qilish" talablari buni taqiqlaydi.

Natijada: ma'lumot bor, lekin undan tezkor va xavfsiz foydalanish yo'q.

---

## 2. Yechim — QueryMind AI

QueryMind AI — bu **o'z infratuzilmangizda ishlaydigan** tabiiy til orqali ma'lumot tahlili platformasi:

1. Foydalanuvchi o'z ma'lumotlar bazasini ulaydi (Postgres, Oracle, ClickHouse, MongoDB, Elasticsearch, SQLite).
2. Tizim bazaning tuzilishini avtomatik o'rganadi.
3. Foydalanuvchi oddiy tilda savol yozadi: *"Oxirgi 3 oyda viloyatlar kesimida sotuvlar qanday?"*
4. AI agent **faqat o'qish uchun** (read-only) so'rov tuzadi, ishga tushiradi va **yozma javob + grafik** qaytaradi.

Hammasi brauzerda, chiroyli interfeysda. Tushuntirish ostida tizim yaratgan SQL kodi ham ko'rinadi — to'liq shaffoflik.

---

## 3. Nima uchun aynan bizning yechim? (Asosiy ustunlik)

🔒 **Ma'lumot serverdan chiqmaydi.** AI modeli (Qwen) sizning o'z serveringizda, lokal `vLLM` orqali ishlaydi. **Hech qanday tashqi API — OpenAI ham, boshqa xorijiy bulut ham yo'q.** Bu O'zbekistondagi ma'lumotlarni lokalizatsiya qilish talablariga to'liq mos keladi.

🛡️ **Uch qatlamli xavfsizlik (read-only).** Tizim hech qachon ma'lumotni o'zgartira olmaydi — so'rov uch bosqichda tekshiriladi (ruxsat, sintaktik tahlil, ish vaqtidagi cheklov). Bu banklar va davlat tashkilotlari uchun muhim.

🇺🇿 **O'zbek tiliga moslashuv.** Mahalliy til va kontekstda savol berish imkoniyati — xorijiy mahsulotlar buni qoplay olmaydi.

⚙️ **Ko'p bazali.** Bitta platforma 6 xil ma'lumotlar bazasi bilan ishlaydi — kompaniyalar tizimlarini almashtirishi shart emas.

---

## 4. Bozor — nega aynan hozir?

- **"Raqamli O'zbekiston — 2030"** strategiyasi davlat va biznesni raqamlashtirishni majburiy qilmoqda.
- Bank sektori, fintech (Click, Payme ekotizimi), e-commerce (marketpleyslar) va telekom tez o'smoqda — barchasida ma'lumot ko'p, analitik kam.
- Data-localization qonunchiligi tufayli **xorijiy bulutli AI yechimlari kira olmaydi** — bu bizning bozorimiz uchun himoyalangan o'rinni yaratadi.
- AI modellarining mahalliy serverda ishlay oladigan darajada arzonlashuvi yechimni endi texnik jihatdan mumkin qildi.

**Maqsadli mijozlar:** banklar va moliya tashkilotlari, davlat idoralari, yirik savdo/marketpleys tarmoqlari, telekom operatorlari, logistika va ishlab chiqarish korxonalari.

---

## 5. Biznes modeli

- **B2B SaaS / On-premise litsenziya** — korxonaning o'z serveriga o'rnatiladi, yillik obuna.
- **Tarif darajalari:** foydalanuvchilar soni va ulangan ma'lumotlar bazalari soniga qarab.
- **Joriy etish va integratsiya xizmatlari** — yirik mijozlar uchun qo'shimcha daromad.
- **Davlat sektori** — alohida xavfsiz (air-gapped) versiya.

---

## 6. Raqobat ustunligi

| | Xorijiy bulutli AI (ChatGPT va b.) | An'anaviy BI (Power BI va b.) | **QueryMind AI** |
|---|---|---|---|
| Ma'lumot mamlakat ichida | ❌ | ✅ | ✅ |
| Tabiiy tilda savol | ✅ | ⚠️ cheklangan | ✅ |
| O'zbek tili / lokal kontekst | ⚠️ | ❌ | ✅ |
| O'rnatish/SQL bilim talab qilmaydi | ✅ | ❌ | ✅ |
| Read-only xavfsizlik kafolati | ❌ | ⚠️ | ✅ |

---

## 7. Talab (Ask)

Pilot loyihalar va mahsulotni rivojlantirish uchun investitsiya va hamkorlik qidirmoqdamiz. Biz bilan birinchi pilotni boshlashga tayyor 3–5 ta korxona — bu bizning keyingi qadamimiz.

**QueryMind AI — ma'lumotlaringiz mamlakatda qoladi, javoblar esa bir necha soniyada keladi.**
