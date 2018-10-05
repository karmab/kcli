#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""provide random names"""

import random

left = ["astonishing", "happy", "jolly", "dreamy", "sad", "angry", "pensive", "focused", "sleepy", "grave",
        "distracted", "determined", "stoic", "stupefied", "sharp", "agitated", "cocky", "tender", "goofy", "furious",
        "desperate", "hopeful", "compassionate", "silly", "lonely", "condescending", "naughty", "kickass", "drunk",
        "boring", "nostalgic", "ecstatic", "insane", "cranky", "mad", "jovial", "sick", "hungry", "thirsty",
        "elegant", "backstabbing", "clever", "trusting", "loving", "suspicious", "berserk", "high", "romantic",
        "prickly", "evil", "magic"]

right = ["albattani", "almeida", "amazigh", "archimedes", "ardinghelli", "babbage", "bardeen", "bartik", "bbanks",
         "bell", "beyonder", "blackwell", "bohr", "brattain", "briana", "brown", "broza", "bumblefoot", "carson",
         "cell", "citellus", "clapton", "colden", "cuqui", "curie", "darwin", "davinci", "django", "einstein", "elion",
         "engelbart", "euclid", "fermat", "fermi", "feynman", "fiambre", "franklin", "freezer", "galactus", "galileo",
         "goiko", "gohan", "goku", "goldstine", "goodall", "hawking", "heisenberg", "hoover", "hopper", "hypatia",
         "jhendrix", "jmayer", "jones", "kirch", "kendra", "kowalevski", "lalande", "leakey", "lilou", "lovelace",
         "lumiere", "lomax", "macenroe", "manchadinha", "mayer", "mccarthy", "mcclintock", "mclean", "meitner",
         "mestorf", "mikel", "minwii", "morse", "mirzoyan", "newton", "nobel", "pare", "pasteur", "pepenforce",
         "perlman", "picolo", "pike", "poincare", "ptolemy", "ritchie", "rosalind", "sammet", "satriani",
         "selen", "shockley", "sinoussi", "spitzer", "stallman", "tesla", "thompson", "torvalds", "turing", "wilson",
         "wozniak", "wright", "yonath", "rulo", "tudela", "tdurdeen", "korsani", "karmab", "gotrunks",
         "xhamster", "minwii", "djokovic", "federer", "nadal", "sampras", "valadas", "vai", "vegeta"]


def get_random_name(sep='_'):
    """

    :param sep:
    :return:
    """
    r = random.SystemRandom()
    while 1:
        name = '%s%s%s' % (r.choice(left), sep, r.choice(right))
        return name


def random_ip():
    """

    :return:
    """
    ip = ".".join(map(str, (random.randint(0, 255) for _ in range(4))))
    return ip


if __name__ == '__main__':
    print((get_random_name()))
