from aiogram.filters.state import State, StatesGroup

class UserRegistrationState(StatesGroup):
    GET_REFFERAL_CODE = State()
    GET_FULL_NAME = State()
    GET_CARD_NUMBER = State()
    GET_CARD_HOLDER_NAME = State()
    GET_PHONE_NUMBER = State()
    GET_REGION = State()
    GET_AGE = State()
    GET_PROFESSION = State()
    GET_GENDER = State()
    


# FSM holatlari
class BuyCourseState(StatesGroup):
    WAITING_FOR_SCREENSHOT = State()

