from aiogram import Router, F, types
from bot.buttons.default.back import get_back_keyboard

router = Router()

@router.message(F.text == "📑 Loyiha haqida")
async def project_about_handler(message: types.Message):
    await message.answer(
        "📑 <b>Loyiha haqida ma'lumot</b>\n\n"
        "🌟 Ushbu loyiha sizning muvaffaqiyatingiz uchun yaratilgan!\n\n"
        "💡 Biz taqdim etadigan imkoniyatlar:\n"
        "├ 🎯 Aniq maqsadlarni belgilash\n"
        "├ 📊 Progress kuzatuvi\n" 
        "├ 🤝 Professional qo'llab-quvvatlash\n"
        "└ 📈 Muntazam rivojlanish\n\n"
        "🔥 Bizning professional jamoamiz sizning muvaffaqiyatingiz uchun ishlaydi\n"
        "✨ Har bir qadam muhim - biz siz bilan birgamiz!\n\n"
        "📞 Savollar va takliflar uchun:\n"
        "└ Administratorga murojaat qiling\n\n"
        "🚀 Keling, birgalikda muvaffaqiyatga erishamiz!",
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )