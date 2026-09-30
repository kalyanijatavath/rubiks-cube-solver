"""Writes the RAG corpus (original teaching notes) and the retrieval eval set, then
measures a plain TF-IDF retrieval baseline. Every algorithm quoted here is verified by
test_algorithms.py - keep them in sync."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import os

NOTES = [
    ("n01_notation", "Move notation", "notation",
     "Each letter names a face: U is the top (up) face, D bottom (down), F front, B back, L left "
     "and R right. A letter on its own means a quarter turn clockwise, as if you were looking straight "
     "at that face. A prime mark, as in R', means a quarter turn counterclockwise. A 2, as in R2, means "
     "a half turn; direction does not matter for a half turn. Read a sequence from left to right and "
     "finish each move before starting the next. The letters always refer to faces of the cube, never to "
     "your left or right hand."),
    ("n02_anatomy", "Pieces of the cube", "basics",
     "A 3x3 cube has 6 centers, 12 edges and 8 corners, which together carry 54 stickers. A center has "
     "one sticker, an edge two, a corner three. The centers never move relative to each other, so they "
     "decide which color belongs on which face. Every color appears exactly 9 times. Pieces cannot be "
     "separated by legal turns, which is why some sticker layouts (one flipped edge, one twisted corner, "
     "two swapped pieces) can never occur on a cube that is merely scrambled."),
    ("n03_frame", "How to hold the cube while learning", "basics",
     "This tutor assumes you hold the cube with the color of your first layer (white in these notes) on "
     "the bottom face and the opposite color (yellow) on top. Pick any front face and keep it consistent "
     "within a stage. When a step says 'front-left' or 'at the back', it refers to how you hold the cube at "
     "that moment; you are allowed to turn the whole cube in your hands between algorithms to bring a "
     "piece to the position the step asks for."),
    ("n04_overview", "The seven stages and how progress is checked", "method",
     "The beginner method has seven stages: (1) the bottom cross, (2) the bottom corners, (3) the middle "
     "layer edges, (4) the top cross, (5) orienting the top corners, (6) positioning the top corners and "
     "(7) positioning the top edges. Stages 1-2 complete the first layer; stage 3 completes the first two "
     "layers. The tutor tracks progress with the names cross, first_layer, first_two_layers, top_cross, "
     "top_face and solved. A stage counts as done only when every sticker of that stage matches its "
     "face color, so a bottom cross with wrong side colors does not count as a cross."),
    ("n05_cross", "Stage 1: the bottom cross", "stage1",
     "Goal: the four bottom edges each have the bottom color on the bottom face and their other sticker "
     "matches the center of the side face they touch. Matching the bottom color alone is not enough. "
     "Work on one edge at a time: find an edge that has the bottom color, turn the top layer until its "
     "other color sits above the matching side center, then turn that side face a half turn to drop the "
     "edge into place. Check all four side stickers against the centers at the end."),
    ("n06_corners", "Stage 2: the bottom corners", "stage2",
     "Goal: all four bottom corners are in place with the bottom color facing down and their two side "
     "colors matching the neighboring centers. Find a corner in the top layer that has the bottom color. "
     "Turn the top layer until the corner sits directly above the slot it belongs in, and hold the cube so "
     "that slot is at the front-right. Repeat the four-move trigger R U R' U' until the corner drops into "
     "the slot with the bottom color facing down; this takes between one and five repeats, and six repeats "
     "bring you back to where you started. If a corner is in the bottom layer but in the wrong place or "
     "twisted, run the trigger once to lift it into the top layer and then place it as above."),
    ("n07_middle", "Stage 3: the middle layer edges", "stage3",
     "Goal: the four middle-layer edges are in place, finishing the first two layers. Look for an edge in "
     "the top layer that has no top-color (yellow) sticker. Turn the top layer until the sticker on the "
     "front face matches the front center. If the sticker on top matches the right center, run "
     "U R U' R' U' F' U F. If it matches the left center, run U' L' U L U F U' F'. Both algorithms leave "
     "the bottom layer solved once they finish. If a middle-layer edge is stuck in the wrong slot, run either algorithm "
     "with that edge in the working slot to pop it out into the top layer, then insert it properly."),
    ("n08_topcross", "Stage 4: the top cross", "stage4",
     "Goal: the four top edges show the top color (yellow) on the top face. Look at the yellow stickers on "
     "top: a dot (none), an L-shape (two neighbors), a line (two opposite) or a cross (all four). The "
     "algorithm is F R U R' U' F'. For a line, hold it left-to-right. For an L-shape, hold it so the two "
     "yellow edges are at the back and on the left. For a dot, hold it any way. After each run, look "
     "again and re-align: a dot becomes an L-shape, an L-shape becomes a line and a line becomes the "
     "cross, so it takes at most three runs. The algorithm keeps the first two layers intact."),
    ("n09_orient", "Stage 5: orienting the top corners", "stage5",
     "Goal: the whole top face is yellow. Count the corners that already show yellow on top and use the "
     "Sune algorithm R U R' U R U2 R'. With exactly one yellow corner, turn the top layer until it is at "
     "the front-left and run Sune. With none, turn the top layer until the front-left corner's yellow "
     "sticker faces left, then run Sune; you will then have exactly one. With two, turn the top layer "
     "until the front-left corner is not yellow on top and its yellow sticker faces the front, then run "
     "Sune; you will then have exactly one. Repeat until all four are yellow; this needs at most three "
     "runs. Sune keeps the first two layers and the top cross intact."),
    ("n10_corner_perm", "Stage 6: positioning the top corners", "stage6",
     "Goal: every top corner is in its correct position, meaning its two side colors match the "
     "neighboring centers. Find a corner that is already correct, hold the cube so it is at the "
     "front-left, and run R' F R' B2 R F' R' B2 R2. This moves the other three corners in a cycle, so "
     "three runs in a row return you to the start; at most two runs are ever needed from one position. "
     "The algorithm keeps the top face yellow. If two corners look correct and the other two are swapped, "
     "turn the top layer by a quarter turn and look again for a single correct corner, because that "
     "swapped layout cannot be fixed directly. If no corner is correct after any top-layer turn, run the "
     "algorithm once from any angle and look again. When done, turn the top layer until the corners "
     "match the side centers."),
    ("n11_edge_perm", "Stage 7: positioning the top edges", "stage7",
     "Goal: the cube is solved. With the top corners correct, find a top edge that is already in place and "
     "hold the cube so it is at the back. Run R U' R U R U R U' R' U' R2. This cycles the other three "
     "top edges and leaves the corners alone. If the edges are cycled the wrong way, run it once more; "
     "three runs return you to the start, so at most two runs are needed. If no top edge is correct, run "
     "the algorithm once from any angle and look again."),
    ("n12_mistakes", "Common mistakes and how to recover", "troubleshooting",
     "The most common mistakes are turning a face the wrong direction (R instead of R'), turning it by the "
     "wrong amount (R instead of R2) and turning the wrong face. To recover, undo the last turn with the "
     "opposite move: the inverse of R is R', of R' is R, and of R2 is R2. Then continue from where you "
     "were. If you are unsure what you did, show the cube to the camera again; the tutor compares the "
     "before and after states and identifies the move you made. Another frequent problem is holding the "
     "cube differently between the algorithm's start and end, which makes 'front-left' mean something else."),
    ("n13_scan", "Scanning tips and misread colors", "vision",
     "Scan in even light and avoid glare on the stickers. The pairs most often confused are white and "
     "yellow under warm light, and orange and red on worn stickers. Hold each face flat and centered in the "
     "overlay, in the order the tutor asks. The tutor reads every sticker by comparing it to the six center "
     "stickers, because centers never move, and checks that each color appears exactly nine times. If a "
     "count is wrong, rescan that face or correct the sticker by hand in the interface."),
    ("n14_invalid", "Invalid or unsolvable states", "troubleshooting",
     "A scan is invalid if any color does not appear exactly nine times, or if it contains a piece that "
     "does not exist on a real cube, such as an edge with two stickers of the same color or a corner "
     "with a color combination that no corner has. Even a valid-looking scan can be "
     "impossible on a genuinely scrambled cube: a single flipped edge, a single twisted corner, or exactly "
     "two swapped pieces cannot be reached with legal turns. If the solver rejects the state, the cause is "
     "almost always a misread sticker; rescan. If the cube was taken apart and reassembled, it may be "
     "unsolvable without being taken apart again."),
    ("n15_technique", "Turning technique and speed", "technique",
     "Learn each algorithm slowly and smoothly before trying to go fast; speed comes from consistency, "
     "not from rushing. Keep the cube in the same hand position, use the index and middle fingers to flick "
     "the top layer, and avoid regripping mid-algorithm. Say the move names quietly while practicing. "
     "Do not stop in the middle of an algorithm: if you lose your place, undo back to the start of the "
     "algorithm or ask the tutor to check the cube."),
    ("n16_solved", "What a solved cube looks like", "basics",
     "A cube is solved when every face shows a single color, each of the six colors on exactly one face. "
     "Because the centers never move, a solved cube can be held in any orientation. If only the top layer "
     "looks off after the last stage, turn the top layer until its sides match the centers. If a face is "
     "uniform but a neighboring face is not, one or more layers are offset and need a turn, not an algorithm."),
]

QA = [  # (question, gold_note_id)
    ("What does a prime mark mean in R'?", "n01_notation"),
    ("What does the 2 mean in a move like U2?", "n01_notation"),
    ("Are the letters in an algorithm about my left and right hand?", "n01_notation"),
    ("How many edges, corners and centers does a cube have?", "n02_anatomy"),
    ("Why do the centers decide the color of each face?", "n02_anatomy"),
    ("Why can't I flip just one edge?", "n02_anatomy"),
    ("Which color should be on the bottom while I learn?", "n03_frame"),
    ("How should I hold the cube during a step?", "n03_frame"),
    ("What are the stages of the beginner method?", "n04_overview"),
    ("How does the tutor decide that the first two layers are finished?", "n04_overview"),
    ("Does a bottom cross count if the side colors don't match?", "n04_overview"),
    ("How do I know my white cross is right?", "n05_cross"),
    ("How do I bring a white edge down to the bottom layer?", "n05_cross"),
    ("What algorithm places the bottom corners?", "n06_corners"),
    ("How many times do I repeat R U R' U' for a corner?", "n06_corners"),
    ("A corner is stuck in the bottom layer the wrong way. What do I do?", "n06_corners"),
    ("How do I insert a middle layer edge to the right?", "n07_middle"),
    ("Which algorithm inserts an edge on the left side?", "n07_middle"),
    ("An edge is in the wrong middle slot. How do I fix it?", "n07_middle"),
    ("What algorithm makes the yellow cross?", "n08_topcross"),
    ("How do I hold an L-shape before running F R U R' U' F'?", "n08_topcross"),
    ("How many times might I need the top cross algorithm for a dot?", "n08_topcross"),
    ("What is Sune and when do I use it?", "n09_orient"),
    ("I have no yellow corners on top. How do I start?", "n09_orient"),
    ("Which corner do I hold at front-left when I have exactly one yellow corner?", "n09_orient"),
    ("How do I position the top corners?", "n10_corner_perm"),
    ("What if two corners are correct and the other two are swapped?", "n10_corner_perm"),
    ("Where do I hold the correct corner before running the corner algorithm?", "n10_corner_perm"),
    ("How do I finish the last step and permute the top edges?", "n11_edge_perm"),
    ("The top edges are cycling the wrong way after one run. What now?", "n11_edge_perm"),
    ("I turned a face the wrong way. How do I undo it?", "n12_mistakes"),
    ("How does the tutor figure out which move I made?", "n12_mistakes"),
    ("Why are white and yellow confused when I scan?", "n13_scan"),
    ("How does the scanner decide a sticker's color?", "n13_scan"),
    ("The solver says my cube is invalid. Why?", "n14_invalid"),
    ("Can a scrambled cube have exactly two swapped pieces?", "n14_invalid"),
    ("How can I turn faster without mistakes?", "n15_technique"),
    ("I lost my place halfway through an algorithm.", "n15_technique"),
    ("What does a solved cube look like?", "n16_solved"),
    ("All faces look uniform except one neighboring face. What is wrong?", "n16_solved"),
]


def main():
    os.makedirs("data/rag_notes", exist_ok=True)
    with open("data/rag_corpus.jsonl", "w") as jf:
        for nid, title, tag, text in NOTES:
            jf.write(json.dumps({"id": nid, "title": title, "tag": tag, "text": text}) + "\n")
            with open(f"data/rag_notes/{nid}.md", "w") as f:
                f.write(f"# {title}\n\n*id: {nid} - tag: {tag}*\n\n{text}\n")
    with open("data/rag_eval.jsonl", "w") as f:
        for i, (q, gold) in enumerate(QA):
            f.write(json.dumps({"id": f"q{i:03d}", "question": q, "gold_note_id": gold}) + "\n")

    # ----------------------------------------------------- TF-IDF baseline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    docs = [f"{t} {x}" for _, t, _, x in NOTES]
    ids = [n[0] for n in NOTES]
    vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english")
    D = vec.fit_transform(docs)
    hit1 = hit3 = 0
    misses = []
    for q, gold in QA:
        sims = cosine_similarity(vec.transform([q]), D)[0]
        order = [ids[i] for i in sims.argsort()[::-1]]
        hit1 += order[0] == gold
        hit3 += gold in order[:3]
        if order[0] != gold:
            misses.append({"question": q, "gold": gold, "got": order[0]})
    res = {"n_notes": len(NOTES), "n_questions": len(QA),
           "tfidf_hit@1": round(hit1 / len(QA), 3), "tfidf_hit@3": round(hit3 / len(QA), 3),
           "top1_misses": misses}
    json.dump(res, open("data/rag_baseline_results.json", "w"), indent=2)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
