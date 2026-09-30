"""Every algorithm quoted in rag_notes must pass these checks. If you edit a note's
algorithm, add it here first."""
from rubik_tutor.cube import SOLVED, apply_moves, invert, stages_done

ALGS = {
    "trigger": "R U R' U'",
    "second_layer_right": "U R U' R' U' F' U F",
    "second_layer_left": "U' L' U L U F U' F'",
    "top_cross": "F R U R' U' F'",
    "sune": "R U R' U R U2 R'",
    "corner_perm": "R' F R' B2 R F' R' B2 R2",
    "edge_perm": "R U' R U R U R U' R' U' R2",
}


def pre(alg):
    """State that `alg` solves (the alg's inverse applied to a solved cube)."""
    return apply_moves(SOLVED, invert(alg))


def order(alg):
    s, k = apply_moves(SOLVED, alg), 1
    while s != SOLVED:
        s, k = apply_moves(s, alg), k + 1
    return k


def test_orders():
    assert order(ALGS["trigger"]) == 6
    assert order(ALGS["top_cross"]) == 6
    assert order(ALGS["sune"]) == 6
    assert order(ALGS["corner_perm"]) == 3
    assert order(ALGS["edge_perm"]) == 3


def test_layer_preservation():
    for name in ("second_layer_right", "second_layer_left"):
        assert "first_layer" in stages_done(apply_moves(SOLVED, ALGS[name]))
    for name in ("top_cross", "sune", "corner_perm", "edge_perm"):
        assert "first_two_layers" in stages_done(apply_moves(SOLVED, ALGS[name]))
    # the two permutation algs must also keep the last-layer orientation intact
    for name in ("corner_perm", "edge_perm"):
        assert "top_face" in stages_done(apply_moves(SOLVED, ALGS[name]))


def test_second_layer_recognition():
    # edge at front-top: front sticker = F colour, top sticker = R (or L) colour
    r, l = pre(ALGS["second_layer_right"]), pre(ALGS["second_layer_left"])
    assert (r[7], r[19]) == ("R", "F")
    assert (l[7], l[19]) == ("L", "F")


def _top_edges_oriented(s):
    return {"back": s[1] == "U", "left": s[3] == "U", "right": s[5] == "U", "front": s[7] == "U"}


def _align_for_top_cross(s):
    """Turn U so the pattern is 'horizontal line' or 'L at back-left' (dot: no turn needed)."""
    want = [{"back": False, "left": True, "right": True, "front": False},
            {"back": True, "left": True, "right": False, "front": False}]
    for turn in ([], ["U"], ["U2"], ["U'"]):
        t = apply_moves(s, turn)
        if _top_edges_oriented(t) in want:
            return t, turn
    return s, []          # dot


def test_top_cross_procedure():
    """Procedure in the notes: align with U turns, run the alg, repeat. At most 3 runs."""
    import random
    from rubik_tutor.cube import is_valid_counts
    rng = random.Random(5)
    pool = ["F R U R' U' F'", "R U R' U R U2 R'", "U R U' L' U R' U' L",
            "R U' R U R U R U' R' U' R2", "U", "U'", "U2"]
    worst, seen = 0, set()
    for _ in range(400):
        seq = []
        for _ in range(rng.randint(2, 8)):
            seq += rng.choice(pool).split()
        s = apply_moves(SOLVED, seq)                    # F2L solved, random last layer
        seen.add(tuple(_top_edges_oriented(s).values()))
        runs = 0
        while not all(_top_edges_oriented(s).values()):
            s, _ = _align_for_top_cross(s)
            s = apply_moves(s, ALGS["top_cross"])
            runs += 1
            assert runs <= 3 and "first_two_layers" in stages_done(s)
        worst = max(worst, runs)
    assert worst == 3          # the dot case really needs three runs
    assert (False, False, False, False) in seen      # dot was exercised


def test_sune_and_perm_recognition():
    s = pre(ALGS["sune"])
    assert [s[i] == "U" for i in (0, 2, 6, 8)] == [False, False, True, False]   # yellow corner front-left
    s = pre(ALGS["corner_perm"])
    assert all(s[i] == SOLVED[i] for i in (6, 18, 38))                          # correct corner front-left
    s = pre(ALGS["edge_perm"])
    assert s[1] == "U" and s[46] == "B"                                        # correct edge at the back


def test_last_layer_permutation_procedure():
    """Corner + edge permutation procedure (rubik_tutor.last_layer) solves every generated last layer,
    including swap/parity cases produced by T-perms."""
    import random
    from rubik_tutor.last_layer import position_corners, position_edges
    rng = random.Random(21)
    tperm = "R U R' U' R' F R2 U' R' U' R U R' F'"
    pool = [ALGS["corner_perm"], ALGS["edge_perm"], tperm, "U", "U'", "U2"]
    worst = 0
    for _ in range(1500):
        seq = []
        for _ in range(rng.randint(2, 8)):
            seq += rng.choice(pool).split()
        s = apply_moves(SOLVED, seq)
        s, g1 = position_corners(s)
        s, g2 = position_edges(s)
        assert s == SOLVED
        worst = max(worst, len(g1) + len(g2))
    assert worst <= 6


def test_permutation_algs_are_pure():
    """corner_perm moves only corners, edge_perm only edges (top layer)."""
    corner_stickers = (0, 2, 6, 8, 36, 47, 45, 11, 20, 9, 18, 38)
    edge_stickers = (1, 46, 3, 37, 5, 10, 7, 19)
    sc = apply_moves(SOLVED, ALGS["corner_perm"])
    se = apply_moves(SOLVED, ALGS["edge_perm"])
    assert all(sc[i] == SOLVED[i] for i in edge_stickers)
    assert all(se[i] == SOLVED[i] for i in corner_stickers)


def test_sune_procedure():
    """1 yellow corner -> hold at front-left; 0 -> yellow faces left on front-left;
    2 -> front-left not yellow-up and its yellow sticker faces front. At most 3 Sune runs."""
    import random
    rng = random.Random(11)
    pool = [ALGS["top_cross"], ALGS["sune"], ALGS["corner_perm"], ALGS["edge_perm"], "U", "U'", "U2"]
    cnt = lambda s: sum(s[i] == "U" for i in (0, 2, 6, 8))
    conds = {1: lambda t: t[6] == "U", 0: lambda t: t[38] == "U",
             2: lambda t: t[6] != "U" and t[18] == "U"}
    tested = worst = 0
    for _ in range(3000):
        seq = []
        for _ in range(rng.randint(2, 8)):
            seq += rng.choice(pool).split()
        s = apply_moves(SOLVED, seq)
        if not all(s[i] == "U" for i in (1, 3, 5, 7)):
            continue                                      # only states with the top cross done
        tested += 1
        runs = 0
        while cnt(s) != 4:
            aligned = [apply_moves(s, tr) for tr in ([], ["U"], ["U2"], ["U'"])]
            s = next(t for t in aligned if conds[cnt(s)](t))
            s = apply_moves(s, ALGS["sune"])
            runs += 1
            assert runs <= 3 and "first_two_layers" in stages_done(s)
        assert "top_face" in stages_done(s)                 # whole top face yellow at the end
        worst = max(worst, runs)
    assert tested > 500 and worst == 3


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
