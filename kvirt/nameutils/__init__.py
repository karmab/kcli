#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""provide random names"""

import random

left = ["astonishing", "happy", "jolly", "dreamy", "sad", "angry", "pensive", "focused", "sleepy", "grave", "distracted", "determined", "stoic", "stupefied", "sharp", "agitated", "cocky", "tender", "goofy", "furious", "desperate", "hopeful", "compassionate", "silly", "lonely", "condescending", "naughty", "kickass", "drunk", "boring", "nostalgic", "ecstatic", "insane", "cranky", "mad", "jovial", "sick", "hungry", "thirsty", "elegant", "backstabbing", "clever", "trusting", "loving", "suspicious", "berserk", "high", "romantic", "prickly", "evil", "magic"]

right = ["albattani", "almeida", "amazigh", "archimedes", "ardinghelli", "babbage", "bardeen", "bartik", "bell", "blackwell", "bohr", "brattain", "briana", "brown", "bumblefoot", "carson", "colden", "cuqui", "curie", "darwin", "davinci", "django", "einstein", "elion", "engelbart", "euclid", "fermat", "fermi", "feynman", "franklin", "galileo", "goiko", "goldstine", "goodall", "hawking", "heisenberg", "hoover", "hopper", "hypatia", "jhendrix", "jmayer", "jones", "kirch", "kendra", "kowalevski", "lalande", "leakey", "lovelace", "lumiere", "manchadinha", "mayer", "mccarthy", "mcclintock", "mclean", "meitner", "mestorf", "mikel", "morse", "newton", "nobel", "pare", "pasteur", "perlman", "pike", "poincare", "ptolemy", "ritchie", "rosalind", "sammet", "selen", "shockley", "sinoussi", "stallman", "tesla", "thompson", "torvalds", "turing", "wilson", "wozniak", "wright", "yonath", "rulo", "tudela", "tdurdeen", "korsani", "karmab", "gotrunks", "xhamster", "minwii", "federer", "valadas", "spitzer"]


def get_random_name(sep='_'):
    r = random.SystemRandom()
    while 1:
        name = '%s%s%s' % (r.choice(left), sep, r.choice(right))
        return name

if __name__ == '__main__':
    print get_random_name()
