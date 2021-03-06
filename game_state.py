import buildings
import text_events
import terrain
from copy import copy
from game_errors import GameplayError
from collections import deque
from random import randint

class Game:
    """Facade class used as an interface to control the game backend"""

    def __init__(self):
        #turn number
        self.turn = 1

        #set main stats
        self.money = 1000
        self.population = 100

        #set additional stats
        self.prestige = 0
        self.safety = 0
        self.technology = 0
        self.food = 0
        self.health = 0

        #make map
        MAP_WIDTH = 100
        MAP_HEIGTH = 100
        # self.map = [[0 for x in range(MAP_WIDTH)] for y in range(MAP_HEIGTH)]
        self.map = terrain.MapPrototype(MAP_HEIGTH,MAP_WIDTH)

        # actions per turn
        self._actions_max = 3
        self.actions = self._actions_max

        # list of buildings on the map (so we don't have to iterate through the whole map to apply per-turn effects)
        self.buildings_on_map = []

        # list of buildings that the player can construct
        self.buildings_deck = buildings.get_initial_buildings()

        # events that must be handled before taking an action or ending a turn (with get_next_event() method)
        self._event_queue = deque()

        # available random events (each turn, there is a chance that one of them will be added to _event_queue)
        self._event_active_deck = deque(text_events.get_basic_random_events())

        # random events not yet unlocked
        self._event_inactive_deck = []

    def build(self, number, x, y):
        #initial requirements checks
        self._try_performing_action()
        if self.money < self.buildings_deck[number].base_price:
            self.actions += 1
            raise GameplayError("You don't have enough money to create this building.")
        if not self.buildings_deck[number].can_be_built(
               self.map.get_field_by_coordinates(x,y),
               self.map.get_neighbors(x,y)):
            self.actions += 1
            raise GameplayError("This building cannot be created here")

        new_building = copy(self.buildings_deck[number])  # buildings on map must not be references to buildings in deck
        self.map.add_building(new_building,x,y)           # so that changes to their attributes (e.g. price being
                                                          # modified depending on terrain) don't affect other instances
        if self.money < new_building.price:
            self.map.remove_building(x,y)
            self.actions += 1
            raise GameplayError("You don't have enough money to build here")

        self.buildings_on_map.append(new_building)
        self.money -= new_building.price
        # building-specific actions
        new_building.on_build(self)

    def demolish(self, x, y):
        self._try_performing_action()
        ref = self.map.get_field_by_coordinates(x,y).building
        if not ref:
            self.actions += 1
            raise GameplayError("Nothing to destroy!")
        self.map.remove_building(x,y)
        self.buildings_on_map.remove(ref)
        ref.on_destroy(self)

    def get_next_event(self):
        if not self._event_queue:
            return
        return self._event_queue.popleft()

    def end_turn(self):
        if self._event_queue:
            raise  GameplayError("You still have unhandled events.")
        self.actions = self._actions_max
        self.turn += 1

        for x in self.buildings_on_map:
            #self.money -= x.upkeep_cost
            x.on_next_turn(self)

        # lock/unlock random events depending on conditions
        move_between_lists(self._event_inactive_deck, self._event_active_deck, lambda a: a.should_be_activated(self))
        move_between_lists(self._event_active_deck, self._event_inactive_deck, lambda a: a.should_be_deactivated(self))

        if self._event_active_deck:
            # print("aaaaaa")
            if randint(1,10) == 10:
                self._event_queue.append(self._event_active_deck.popleft())
                # print(self._event_queue[0])

    def _try_performing_action(self):
        # common functionality for all actions
        if self._event_queue:
            raise  GameplayError("You still have unhandled events.")
        if not self.actions:
            raise GameplayError("You don't have enough actions left.")
        self.actions -= 1


def move_between_lists(source, dest, func):
    temp = list(filter(func, source))  # why does py3 functional programming suck so much?
    dest.extend(temp)
    for f in temp:
        source.remove(f)