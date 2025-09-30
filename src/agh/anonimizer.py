import agh.humanhash as humanhash
from hashlib import md5

defWordList = (
        "aged", "acre",  # "acorn", "acts",
        "afar", "agent",  #
        "affix", "agile",
        # "aging", "ahead", #"agony", "aids",
        "aim", "alike",  # "alarm", "alive",
        # "alone", "aloft",
        "aloha", "amend",
        "ample", "angel",  # "amuse", "anger",
        "apple", "apron",  # "april", "awake",
        "area", "argue",  # "army", "armed",
        "armor", "art",  # "arson", "atlas",
        # "atom", "avoid", #
        "avert", "bacon",
        "boots", "book",  # "basil", "bust",
        "baker", "bunch",  # "balmy", "broke",
        "barn", "baton",  #
        "both", "blade",
        "blank", "blog",  # "blast", "blend",
        "blimp", "blurt",  # "blob", "bully",
        # "boned", "broad", #"bunny", "bribe",
        "bring", "civil",  # "broil", "case",
        "city", "come",  # "claim", "canal",
        "candy", "card",  # "chief", "crazy",
        "carol", "crop",  # "carry", "cedar",
        "crown", "clay",  # "cost", "chump",
        "comic", "cold",  #
        "civic", "clamp",
        "clip", "clasp",  #
        "class", "clear",
        # "cleft", "cling", #"clerk", "cover",
        # "craft", "crank", #"cramp", "crisp",
        "crust", "cycle",  # "cupid", "deaf",
        "data", "draw",  #
        "deal", "duke",
        # "doing", "drama", #"dent", "dried",
        "down", "debug",  # "debt", "decaf",
        "decal", "drive",  # "decor", "dimly",
        # "donor", "drank", #
        "ditch", "dress",
        "drift", "dust",  # "drill", "equal",
        "early", "east",  # "earth", "eaten",
        "edge", "even",  # "ebay", "evoke",
        "essay", "elbow",  # "eel", "elder",
        "elk", "elude",  #
        "elm", "elves",
        "email", "empty",  # "emit", "emu",
        "enter", "erase",  # "envoy", "error",
        # "erupt", "evict", #"evade", "evil",
        "fable", "food",  # "fact", "fall",
        "false", "fox",  #
        "fancy", "femur",
        "found", "fetal",  # "ferry", "fetch",
        # "fever", "film", #"fifth", "fled",
        "final", "flip",  # "five", "fling",
        "flint", "flyer",  # "flirt", "foam",
        # "frail", "fresh", #"from", "fruit",
        "front", "gas",  #
        "frost", "going",
        # "goal", "gave", #
        "game", "grew",
        "genre", "glass",  # "gift", "given",
        "giver", "golf",  #
        "glad", "good",
        # "grab", "grant", #"green", "grasp",
        "grass", "grill",  # "grid", "habit",
        "help", "halt",  #
        "hull", "happy",
        "harm", "hasty",  #
        "hug", "hatch",
        # "hate", "hazel", #
        "haven",  # "herbs",
        # "hers",
        "hunt",  # "human", "hump",
        # "hung", "hurt", #"hurry", "issue",
        # "icing", "igloo", #
        "icon", "image",
        "ion", "item",  # "iron", "ivory",
        "ivy", "jam",  # "job", "juice",
        "july", "jolt",  # "jet", "judge",
        "jump", "jury",  # "junky", "keep",
        "kick", "kilt",  # "kept", "king",
        # "kitty", "knelt", #
        "knee", "koala",
        # "ladle", "lure", #"late", "lake",
        "lunch", "level",  # "land", "large",
        "last", "left",  # "latch", "legal",
        "line", "life",  #
        "liver", "lilac",
        "lily", "lunar",  # "limb", "music",
        "maker", "many",  # "mold", "mango",
        "manor", "march",  # "move", "mardi",
        # "marry", "mouth", #
        "match", "most",
        "motor", "mulch",  # "mount", "mule",
        "mumbo", "niece",  # "mural", "nail",
        "name", "near",  # "navy", "net",
        # "nerd", "ninth", #
        "next", "oak",
        "oat", "oil",  # "ocean", "old",
        "olive", "only",  # "onion", "oval",
        "open", "opt",  #
        "opera", "outer",
        # "ounce", "pagan", #"push", "poker",
        "palm", "punch",  # "point", "pants",
        "paper", "party",  # "press", "pasta",
        # "patch", "power", #
        "photo", "poem",
        "puppy", "petal",  # "perm", "petri",
        "plank", "plus",  #
        "plant", "plot",
        # "pull", "prank", #"polar", "print",
        "prism", "props",  # "proof", "pulp",
        "pupil", "query",  # "quake", "quiet",
        "quill", "raft",  # "quilt", "risk",
        "radar", "rule",  # "radio", "ramp",
        "range", "robin",  # "rant", "react",
        "roman", "recap",  # "reply", "relax",
        "rope", "rigor",  # "rerun", "ritzy",
        "river", "size",  # "stole", "said",
        # "send", "slam", #
        "salt", "silk",
        "same", "speed",  # "steam", "spray",
        # "scale", "score", #
        "scan", "scrap",
        "scope", "squad",  # "scold", "scorn",
        # "self", "serve", #
        "ship", "seven",
        "share", "shirt",  #
        "shell", "shrug",
        # "siren", "slang", #"skirt", "slept",
        "slurp", "swing",  # "small", "smirk",
        # "snap", "snarl", #
        "snare", "snort",
        "speak", "spill",  # "spent", "sport",
        "stage", "stamp",  # "stop", "stand",
        "sting", "start",  # "stark", "stir",
        "storm", "those",  # "swirl", "tall",
        "talon", "think",  # "tamer", "taper",
        # "taps", "taste", #
        "trade", "tint",
        # "theft", "train", #"theme", "trap",
        "tweet", "try",  #
        "thumb", "tidal",
        "tiger", "track",  # "tilt", "trend",
        "trial", "tulip",  # "trunk", "tutor",
        # "uncle", "unit", #"uncut", "unify",
        "union", "upper",  #
        "upon", "urban",
        # "used", "utter", #"user", "value",
        "vapor", "venue",  # "vegan", "virus",
        "vest", "voice",  #
        "video", "viral",
        "visor", "volt",  # "vocal", "voter",
        "wheat", "wager",  #
        "wafer", "wish",
        "wagon", "wind",  # "walk", "wasp",
        # "watch", "wife", #
        "water", "whole",
        # "widen", "womb", #"wilt", "wing",
        "word", "wolf",  # "worry", "work",
        "woven", "xerox",  # "wrist", "yummy",
        "yard", "yeast",  # "year", "yelp",
        "yield", "yoga",  # "yodel", "zebra",
        "zero", "zippy",  # "zesty", "zone",
)
hh = humanhash.HumanHasher(wordlist=defWordList)


def anonymize(submission_file_name: str, assignment_name: str, assignment_year: str, assignment_semester: str,
              assignment_course: str, prefix: str = "edu.cofc") -> str:
    """
    Generates an anonymized filename for a submission file by creating a hash of identifying information and
    converting it into a human-readable format.

    The function takes the submission file name and its relevant assignment details as input, generates a hash
    to create a unique identifier, and then utilizes a human-readable hash library to return an anonymized name.

    Parameters:
    submission_file_name: str
        The original name of the submission file.
    assignment_name: str
        Name of the assignment associated with the submission.
    assignment_year: str
        Year the assignment has been assigned or is due.
    assignment_semester: str
        Semester of the assignment (e.g., Spring, Fall).
    assignment_course: str
        Course identifier for the assignment (e.g., course code).
    prefix: str, optional
        A customizable prefix used in generating the hash. Default is 'edu.cofc'.

    Returns:
    str
        An anonymized and human-readable name for the submission file by incorporating assignment and submission
        information.
    """
    full_name = (f'{prefix}.{assignment_year}.{assignment_semester}.{assignment_course}.{assignment_name}-'
                 f'{submission_file_name}')
    anonName = hh.humanize(md5(full_name.encode(errors='xmlcharrefreplace')).hexdigest())
    return anonName
