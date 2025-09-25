import random
from typing import List, Tuple

from .constants import C
from .session_counter import SessionCounter


class Matching:
    def __init__(self):
        # Not meant to be called, just remove annoying PyCharm notifications
        self.session = None
        self.get_group_matrix = None
        self.round_number = None
        self.get_groups = None
        self.get_players = None

        raise NotImplementedError

    def match_players(self):
        all_ids = sorted([i for g in self.get_group_matrix() for i in g])

        # Isolate the last player if there's an odd number
        odd_group = []
        if len(all_ids) % 2 == 1:
            odd_group = [all_ids.pop()]

        # Practice round 1 (random Bot or Human)
        if self.round_number == 1:
            groups = self._match_round_random_role(all_ids)
        # Practice round 2 (the opposite nature from the previous round)
        elif self.round_number == 2:
            groups = self._match_round_opposite_from_prev_round(all_ids)
        # Real round 3 (random Bot or Human)
        elif self.round_number == 3:
            groups = self._match_round_balanced_design_bot_human(all_ids)
        # Real rounds 4,5,6 (Same Nature as round 3 but random matched partner)
        elif 4 <= self.round_number <= 6:
            groups = self._match_round_same_as_previous(all_ids)
        # Real round 7 (the opposite to the previous round (Same as round 2))
        elif self.round_number == 7:
            groups = self._match_round_opposite_from_prev_round(all_ids)
        # Real round 8,9,10 (Same Nature as round 7 but random matched partner)
        elif 8 <= self.round_number <= 10:
            groups = self._match_round_same_as_previous(all_ids)
        else:
            raise NotImplementedError

        # Verify that all IDs are used exactly once
        msg = "Some IDs are either missing or used multiple times"
        assert all_ids == sorted([i for g in groups for i in g]), msg

        # Add the odd players group
        if odd_group:
            groups.append(odd_group)

        self._process_groups(groups)

    def _match_round_random_role(self, all_ids: List[int]) -> List[List[int]]:
        pref_role_ids, not_pref_role_ids = self._get_ids(all_ids)
        groups = []
        if self.session.config['use_bots']:
            Bot_first_=random.choice([0, 1])
            
            if Bot_first_==1 and self.session.config['within_balance_desgin_BOT_vs_HUMAN_4_at_a_time']== False:
                # All participants are matched against bots
                groups = [[idx] for idx in all_ids]
            elif  self.session.config['within_balance_desgin_BOT_vs_HUMAN_4_at_a_time']== True:
                # Only first 4 participants are matched against bots
                bot_ids = pref_role_ids[:2] + not_pref_role_ids[:2]
                pref_role_ids_for_match = pref_role_ids[2:] 
                not_pref_role_ids_for_match  = not_pref_role_ids[2:] 
                groups = [[idx] for idx in bot_ids]
                # The rest of the participants are matched against humans
                msg = "The groups must be of equal size for human matches"
                assert len(pref_role_ids_for_match) == len(not_pref_role_ids_for_match), msg
                random.shuffle(not_pref_role_ids)
                combos = zip(pref_role_ids_for_match, not_pref_role_ids_for_match)
                for pref_role_ids_for_match, not_pref_role_ids_for_match in combos:
                    groups.append([pref_role_ids_for_match, not_pref_role_ids_for_match])
            else:
                # All participants are matched against humans
                msg = "The groups must be of equal size for human matches"
                assert len(pref_role_ids) == len(not_pref_role_ids), msg
                random.shuffle(not_pref_role_ids)
                combos = zip(pref_role_ids, not_pref_role_ids)
                for pref_role_idx, not_pref_role_idx in combos:
                    groups.append([pref_role_idx, not_pref_role_idx])
        else:
            # All participants are matched against humans
            msg = "The groups must be of equal size for human matches"
            assert len(pref_role_ids) == len(not_pref_role_ids), msg
            random.shuffle(not_pref_role_ids)
            combos = zip(pref_role_ids, not_pref_role_ids)
            for pref_role_idx, not_pref_role_idx in combos:
                groups.append([pref_role_idx, not_pref_role_idx])

        return groups

    def _match_round_balanced_design_bot_human(self, all_ids: List[int]) \
            -> List[List[int]]:
        pref_role_ids, not_pref_role_ids = self._get_ids(all_ids)

        groups = []
        if self.session.config['use_bots']:
            if SessionCounter.in_balanced_list() and  \
                    self.session.config['override_third_round_HUMAN_vs_HUMAN']== False and \
                    self.session.config['override_third_round_BOT_vs_HUMAN'] == True and \
                    self.session.config['within_balance_desgin_BOT_vs_HUMAN_4_at_a_time'] == False:
                # All participants are matched against bots
                groups = [[idx] for idx in all_ids]
            elif self.session.config['within_balance_desgin_BOT_vs_HUMAN_4_at_a_time']== True and \
                self.session.config['override_third_round_HUMAN_vs_HUMAN']== False:
                # Only first 4 participants are matched against bots
                bot_ids = pref_role_ids[:2] + not_pref_role_ids[:2]
                pref_role_ids_for_match = pref_role_ids[2:] 
                not_pref_role_ids_for_match  = not_pref_role_ids[2:] 
                groups = [[idx] for idx in bot_ids]
                # The rest of the participants are matched against humans
                msg = "The groups must be of equal size for human matches"
                assert len(pref_role_ids_for_match) == len(not_pref_role_ids_for_match), msg
                random.shuffle(not_pref_role_ids)
                combos = zip(pref_role_ids_for_match, not_pref_role_ids_for_match)
                for pref_role_ids_for_match, not_pref_role_ids_for_match in combos:
                    groups.append([pref_role_ids_for_match, not_pref_role_ids_for_match])
            else:
                # All participants are matched against humans
                msg = "The groups must be of equal size for human matches"
                assert len(pref_role_ids) == len(not_pref_role_ids), msg
                random.shuffle(not_pref_role_ids)
                combos = zip(pref_role_ids, not_pref_role_ids)
                for pref_role_idx, not_pref_role_idx in combos:
                    groups.append([pref_role_idx, not_pref_role_idx])
        else:
            # All participants are matched against humans
            msg = "The groups must be of equal size for human matches"
            assert len(pref_role_ids) == len(not_pref_role_ids), msg
            random.shuffle(not_pref_role_ids)
            combos = zip(pref_role_ids, not_pref_role_ids)
            for pref_role_idx, not_pref_role_idx in combos:
                groups.append([pref_role_idx, not_pref_role_idx])

        return groups
    
    def _match_round_opposite_from_prev_round(self, all_ids: List[int]) \
                -> List[List[int]]:
            pref_role_ids, not_pref_role_ids = self._get_ids(all_ids)

            # When not using bots: everyone needs a human
            if not self.session.config['use_bots']:
                pref_role_human_ids, pref_role_bot_ids = pref_role_ids, []
                non_pref_role_human_ids, non_pref_role_bot_ids = \
                    not_pref_role_ids, []
            else:
                # Invert prefs compared to last round
                pref_role_human_ids, pref_role_bot_ids = \
                    self._get_type_ids(pref_role_ids)
                non_pref_role_human_ids, non_pref_role_bot_ids = \
                    self._get_type_ids(not_pref_role_ids)

            return self._get_groups(pref_role_human_ids, non_pref_role_human_ids,
                                    pref_role_bot_ids, non_pref_role_bot_ids)

    def _match_round_same_as_previous(self, all_ids: List[int]) \
            -> List[List[int]]:
        pref_role_ids, not_pref_role_ids = self._get_ids(all_ids)

        # When not using bots: everyone needs a human
        if not self.session.config['use_bots']:
            pref_role_human_ids, pref_role_bot_ids = pref_role_ids, []
            non_pref_role_human_ids, non_pref_role_bot_ids = \
                not_pref_role_ids, []
        else:
            # Invert prefs compared to last round
            pref_role_human_ids, pref_role_bot_ids = \
                self._get_type_ids(pref_role_ids, True)
            non_pref_role_human_ids, non_pref_role_bot_ids = \
                self._get_type_ids(not_pref_role_ids, True)



        return self._get_groups(pref_role_human_ids, non_pref_role_human_ids,
                                pref_role_bot_ids, non_pref_role_bot_ids)

    @staticmethod
    def _get_groups(pref_role_human_ids: List[int],
                    non_pref_role_human_ids: List[int],
                    pref_role_bot_ids: List[int],
                    non_pref_role_bot_ids: List[int]) -> List[List[int]]:
        assert len(pref_role_human_ids) == len(non_pref_role_human_ids)
        assert len(pref_role_bot_ids) == len(non_pref_role_bot_ids)

        groups = []
        for pref_role_idx in pref_role_human_ids:
            other_id = non_pref_role_human_ids.pop(
                random.randrange(len(non_pref_role_human_ids)))
            groups.append([pref_role_idx, other_id])
        assert len(non_pref_role_human_ids) == 0

        # Assign remaining players to bots
        for pref_role_idx in pref_role_bot_ids:
            groups.append([pref_role_idx])
        for not_pref_role_idx in non_pref_role_bot_ids:
            groups.append([not_pref_role_idx])

        return groups

    def _get_ids(self, all_ids: List[int]) -> Tuple[List[int], List[int]]:
        # Split ids in 2 lists, depending on role preference, used in all rounds
        pref_role = self.get_groups()[0].preference_role
        not_pref_role = 1 - C.ROLES.index(pref_role)
        pref_role_ids = [idx for idx in all_ids if idx % 2 == not_pref_role]
        not_pref_role_ids = list(set(all_ids) - set(pref_role_ids))
        random.shuffle(pref_role_ids)
        random.shuffle(not_pref_role_ids)
        return pref_role_ids, not_pref_role_ids

    def _get_type_ids(self, ids: List[int], opposite: bool = False) \
            -> Tuple[List[int], List[int]]:
        # Split ids in 2 lists, depending on previous round, used in round 2
        players = self.get_players()
        ids1, ids2 = [], []
        for idx in ids:
            prev_player = players[idx - 1].in_round(
                players[idx - 1].round_number - 1)
            if prev_player.bot_opponent:
                ids1.append(idx)
            else:
                ids2.append(idx)
        if opposite:
            return ids2, ids1
        return ids1, ids2

    def _process_groups(self, groups: List[List[int]]):
        debug_log = []
        players = self.get_players()
        for group_idx, group in enumerate(groups, 1):
            debug_log.append(f"{group_idx} {group}")
            channel_id = f"{self.round_number}_{group_idx}"
            if len(group) == 1:
                player = players[group[0] - 1]
                player.channel_id = channel_id
            elif len(group) > 1:
                player_1 = players[group[0] - 1]
                player_2 = players[group[1] - 1]
                player_2.other_id, player_1.other_id = group
                player_2.channel_id = player_1.channel_id = channel_id

                assert len(group) == 2
                assert sorted(C.ROLES) == sorted([player_1.role, player_2.role])
        self.session.debug_log[self.round_number].append(
            'GROUPS: ' + '   '.join(debug_log))