from enum import Enum

# Constants for regions in Uzbekistan
REGIONS = [
    ("tashkent", "Toshkent"),
    ("samarkand", "Samarqand"),
    ("bukhara", "Buxoro"),
    ("andijan", "Andijon"),
    ("fergana", "Farg'ona"),
    ("namangan", "Namangan"),
    ("kashkadarya", "Qashqadaryo"),
    ("surkhandarya", "Surxondaryo"),
    ("khorezm", "Xorazm"),
    ("navoi", "Navoiy"),
    ("jizzakh", "Jizzax"),
    ("sirdarya", "Sirdaryo"),
    ("karakalpakstan", "Qoraqalpog'iston"),
]

# Constants for professions
PROFESSIONS = [
    ("dev", "Dasturchi"),
    ("eng", "Muhandis"),
    ("teacher", "O'qituvchi"),
    ("med", "Tibbiyot xodimi"),
    ("biz", "Biznesmen"),
    ("art", "San'atkor"),
    ("sci", "Ilmiy xodim"),
    ("build", "Quruvchi"),
    ("mkt", "Marketing mutaxassisi"),
    ("mgr", "Boshqaruvchi"),
    ("fin", "Moliyachi"),
    ("photo", "Fotograf"),
    ("design", "Dizayner"),
    ("psy", "Psixolog"),
    ("home", "Uy bekasi"),
    ("student", "Talaba"),
    ("other", "Boshqa")
]


# Constants for gender choices
GENDER = [
    ("M", "Erkak"),
    ("F", "Ayol"),
]

AGE_CHOICES = [
        ('18-24', '18-24'),
        ('25-34', '25-34'),
        ('35-44', '35-44'),
        ('45+', '45+'),
    ]

LEVEL_CHOICES = [
    ('level_0', "0-bosqich"),
    ('level_1', "1-bosqich"),
    ('level_2', "2-bosqich"),
    ('level_3', "3-bosqich"),
    ('level_4', "4-bosqich"),
    ('level_5', "5-bosqich"),
    ('level_6', "6-bosqich"),
    ('level_7', "7-bosqich"),
]

# Statuslar Choices
STATUS_CHOICES = [
        ('PENDING', 'Kutilmoqda'),
        ('CONFIRMED', 'Tasdiqlangan'),
        ('REJECTED', 'Rad etilgan')
    ]

PAYMENT_TYPES = [
        ('KONKURS', 'Konkurs to\'lovi'),
        ('COURSE', 'Kurs to\'lovi'),
        ('DONATION', 'Xayriya to\'lovi')
    ]

# Button Enum

class Button(Enum):
    send_phone_number = "📲 Telefon raqamini yuborish"
    contact = "📞 Aloqa"
    company_about = "🏢 Kompaniya haqida"
    guide = "📖 Yo'riqnoma"
    my_profile = "👤 Mening hisobim"
    my_team = "👥 Mening jamoam"
    projects = "📂 Loyihalar"
    back = "🔙 Orqaga"
    check_member_to_channel = "✅ A'zo bo'ldim"

class Messages(Enum):
    # User Registration card messages
    ask_full_name = "📝 Familya, Ism, Sharifingizni to'liq kiriting:"
    ask_phone_number = "📞 Telefon raqamingizni yuboring:"
    ask_region = "🌍 Hududingizni tanlang:"
    ask_profession = "💼 Kasbingizni tanlang: "
    ask_gender = "👤 Jinsingizni tanlang:"

    welcome_message_for_registration = """Assalomu alaykum. \n\nSiz ro'yxatdan muvaffaqiyatli o'tdingiz!\nSahifamizga xush kelibsiz!🥰\n\nUshbu bot orqali siz psixolog <b>Gulhayo Mo'minova</b>ning kurslari orqali ham ruhan rivojlanasiz ham oylik daromadga ega bo'lasiz. \n\n\nTo'liq botdan foydalanish uchun avvalo <b>1-bosqich</b> SHUKRONALIK MO'JIZALARI kursimizga 40ming so'm to'lov qiling."""

    welcome_message = """Assalomu alaykum, {full_name}!\n\nSiz botimizga xush kelibsiz! Bu yerda siz o'z kasbingiz bo'yicha rivojlanishingiz va yangi imkoniyatlar topishingiz mumkin.\n\nIltimos, quyidagi tugmalar orqali davom eting:"""

    # Check member to channel
    do_member_in_channel = """🚀 Loyihada ishtirok etish uchun quyidagi kanallarga a'zo bo'ling. Keyin <b>"✅ A'zo bo'ldim"</b> tugmasini bosing\n\n⚠️ <i>Yopiq kanallarga ulanish so'rovini yuborishingiz kifoya.</i>"""
    # Registration error messages
    registration_error = "❌ Ro'yxatdan o'tishda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring."
    full_name_error = "❌ To'liq ism 3-100 ta belgi orasida bo'lishi kerak. Qaytadan kiriting:"
    profession_error = "❌ Noto'g'ri kasb tanlandi. Iltimos, qaytadan tanlang."
    phone_number_error = """❌ Telefon raqam noto'g'ri formatda!\n"
            "Iltimos, tugmani bosing yoki +998901234567 formatida kiriting:"""
    region_error = "❌ Noto'g'ri hudud tanlandi. Iltimos, qaytadan tanlang."
    system_error = "❌ Tizimda xatolik yuz berdi. Keyinroq urinib ko'ring."
    select_region_success = "✅ Siz {region} hududini tanladingiz."
    select_profession_success = "✅ Siz {profession} kasbini tanladingiz."
    gender_error = "❌ Iltimos, jinsingizni tanlang: Erkak yoki Ayol."
    too_requests = "❗️ Siz juda ko'p so'rov yubordingiz. Iltimos, bir necha daqiqa kuting va qaytadan urinib ko'ring."
    # To'lov rekvizitlari
    
    payment_details = (
        "💳 <b>To'lov uchun rekvizitlar:</b>\n"
        "🏦 Karta raqami: <code>{card_number}</code>\n"
        "👤 Ism: {owner_name}\n\n"
        "💰 To'lov summasi: <b>{amount} so'm</b>\n\n"
        "📸 To'lovni amalga oshirib, chek (screenshot) yuboring."
    )

