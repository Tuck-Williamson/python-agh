"""
humanhash: Human-readable representations of digests.

The simplest ways to use this module are the :func:`humanize` and :func:`uuid`
functions. For tighter control over the output, see :class:`HumanHasher`.
"""

import operator
import uuid as uuidlib
from functools import reduce

DEFAULT_WORDLIST = (
    "ack",
    "alabama",
    "alanine",
    "alaska",
    "alpha",
    "angel",
    "apart",
    "april",
    "arizona",
    "arkansas",
    "artist",
    "asparagus",
    "aspen",
    "august",
    "autumn",
    "avocado",
    "bacon",
    "bakerloo",
    "batman",
    "beer",
    "berlin",
    "beryllium",
    "black",
    "blossom",
    "blue",
    "bluebird",
    "bravo",
    "bulldog",
    "burger",
    "butter",
    "california",
    "carbon",
    "cardinal",
    "carolina",
    "carpet",
    "cat",
    "ceiling",
    "charlie",
    "chicken",
    "coffee",
    "cola",
    "cold",
    "colorado",
    "comet",
    "connecticut",
    "crazy",
    "cup",
    "dakota",
    "december",
    "delaware",
    "delta",
    "diet",
    "don",
    "double",
    "early",
    "earth",
    "east",
    "echo",
    "edward",
    "eight",
    "eighteen",
    "eleven",
    "emma",
    "enemy",
    "equal",
    "failed",
    "fanta",
    "fifteen",
    "fillet",
    "finch",
    "fish",
    "five",
    "fix",
    "floor",
    "florida",
    "football",
    "four",
    "fourteen",
    "foxtrot",
    "freddie",
    "friend",
    "fruit",
    "gee",
    "georgia",
    "glucose",
    "golf",
    "green",
    "grey",
    "hamper",
    "happy",
    "harry",
    "hawaii",
    "helium",
    "high",
    "hot",
    "hotel",
    "hydrogen",
    "idaho",
    "illinois",
    "india",
    "indigo",
    "ink",
    "iowa",
    "island",
    "item",
    "jersey",
    "jig",
    "johnny",
    "juliet",
    "july",
    "jupiter",
    "kansas",
    "kentucky",
    "kilo",
    "king",
    "kitten",
    "lactose",
    "lake",
    "lamp",
    "lemon",
    "leopard",
    "lima",
    "lion",
    "lithium",
    "london",
    "louisiana",
    "low",
    "magazine",
    "magnesium",
    "maine",
    "mango",
    "march",
    "mars",
    "maryland",
    "massachusetts",
    "may",
    "mexico",
    "michigan",
    "mike",
    "minnesota",
    "mirror",
    "mississippi",
    "missouri",
    "mobile",
    "mockingbird",
    "monkey",
    "montana",
    "moon",
    "mountain",
    "muppet",
    "music",
    "nebraska",
    "neptune",
    "network",
    "nevada",
    "nine",
    "nineteen",
    "nitrogen",
    "north",
    "november",
    "nuts",
    "october",
    "ohio",
    "oklahoma",
    "one",
    "orange",
    "oranges",
    "oregon",
    "oscar",
    "oven",
    "oxygen",
    "papa",
    "paris",
    "pasta",
    "pennsylvania",
    "pip",
    "pizza",
    "pluto",
    "potato",
    "princess",
    "purple",
    "quebec",
    "queen",
    "quiet",
    "red",
    "river",
    "robert",
    "robin",
    "romeo",
    "rugby",
    "sad",
    "salami",
    "saturn",
    "september",
    "seven",
    "seventeen",
    "shade",
    "sierra",
    "single",
    "sink",
    "six",
    "sixteen",
    "skylark",
    "snake",
    "social",
    "sodium",
    "solar",
    "south",
    "spaghetti",
    "speaker",
    "spring",
    "stairway",
    "steak",
    "stream",
    "summer",
    "sweet",
    "table",
    "tango",
    "ten",
    "tennessee",
    "tennis",
    "texas",
    "thirteen",
    "three",
    "timing",
    "triple",
    "twelve",
    "twenty",
    "two",
    "uncle",
    "undress",
    "uniform",
    "uranus",
    "utah",
    "vegan",
    "venus",
    "vermont",
    "victor",
    "video",
    "violet",
    "virginia",
    "washington",
    "west",
    "whiskey",
    "white",
    "william",
    "winner",
    "winter",
    "wisconsin",
    "wolfram",
    "wyoming",
    "xray",
    "yankee",
    "yellow",
    "zebra",
    "zulu",
)

DEFAULT_WORDLIST = (
    "aged",
    "acre",  # "acorn", "acts",
    "afar",
    "agent",  #
    "affix",
    "agile",
    # "aging", "ahead", #"agony", "aids",
    "aim",
    "alike",  # "alarm", "alive",
    # "alone", "aloft",
    "aloha",
    "amend",
    "ample",
    "angel",  # "amuse", "anger",
    "apple",
    "apron",  # "april", "awake",
    "area",
    "argue",  # "army", "armed",
    "armor",
    "art",  # "arson", "atlas",
    # "atom", "avoid", #
    "avert",
    "bacon",
    "boots",
    "book",  # "basil", "bust",
    "baker",
    "bunch",  # "balmy", "broke",
    "barn",
    "baton",  #
    "both",
    "blade",
    "blank",
    "blog",  # "blast", "blend",
    "blimp",
    "blurt",  # "blob", "bully",
    # "boned", "broad", #"bunny", "bribe",
    "bring",
    "civil",  # "broil", "case",
    "city",
    "come",  # "claim", "canal",
    "candy",
    "card",  # "chief", "crazy",
    "carol",
    "crop",  # "carry", "cedar",
    "crown",
    "clay",  # "cost", "chump",
    "comic",
    "cold",  #
    "civic",
    "clamp",
    "clip",
    "clasp",  #
    "class",
    "clear",
    # "cleft", "cling", #"clerk", "cover",
    # "craft", "crank", #"cramp", "crisp",
    "crust",
    "cycle",  # "cupid", "deaf",
    "data",
    "draw",  #
    "deal",
    "duke",
    # "doing", "drama", #"dent", "dried",
    "down",
    "debug",  # "debt", "decaf",
    "decal",
    "drive",  # "decor", "dimly",
    # "donor", "drank", #
    "ditch",
    "dress",
    "drift",
    "dust",  # "drill", "equal",
    "early",
    "east",  # "earth", "eaten",
    "edge",
    "even",  # "ebay", "evoke",
    "essay",
    "elbow",  # "eel", "elder",
    "elk",
    "elude",  #
    "elm",
    "elves",
    "email",
    "empty",  # "emit", "emu",
    "enter",
    "erase",  # "envoy", "error",
    # "erupt", "evict", #"evade", "evil",
    "fable",
    "food",  # "fact", "fall",
    "false",
    "fox",  #
    "fancy",
    "femur",
    "found",
    "fetal",  # "ferry", "fetch",
    # "fever", "film", #"fifth", "fled",
    "final",
    "flip",  # "five", "fling",
    "flint",
    "flyer",  # "flirt", "foam",
    # "frail", "fresh", #"from", "fruit",
    "front",
    "gas",  #
    "frost",
    "going",
    # "goal", "gave", #
    "game",
    "grew",
    "genre",
    "glass",  # "gift", "given",
    "giver",
    "golf",  #
    "glad",
    "good",
    # "grab", "grant", #"green", "grasp",
    "grass",
    "grill",  # "grid", "habit",
    "help",
    "halt",  # "hull", "happy",
    "harm",
    "hasty",  #
    "hug",
    "hatch",
    # "hate", "hazel", #"haven", "herbs",
    "hers",
    "hunt",  # "human", "hump",
    "hung",
    "hurt",  # "hurry", "issue",
    # "icing", "igloo", #
    "icon",
    "image",
    "ion",
    "item",  # "iron", "ivory",
    "ivy",
    "jam",  # "job", "juice",
    "july",
    "jolt",  # "jet", "judge",
    "jump",
    "jury",  # "junky", "keep",
    "kick",
    "kilt",  # "kept", "king",
    # "kitty", "knelt", #
    "knee",
    "koala",
    # "ladle", "lure", #"late", "lake",
    "lunch",
    "level",  # "land", "large",
    "last",
    "left",  # "latch", "legal",
    "line",
    "life",  #
    "liver",
    "lilac",
    "lily",
    "lunar",  # "limb", "music",
    "maker",
    "many",  # "mold", "mango",
    "manor",
    "march",  # "move", "mardi",
    # "marry", "mouth", #
    "match",
    "most",
    "motor",
    "mulch",  # "mount", "mule",
    "mumbo",
    "niece",  # "mural", "nail",
    "name",
    "near",  # "navy", "net",
    # "nerd", "ninth", #
    "next",
    "oak",
    "oat",
    "oil",  # "ocean", "old",
    "olive",
    "only",  # "onion", "oval",
    "open",
    "opt",  #
    "opera",
    "outer",
    # "ounce", "pagan", #"push", "poker",
    "palm",
    "punch",  # "point", "pants",
    "paper",
    "party",  # "press", "pasta",
    # "patch", "power", #
    "photo",
    "poem",
    "puppy",
    "petal",  # "perm", "petri",
    "plank",
    "plus",  #
    "plant",
    "plot",
    # "pull", "prank", #"polar", "print",
    "prism",
    "props",  # "proof", "pulp",
    "pupil",
    "query",  # "quake", "quiet",
    "quill",
    "raft",  # "quilt", "risk",
    "radar",
    "rule",  # "radio", "ramp",
    "range",
    "robin",  # "rant", "react",
    "roman",
    "recap",  # "reply", "relax",
    "rope",
    "rigor",  # "rerun", "ritzy",
    "river",
    "size",  # "stole", "said",
    # "send", "slam", #
    "salt",
    "silk",
    "same",
    "speed",  # "steam", "spray",
    # "scale", "score", #
    "scan",
    "scrap",
    "scope",
    "squad",  # "scold", "scorn",
    # "self", "serve", #
    "ship",
    "seven",
    "share",
    "shirt",  #
    "shell",
    "shrug",
    # "siren", "slang", #"skirt", "slept",
    "slurp",
    "swing",  # "small", "smirk",
    # "snap", "snarl", #
    "snare",
    "snort",
    "speak",
    "spill",  # "spent", "sport",
    "stage",
    "stamp",  # "stop", "stand",
    "sting",
    "start",  # "stark", "stir",
    "storm",
    "those",  # "swirl", "tall",
    "talon",
    "think",  # "tamer", "taper",
    # "taps", "taste", #
    "trade",
    "tint",
    # "theft", "train", #"theme", "trap",
    "tweet",
    "try",  #
    "thumb",
    "tidal",
    "tiger",
    "track",  # "tilt", "trend",
    "trial",
    "tulip",  # "trunk", "tutor",
    # "uncle", "unit", #"uncut", "unify",
    "union",
    "upper",  #
    "upon",
    "urban",
    # "used", "utter", #"user", "value",
    "vapor",
    "venue",  # "vegan", "virus",
    "vest",
    "voice",  #
    "video",
    "viral",
    "visor",
    "volt",  # "vocal", "voter",
    "wheat",
    "wager",  #
    "wafer",
    "wish",
    "wagon",
    "wind",  # "walk", "wasp",
    # "watch", "wife", #
    "water",
    "whole",
    # "widen", "womb", #"wilt", "wing",
    "word",
    "wolf",  # "worry", "work",
    "woven",
    "xerox",  # "wrist", "yummy",
    "yard",
    "yeast",  # "year", "yelp",
    "yield",
    "yoga",  # "yodel", "zebra",
    "zero",
    "zippy",  # "zesty", "zone",
)


class HumanHasher:
    """
    Transforms hex digests to human-readable strings.

    The format of these strings will look something like:
    `victor-bacon-zulu-lima`. The output is obtained by compressing the input
    digest to a fixed number of bytes, then mapping those bytes to one of 256
    words. A default wordlist is provided, but you can override this if you
    prefer.

    As long as you use the same wordlist, the output will be consistent (i.e.
    the same digest will always render the same representation).
    """

    def __init__(self, wordlist=DEFAULT_WORDLIST):
        if len(wordlist) != 256:
            raise ValueError("Wordlist must have exactly 256 items")
        self.wordlist = wordlist

    def humanize(self, hexdigest, words=4, separator="-"):
        """
        Humanize a given hexadecimal digest.

        Change the number of words output by specifying `words`. Change the
        word separator with `separator`.

            >>> digest = '60ad8d0d871b6095808297'
            >>> HumanHasher().humanize(digest)
            'sodium-magnesium-nineteen-hydrogen'
        """

        # Gets a list of byte values between 0-255.
        bytes = [*map(lambda x: int(x, 16), map("".join, zip(hexdigest[::2], hexdigest[1::2], strict=False)))]
        # Compress an arbitrary number of bytes to `words`.
        compressed = self.compress(bytes, words)
        # Map the compressed byte values through the word list.
        return separator.join(self.wordlist[byte] for byte in compressed)

    @staticmethod
    def compress(bytes, target):
        """
        Compress a list of byte values to a fixed target length.

            >>> bytes = [96, 173, 141, 13, 135, 27, 96, 149, 128, 130, 151]
            >>> HumanHasher.compress(bytes, 4)
            [205, 128, 156, 96]

        Attempting to compress a smaller number of bytes to a larger number is
        an error:

            >>> HumanHasher.compress(bytes, 15)  # doctest: +ELLIPSIS
            Traceback (most recent call last):
            ...
            ValueError: Fewer input bytes than requested output
        """

        length = len(bytes)
        if target > length:
            raise ValueError("Fewer input bytes than requested output")

        # Split `bytes` into `target` segments.
        seg_size = length // target
        segments = [bytes[i * seg_size : (i + 1) * seg_size] for i in range(target)]
        # Catch any left-over bytes in the last segment.
        segments[-1].extend(bytes[target * seg_size :])

        # Use a simple XOR checksum-like function for compression.
        checksum = lambda bytes: reduce(operator.xor, bytes, 0)
        checksums = map(checksum, segments)
        return checksums

    def uuid(self, **params):
        """
        Generate a UUID with a human-readable representation.

        Returns `(human_repr, full_digest)`. Accepts the same keyword arguments
        as :meth:`humanize` (they'll be passed straight through).
        """

        digest = str(uuidlib.uuid4()).replace("-", "")
        return self.humanize(digest, **params), digest


DEFAULT_HASHER = HumanHasher()
uuid = DEFAULT_HASHER.uuid
humanize = DEFAULT_HASHER.humanize
