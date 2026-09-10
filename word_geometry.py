"""Group left-to-right word estimates; no language or icon classification."""


def group_boxes(words, gap_height=1):
    groups = []
    for text, confidence, points in words:
        left = min(p[0] for p in points)
        top = min(p[1] for p in points)
        right = max(p[0] for p in points)
        bottom = max(p[1] for p in points)
        if groups and left - groups[-1][2] <= gap_height * (bottom-top):
            a, b, c, d = groups[-1]
            groups[-1] = (min(a,left), min(b,top), max(c,right), max(d,bottom))
        else:
            groups.append((left,top,right,bottom))
    return groups
