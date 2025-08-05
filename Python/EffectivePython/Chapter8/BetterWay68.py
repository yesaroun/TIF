# Better Way 68 copyreg 를 사용해 pickle을 더 신뢰성 있게 만들라

import pickle


class GameState:
    def __init__(self, level=0, lives=4, points=0):
        self.level = level  # 레벨
        self.lives = lives  # 생명 개수
        self.points = points


state = GameState()
state.level += 1
state.lives -= 1

print(state.__dict__)
# {'level': 1, 'lives': 3}


state_path = "gate_state.bin"  # GameState 객체를 기록할 파일
with open(state_path, "wb") as f:
    pickle.dump(state, f)  # dump 함수 사용해 상태 기록

with open(state_path, "rb") as f:
    state_after = pickle.load(f)  # load 함수 사용해 돌려받을 수 있다.

print(state_after.__dict__)
# {'level': 1, 'lives': 3}


def pickle_game_state(game_state):
    kwargs = game_state.__dict__
    return unpickle_game_state, (kwargs,)


def unpickle_game_state(kwargs):
    return GameState(**kwargs)
