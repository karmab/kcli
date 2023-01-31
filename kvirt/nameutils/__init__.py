#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""provide random names"""

import random

left = ["astonishing", "happy", "jolly", "dreamy", "sad", "angry", "pensive", "focused", "sleepy", "grave",
        "distracted", "determined", "stoic", "stupefied", "sharp", "agitated", "cocky", "tender", "goofy", "furious",
        "desperate", "hopeful", "compassionate", "silly", "lonely", "condescending", "naughty", "kickass", "drunk",
        "boring", "nostalgic", "ecstatic", "insane", "cranky", "mad", "jovial", "sick", "hungry", "thirsty",
        "elegant", "backstabbing", "clever", "trusting", "loving", "suspicious", "berserk", "high", "romantic",
        "prickly", "evil", "magic", "vaccinated", "blader", "starving", "dope", "dingo"]

right = ["albattani", "ablonde", "acid", "adark", "almeida", "alknopfler", "amazigh", "amouranth", "afawx",
         "archimedes", "ardinghelli", "babbage", "bagnaia", "bardeen", "bartik", "benzema", "bingchong", "bbanks",
         "bell", "beyonder", "blackwell", "bohr", "brattain", "briana", "brown", "broza", "bumblefoot", "cantalpino",
         "carson", "cell", "chechik", "clapton", "cobra", "colden", "connors", "conti", "cr7", "curie", "darwin",
         "davinci", "django", "dolores", "einstein", "elion", "engelbart", "euclid", "fermat", "fermi", "feynman",
         "fiambre", "franklin", "freezer", "galactus", "galois", "galileo", "ghowe", "giselle", "goiko", "gogetta",
         "gohan", "goku", "goldstine", "goodall", "govan", "griezmann", "hawking", "heisenberg", "hoover", "hopper",
         "hypatia", "idir", "jhendrix", "jmayer", "jonas", "jones", "kirch", "kendra", "kheiron", "kowalevski",
         "krilin", "kylee", "lalande", "leakey", "lendl", "lilou", "lomax", "lovelace", "lumiere", "lomax",
         "macenroe", "mwilde", "marquez", "chavero", "matoub", "mayer", "mbappe", "mccarthy", "mcclintock", "mclean",
         "meitner", "messi", "mestorf", "mikel", "vaiana", "morse", "nilibrosh", "newton", "nobel", "norinradd",
         "obama", "pare", "jparrill", "pasteur", "pepenforce", "perlman", "picolo", "pike", "pinkman", "poincare",
         "pparker", "productionready", "ptolemy", "quartararo", "rosalind", "rgemma", "reinhardt", "rossi", "sammet",
         "sandler", "satriani", "selen", "shockley", "sinoussi", "silversurfer", "snowwhites", "socarrat", "spidey",
         "spitzer", "stallman", "tesla", "timesburg", "thompson", "torvalds", "turing", "wilson", "wozniak", "wright",
         "yonath", "rulo", "tudela", "tylerdurdeen", "korsani", "karmab", "gotrunks", "xhamster", "minwii", "djokovic",
         "federer", "nadal", "sampras", "tgb", "valadas", "vai", "vegeta", "ivanisevic", "muster", "agassi",
         "targaryen", "lannister", "safin", "stark", "jsnow", "superduper", "telecaster", "tommyemmanuel", "thor",
         "vario", "walterwhite", "yuval", "5g", "5guys", "180k", "merletravis", "chetatkins", "fusilijerri",
         "joerobinson", "mog", "unity", "savannah", "soul", "mm93", "vcossart", "gruson", "patarin", "hichem", "regis",
         "elisa", "limu", "brais", "duncanmcleod"]


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
