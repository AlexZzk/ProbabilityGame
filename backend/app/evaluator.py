"""双色球中奖等级判定。"""


def prize_level(red_hits: int, blue_hit: bool) -> int:
    """返回奖级 1-6，0 表示未中奖。"""
    b = 1 if blue_hit else 0
    if red_hits == 6 and b == 1:
        return 1
    if red_hits == 6 and b == 0:
        return 2
    if red_hits == 5 and b == 1:
        return 3
    if (red_hits == 5 and b == 0) or (red_hits == 4 and b == 1):
        return 4
    if (red_hits == 4 and b == 0) or (red_hits == 3 and b == 1):
        return 5
    if b == 1 and red_hits in (0, 1, 2):
        return 6
    return 0


def evaluate(pred_reds: list[int], pred_blue: int, real_reds: list[int], real_blue: int) -> tuple[int, bool, int]:
    """返回 (红球命中数, 蓝球是否命中, 奖级)"""
    red_hits = len(set(pred_reds) & set(real_reds))
    blue_hit = pred_blue == real_blue
    return red_hits, blue_hit, prize_level(red_hits, blue_hit)
