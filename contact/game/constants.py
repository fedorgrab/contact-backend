from enum import Enum

NUMBER_OF_PLAYERS_TO_START = 3
CONTACT_AWAITING_TIME = 5  # seconds
GAME_TIME_LIMIT = 60 * 5  # 5 minutes
ROOM_CLEANING_DELAY = 5  # seconds
PLAYER_DISCONNECTION_AWAITING_TIME = 7  # seconds
DISCONNECTION_KEY_FORMAT = "disconnection:{player_id}"
CLEANING_ROOM_KEY_FORMAT = "cleaning:room:{room_id}"


class POINTS:
    CONTACT_CANCEL = 1
    CONTACT_CANCEL_COMBO_3 = 3
    CONTACT_INITIATOR_SUCCESS = 3
    CONTACT_PARTICIPANT_SUCCESS = 2


class GameFinishReason:
    DISCONNECTION = "disconnection"
    GAME_TIME_LIMIT_EXPIRED = "time_limit_expired"
    GAME_HOST_WON = "host_won"
    PLAYERS_WON = "players_won"


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
