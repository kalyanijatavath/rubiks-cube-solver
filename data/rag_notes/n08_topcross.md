# Stage 4: the top cross

*id: n08_topcross - tag: stage4*

Goal: the four top edges show the top color (yellow) on the top face. Look at the yellow stickers on top: a dot (none), an L-shape (two neighbors), a line (two opposite) or a cross (all four). The algorithm is F R U R' U' F'. For a line, hold it left-to-right. For an L-shape, hold it so the two yellow edges are at the back and on the left. For a dot, hold it any way. After each run, look again and re-align: a dot becomes an L-shape, an L-shape becomes a line and a line becomes the cross, so it takes at most three runs. The algorithm keeps the first two layers intact.
