from typing import List

from otree.api import *

greedy_list = [number for i in range(0, 1000, 8)
               for number in range(i + 1, i + 5)]

balanced_list = [number for i in range(0, 1000, 4)
                 for number in range(i + 1, i + 3)]


class SessionCounter(ExtraModel):
    session_code = models.StringField()

    @classmethod
    def add_code(cls, session_code: str):
        cls.create(session_code=session_code)

    @classmethod
    def count(cls) -> int:
        return len(cls.values_dicts())

    @classmethod
    def in_greedy_list(cls) -> bool:
        return cls.count() in greedy_list

    @classmethod
    def in_balanced_list(cls) -> bool:
        return cls.count() in balanced_list

    @classmethod
    def choices(cls) -> List[str]:
        return sorted({b['name'] for b in cls.values_dicts()})

    @classmethod
    def remove_key(cls):
        for bid_dict in cls.values_dicts():
            bid = cls.objects_get(id=bid_dict['id'])
            bid.delete()
