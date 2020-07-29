from enum import Enum

NUMBER_OF_PLAYERS_TO_START = 3
CONTACT_AWAITING_TIME = 5
GAME_TIME_LIMIT = 60 * 3  # 3 mins


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
    ROOM_STATE = "room_state"
    PLAYER_STATE = "player_state"
    # Game Actions
    OFFER = "offer"
    OFFER_COMMENT = "offer_comment"
    SET_WORD = "word"
    CONTACT = "contact"
    CONTACT_RESULT = "contact_result"
    CANCEL_CONTACT = "contact_cancel"
