# Stage 5: orienting the top corners

*id: n09_orient - tag: stage5*

Goal: the whole top face is yellow. Count the corners that already show yellow on top and use the Sune algorithm R U R' U R U2 R'. With exactly one yellow corner, turn the top layer until it is at the front-left and run Sune. With none, turn the top layer until the front-left corner's yellow sticker faces left, then run Sune; you will then have exactly one. With two, turn the top layer until the front-left corner is not yellow on top and its yellow sticker faces the front, then run Sune; you will then have exactly one. Repeat until all four are yellow; this needs at most three runs. Sune keeps the first two layers and the top cross intact.
