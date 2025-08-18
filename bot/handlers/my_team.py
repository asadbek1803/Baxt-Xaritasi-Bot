from aiogram import types, F, Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from datetime import datetime
from bot.handlers.my_profile import format_user_level
from bot.selectors import (
    get_user_referrals,
    get_user_referrals_count,
    get_user_referral_tree,
    get_confirmed_referrals_count,
)
import math
from bot.buttons.default.back import get_back_keyboard

router = Router()


async def safe_edit_message(
    query: types.CallbackQuery, text: str, keyboard: InlineKeyboardMarkup = None
):
    """Xabarni xavfsiz tahrirlash"""
    try:
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Xabar o'zgarmaganida hech narsa qilmaslik
            pass
        else:
            # Boshqa xatoliklarni qayta raise qilish
            raise e


@router.message(F.text == "👥 Mening jamoam")
async def my_team_handler(message: types.Message):
    """Foydalanuvchining referal jamoasini ko'rsatish"""
    user_id = str(message.from_user.id)

    # Foydalanuvchining referal sonini olish
    referrals_count = await get_user_referrals_count(user_id)

    if referrals_count == 0:
        await message.answer(
            "🚫 <b>Sizda hali referal yo'q</b>\n\n"
            "👥 Referal jamoangizni kengaytirish uchun:\n"
            "• Referal havolangizni ulashing\n"
            "• Do'stlaringizni taklif qiling\n"
            "• Mukofotlar oling!\n\n"
            "💡 <b>Referal havolangizni olish uchun:</b>\n"
            "🔗 Referal havola tugmasini bosing",
            parse_mode="HTML",
            reply_markup=get_back_keyboard(),
        )
        return

    # Birinchi sahifani ko'rsatish
    await show_team_page(message, user_id, page=0)


async def show_team_page(message_or_query, user_id: str, page: int = 0):
    """Jamoa sahifasini ko'rsatish"""
    page_size = 8
    offset = page * page_size

    # Foydalanuvchining referallarini olish
    referrals = await get_user_referrals(user_id, limit=page_size, offset=offset)
    total_count = await get_user_referrals_count(user_id)

    # Sahifalar sonini hisoblash
    total_pages = math.ceil(total_count / page_size)

    # Xabar matni
    text = "👥 <b>Mening jamoam</b>\n\n"
    text += f"📊 <b>Jami referallar:</b> {total_count} ta\n"
    text += f"📄 <b>Sahifa:</b> {page + 1}/{total_pages}\n"
    text += f"🕐 <b>Yangilandi:</b> {datetime.now().strftime('%H:%M')}\n\n"

    if referrals:
        text += "👤 <b>Referal a'zolar:</b>\n\n"

        for i, referral in enumerate(referrals, start=1):
            # Har bir referal uchun ma'lumot
            ref_count = await get_user_referrals_count(referral.telegram_id)
            status = "✅" if referral.is_confirmed else "⏳"

            text += f"{offset + i}. {status} <b>{referral.full_name}</b>\n"
            text += f"   📞 {referral.phone_number}\n"
            text += f"   🏆 Daraja: {format_user_level(referral.level)}\n"
            text += f"   👥 Uning referallari: {ref_count} ta\n"
            text += f"   📅 Qo'shilgan: {referral.registration_date.strftime('%d.%m.%Y')}\n\n"
    else:
        text += "🚫 Bu sahifada hech kim yo'q"

    # Klaviatura yaratish
    keyboard = create_team_keyboard(page, total_pages, user_id)

    # Xabar yuborish yoki tahrirlash
    if isinstance(message_or_query, types.Message):
        await message_or_query.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await safe_edit_message(message_or_query, text, keyboard)


def create_team_keyboard(
    page: int, total_pages: int, user_id: str
) -> InlineKeyboardMarkup:
    """Jamoa klaviaturasini yaratish"""
    keyboard = []

    # Sahifalash tugmalari
    nav_buttons = []

    # Oldingi sahifa
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="◀️ Oldingi", callback_data=f"team_page:{user_id}:{page-1}"
            )
        )

    # Sahifa raqami
    nav_buttons.append(
        InlineKeyboardButton(
            text=f"📄 {page + 1}/{total_pages}", callback_data="ignore"
        )
    )

    # Keyingi sahifa
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="Keyingi ▶️", callback_data=f"team_page:{user_id}:{page+1}"
            )
        )

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Qo'shimcha funktsiyalar
    action_buttons = [
        [
            InlineKeyboardButton(
                text="🌳 Referal daraxti", callback_data=f"ref_tree:{user_id}"
            ),
            InlineKeyboardButton(
                text="📊 Statistika", callback_data=f"ref_stats:{user_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔄 Yangilash", callback_data=f"team_page:{user_id}:{page}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Ortga", callback_data="back_to_home"
            )
        ],
        
    ]

    keyboard.extend(action_buttons)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.callback_query(F.data.startswith("team_page:"))
async def team_page_callback(query: types.CallbackQuery):
    """Sahifa o'zgartirish callback"""
    try:
        _, user_id, page_str = query.data.split(":")
        page = int(page_str)

        # Faqat o'z jamoasini ko'ra olishi
        if str(query.from_user.id) != user_id:
            await query.answer("❌ Bu sizning jamoangiz emas!", show_alert=True)
            return

        await show_team_page(query, user_id, page)
        await query.answer()
    except (ValueError, IndexError):
        await query.answer("❌ Xatolik yuz berdi!", show_alert=True)


@router.callback_query(F.data.startswith("ref_tree:"))
async def referral_tree_callback(query: types.CallbackQuery):
    """Referal daraxti ko'rsatish"""
    try:
        _, user_id = query.data.split(":")

        # Faqat o'z daraxtini ko'ra olishi
        if str(query.from_user.id) != user_id:
            await query.answer("❌ Bu sizning daraxtingiz emas!", show_alert=True)
            return

        await show_referral_tree(query, user_id)
        await query.answer()
    except (ValueError, IndexError):
        await query.answer("❌ Xatolik yuz berdi!", show_alert=True)


@router.callback_query(F.data.startswith("ref_stats"))
async def referral_stats_callback(query: types.CallbackQuery):
    """Referal statistikasi"""
    try:
        user_id = query.message.from_user.id
        await show_referral_stats(query, user_id)
        await query.answer()
    except (ValueError, IndexError):
        await query.answer("❌ Xatolik yuz berdi!", show_alert=True)


async def show_referral_tree(query: types.CallbackQuery, user_id: str):
    """Referal daraxtini ko'rsatish (3 daraja chuqurligida)"""
    tree_data = await get_user_referral_tree(user_id, depth=3)

    text = "🌳 <b>Referal daraxti</b>\n\n"

    if not tree_data:
        text += "🚫 Referal daraxtingiz bo'sh"
    else:
        text += format_referral_tree(tree_data, level=0)

    # Orqaga qaytish tugmasi
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="◀️ Orqaga", callback_data="back_to_home"
                )
            ]
        ]
    )

    try:
        await safe_edit_message(query, text, keyboard)
    except Exception:
        await query.message.answer(text, reply_markup=keyboard, parse_mode="HTML")


def format_referral_tree(tree_data: list, level: int = 0) -> str:
    """Referal daraxtini formatlash"""
    result = ""
    prefix = "    " * level

    for i, user_data in enumerate(tree_data, 1):
        user = user_data["user"]
        children = user_data.get("children", [])

        # Daraja belgilari
        if level == 0:
            symbol = "👤"
        elif level == 1:
            symbol = "├─👥"
        else:
            symbol = "├──👶"

        status = "✅" if user.is_confirmed else "⏳"
        result += f"{prefix}{symbol} {status} <b>{user.full_name}</b>\n"
        result += f"{prefix}    📞 {user.phone_number}\n"
        result += f"{prefix}    🏆 {format_user_level(user.level)}\n"

        # Bolalar daraxtini ko'rsatish
        if children and level < 2:  # Faqat 3 daraja
            result += format_referral_tree(children, level + 1)

        if i < len(tree_data):
            result += "\n"

    return result


async def show_referral_stats(query: types.CallbackQuery, user_id: str):
    """Referal statistikasini ko'rsatish"""
    # Statistika ma'lumotlarini olish
    total_referrals = await get_user_referrals_count(user_id)
    confirmed_referrals = await get_confirmed_referrals_count(user_id)
    pending_referrals = total_referrals - confirmed_referrals

    text = "📊 <b>Referal statistikasi</b>\n"
    text += f"👥 <b>Jami referallar:</b> {total_referrals} ta\n"
    text += f"✅ <b>Tasdiqlangan:</b> {confirmed_referrals} ta\n"
    text += f"⏳ <b>Kutilayotgan:</b> {pending_referrals} ta\n"

    # Orqaga qaytish tugmasi
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="◀️ Orqaga", callback_data="back_to_home"
                )
            ]
        ]
    )

    try:
        await safe_edit_message(query, text, keyboard)
    except Exception:
        # Agar edit ishlamasa, yangi xabar yuborish
        await query.message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "ignore")
async def ignore_callback(query: types.CallbackQuery):
    """Ignore callback - hech narsa qilmaydi"""
    await query.answer()
