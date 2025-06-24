AUTHOR = 'Max Pfeiffer'
SITENAME = 'The Nerdy Tech Blog'
SITEURL = "http://127.0.0.1:8000"
THEME = "pelican-hyde"

PATH = "content"

TIMEZONE = 'Europe/Zurich'

DEFAULT_LANG = 'en'

STATIC_PATHS = [
    'images',
    'extra',
]
EXTRA_PATH_METADATA = {
    'extra/favicon.ico': {'path': 'favicon.ico'},
}

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

SOCIAL = (
    ("github", "https://github.com/max-pfeiffer"),
)

DEFAULT_PAGINATION = 10

# Hyde theme
PROFILE_IMAGE = "avatar.jpeg"
FOOTER_TEXT = "© 2025 Max Pfeiffer"

# SEO Plugin
SEO_REPORT = False
SEO_ENHANCER = True
SEO_ENHANCER_OPEN_GRAPH = False
SEO_ENHANCER_TWITTER_CARDS = False
SEO_ENHANCER_SITEMAP_URL = "https://max-pfeiffer.github.io/sitemap.xml"
LOGO = "https://max-pfeiffer.github.io/blog/images/avatar.jpeg"

# Sitemap plugin
SITEMAP = {
    "format": "xml",
    "priorities": {
        "articles": 0.9,
        "indexes": 1.0,
        "pages": 0.5
    },
    "changefreqs": {
        "articles": "weekly",
        "indexes": "daily",
        "pages": "monthly"
    }
}

# Injector Plugin
INJECTOR_ITEMS = [
    ('head', '<meta name="google-site-verification" content="F3nYemi_dYYQckoOJ33wBp5BG4frj27_I6Iiianw594" />'),
    ('head', '<link rel="icon" href="/favicon.ico">'),
]
INJECTOR_IN_PAGES = False
INJECTOR_IN_ARTICLES = True
