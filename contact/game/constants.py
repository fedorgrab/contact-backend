from enum import Enum


class GameEvent(Enum):
    START = "start"
    RECEIVE_MESSAGE = "message"
    SET_WORD = "word"
    CONTACT = "contact"
    CANCEL_CONTACT = "contact_cancel"
