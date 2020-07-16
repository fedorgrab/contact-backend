from enum import Enum

NUMBER_OF_PLAYERS_TO_START = 3
CONTACT_AWAITING_TIME = 5


class POINTS:
    CONTACT_CANCEL = 1
    CONTACT_CANCEL_COMBO_3 = 3
    CONTACT_INITIATOR_SUCCESS = 3
    CONTACT_PARTICIPANT_SUCCESS = 2


class GameEvent(Enum):
    # Game Lifecycle
    START = "start"
    CONTINUE = "continue"
    FINISH = "finish"
    # Game Actions
    MESSAGE_RECEIVE = "message"
    MESSAGE_COMMENT = "message_comment"
    SET_WORD = "word"
    CONTACT = "contact"
    CONTACT_RESULT = "contact_result"
    CANCEL_CONTACT = "contact_cancel"
