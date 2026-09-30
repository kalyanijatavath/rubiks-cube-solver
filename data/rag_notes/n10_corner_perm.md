# Stage 6: positioning the top corners

*id: n10_corner_perm - tag: stage6*

Goal: every top corner is in its correct position, meaning its two side colors match the neighboring centers. Find a corner that is already correct, hold the cube so it is at the front-left, and run R' F R' B2 R F' R' B2 R2. This moves the other three corners in a cycle, so three runs in a row return you to the start; at most two runs are ever needed from one position. The algorithm keeps the top face yellow. If two corners look correct and the other two are swapped, turn the top layer by a quarter turn and look again for a single correct corner, because that swapped layout cannot be fixed directly. If no corner is correct after any top-layer turn, run the algorithm once from any angle and look again. When done, turn the top layer until the corners match the side centers.
