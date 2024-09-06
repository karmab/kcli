#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random

left = ["astonishing", "happy", "jolly", "dreamy", "sad", "angry", "pensive", "focused", "sleepy", "grave",
        "distracted", "determined", "stoic", "stupefied", "sharp", "agitated", "cocky", "tender", "goofy", "furious",
        "desperate", "hopeful", "compassionate", "silly", "lonely", "condescending", "naughty", "kickass", "drunk",
        "boring", "nostalgic", "ecstatic", "insane", "cranky", "mad", "jovial", "sick", "hungry", "thirsty",
        "elegant", "backstabbing", "clever", "trusting", "loving", "suspicious", "berserk", "high", "romantic",
        "prickly", "evil", "magic", "vaccinated", "blader", "starving", "dope", "dingo", "summer", "tolai", "sweaty",
        "fired"]

right = ["albattani", "ablonde", "acid", "adark", "adebarre", "almeida", "alcaraz", "acosta", "alknopfler", "amazigh",
         "amouranth", "afawx", "archimedes", "ardinghelli", "babbage", "bagnaia", "bardeen", "bartik", "bcoco",
         "benzema", "bingchong", "bbanks", "bell", "beyonder", "blackwell", "bohr", "brattain", "briana", "brown",
         "bumblefoot", "cantalpino", "carson", "cell", "chechik", "clapton", "cobra", "colden", "connors", "conti",
         "cr7", "curie", "darwin", "davinci", "django", "dolores", "einstein", "elion", "engelbart", "euclid", "fermat",
         "fermi", "feynman", "franklin", "freezer", "galactus", "galois", "galileo", "ghowe", "giselle", "gogetta",
         "gohan", "goku", "goldstine", "goodall", "govan", "griezmann", "hawking", "heisenberg",
         "hoover", "hopper", "hypatia", "idir", "jhendrix", "jmayer", "jmiller", "jonas", "jones", "kirch", "kendra",
         "kheiron", "kowalevski", "krilin", "kylee", "lalande", "leakey", "lendl", "lilou", "lomax", "lovelace",
         "lumiere", "lomax", "macenroe", "mwilde", "marquez", "martin",
         "chavero", "matoub", "jmayer", "mbappe", "mccarthy", "mcclintock", "mclean", "meitner", "messi", "mestorf",
         "mikel", "vaiana", "stevemorse", "nilibrosh", "newton", "nobel", "nuno", "norinradd", "obama", "pare",
         "pasteur", "perlman", "picolo", "pike", "pinkman", "poincare", "pparker", "productionready", "ptolemy",
         "quartararo", "rosalind", "rgemma", "reinhardt", "rossi", "sammet", "sandler", "satriani", "selen",
         "shockley", "shyla", "sinoussi", "silversurfer", "snowwhites", "socarrat", "spidey", "spitzer", "stallman",
         "stochelo", "syren", "tesla", "thompson", "torvalds", "turing", "wilson", "wozniak", "wright",
         "yonath", "tudela", "tylerdurdeen", "korsani", "karmab", "gotrunks", "xhamster", "djokovic", "federer",
         "nadal", "sampras", "valadas", "vai", "vegeta", "ivanisevic", "muster", "agassi", "targaryen", "lannister",
         "safin", "stark", "jsnow", "sinner", "superduper", "tommyemmanuel", "thor", "mario", "walterwhite", "yuval",
         "5g", "5guys", "200k", "merletravis", "chetatkins", "fusilijerri", "joerobinson", "mog", "unity", "savannah",
         "soul", "mm93", "vcossart", "gruson", "patarin", "hichem", "regis", "elisa", "brais", "duncanmcleod", "mizu",
         "makio", "lois", "fender", "marshall", "stratocaster", "telecaster", "tenshinhan", "jmartin", "dalridge",
         "paul", "john", "mellen", "johnwick", "stef", "sperez", "sweetstance", "kindgrind", "fishbrain", "topsoul",
         "alleyoop", "mancuso", "asato", "atimmons", "interstellar", "shawshank", "samourai", "neo", "morfeus"]


def get_random_name(sep='-'):
    r = random.SystemRandom()
    while 1:
        name = '%s%s%s' % (r.choice(left), sep, r.choice(right))
        return name


def random_ip():
    ip = ".".join(map(str, (random.randint(0, 255) for _ in range(4))))
    return ip


if __name__ == '__main__':
    print(get_random_name())
