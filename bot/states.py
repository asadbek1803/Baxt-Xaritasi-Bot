from aiogram.filters.state import State, StatesGroup

class UserRegistrationState(StatesGroup):
    GET_FULL_NAME = State()
    GET_PHONE_NUMBER = State()
    GET_REGION = State()
    GET_AGE = State()
    GET_PROFESSION = State()
    GET_GENDER = State()
    

