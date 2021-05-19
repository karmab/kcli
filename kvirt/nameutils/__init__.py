#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""provide random names"""

import random

left = ["astonishing", "happy", "jolly", "dreamy", "sad", "angry", "pensive", "focused", "sleepy", "grave",
        "distracted", "determined", "stoic", "stupefied", "sharp", "agitated", "cocky", "tender", "goofy", "furious",
        "desperate", "hopeful", "compassionate", "silly", "lonely", "condescending", "naughty", "kickass", "drunk",
        "boring", "nostalgic", "ecstatic", "insane", "cranky", "mad", "jovial", "sick", "hungry", "thirsty",
        "elegant", "backstabbing", "clever", "trusting", "loving", "suspicious", "berserk", "high", "romantic",
        "prickly", "evil", "magic", "vaccinated"]

right = ["albattani", "almeida", "alknopfler", "amazigh", "apfelb", "archimedes", "ardinghelli", "babbage", "bardeen",
         "bartik", "bingchong", "bbanks", "bell", "beyonder", "blackwell", "bohr", "brattain", "briana", "brown",
         "broza", "bumblefoot", "cantalpino", "carson", "cell", "chechik", "citellus", "clapton", "cobra", "colden",
         "cr7", "cuqui", "curie", "darwin", "davinci", "django", "einstein", "elion", "engelbart", "euclid", "fermat",
         "fermi", "feynman", "fiambre", "franklin", "freezer", "galactus", "galois", "galileo", "goiko", "gohan",
         "goku", "goldstine", "goodall", "govan", "griezmann", "hawking", "heisenberg", "hoover", "hopper", "hypatia",
         "jhendrix", "jmayer", "jonas", "jones", "kirch", "kendra", "kowalevski", "krilin", "lalande", "leakey",
         "lendl", "lilou", "lomax", "lovelace", "lumiere", "lomax", "macenroe", "manchadinha", "mayer",
         "mbappe", "mccarthy", "mcclintock", "mclean", "meitner", "messi", "mestorf", "mikel", "minwii", "moana",
         "morse", "mirzoyan", "newton", "nobel", "norinradd", "pare", "jparrill", "pasteur", "pepenforce", "perlman",
         "picolo", "pike", "pinkman", "poincare", "pparker", "productionready", "ptolemy", "ritchie", "rosalind",
         "reinhardt", "sammet", "satriani", "selen", "shockley", "sinoussi", "silversurfer", "snowwhites", "socarrat",
         "spitzer", "stallman", "tesla", "timesburg", "thompson", "torvalds", "turing", "wilson", "wozniak", "wright",
         "yonath", "rulo", "tudela", "tdurdeen", "korsani", "karmab", "gotrunks", "xhamster", "minwii", "djokovic",
         "federer", "nadal", "sampras", "tgb", "valadas", "vai", "vegeta", "ivanisevic", "muster", "agassi",
         "targaryen", "lannister", "safin", "stark", "jsnow", "superduper", "tripleo", "vario", "walterwhite",
         "yolandarock", "yuval", "5guys"]


def get_random_name(sep='-'):
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
    print(get_random_name())
