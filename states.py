from aiogram.dispatcher.filters.state import State, StatesGroup

class MyState(StatesGroup):
    phone_number_received = State()
    waiting_for_name = State()
    waiting_for_dob = State()
    confirm_data = State()

class MyAnotherState(StatesGroup):
    phone_number_received = State()
    waiting_for_patient_name = State()
    waiting_for_doctor_name = State()
    waiting_for_dob = State()
    confirm_data = State()

class AnswerState(StatesGroup):
    WaitingForAnswer = State()

class QuestionState(StatesGroup):
    WaitingForQuestion = State()

class BroadcastState(StatesGroup):
    text = State()
    photo = State()
    preview = State()
