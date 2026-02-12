# -*- coding: utf-8 -*-
from typing import Dict, List


def filter_search_result_card(card_list: List[Dict]) -> List[Dict]:
    """
    Filter Weibo search results, only keep data with card_type of 9
    :param card_list: List of card items from search results
    :return: Filtered list of note items
    """
    note_list: List[Dict] = []
    for card_item in card_list:
        if card_item.get("card_type") == 9:
            note_list.append(card_item)
        if len(card_item.get("card_group", [])) > 0:
            card_group = card_item.get("card_group")
            for card_group_item in card_group:
                if card_group_item.get("card_type") == 9:
                    note_list.append(card_group_item)

    return note_list
