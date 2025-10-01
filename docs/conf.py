extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.coverage",
    "sphinx.ext.doctest",
    "sphinx.ext.extlinks",
    "sphinx.ext.ifconfig",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
]
source_suffix = ".rst"
master_doc = "index"
project = "agh"
year = "2025"
author = "Tuck Williamson"
copyright = f"{year}, {author}"
version = release = "0.2.1"

pygments_style = "trac"
templates_path = ["."]
extlinks = {
    "issue": ("https://github.com/Tuck-Williamson/python-agh/issues/%s", "#%s"),
    "pr": ("https://github.com/Tuck-Williamson/python-agh/pull/%s", "PR #%s"),
}

html_theme = "sphinx_py3doc_enhanced_theme"
html_theme_options = {
    "source_repository": "https://github.com/Tuck-Williamson/python-agh/",
    "source_branch": "main",
    "source_directory": "docs/",
    "footer_icons": [
        {
            "url": "https://github.com/Tuck-Williamson/python-agh/",
            "html": "github.com/Tuck-Williamson/python-agh",
        },
    ],
}

html_use_smartypants = True
html_last_updated_fmt = "%b %d, %Y"
html_split_index = False
html_short_title = f"{project}-{version}"

napoleon_use_ivar = True
napoleon_use_rtype = False
napoleon_use_param = False
