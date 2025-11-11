import socket
from os import environ

LOCAL_NAMES = ['glendronach', 'awesom-o-4000', 'Klauss-MacBook-Pro.local', 'Asus-Tuf-Dash-f15', 'mac.home']

SESSION_CONFIG_DEFAULTS = {
    'real_world_currency_per_point': 1.00,
    'participation_fee': 0.00,

    'timeout_bargain': 3 * 60,
    'timeout_bargain_round1': 5 * 60,

    # Fixed market price and production cost are only used in test
    # Will be randomized if not set to >= 0
    'market_price': -1,
    'production_cost': -1,

    # For live_bargaining, always randomize the values
    'market_price_low': 10,
    'market_price_high': 12,
    'production_cost_low': 3,
    'production_cost_high': 5,
    'demand_low': 0,
    'demand_high': 100,

    'preference_role': "",

    'default_greedy': 3,
    # This is only used by Test
    'max_greedy': True,
    # This is only used by live_bargain
    'override_make_it_greedy': False,
    'override_make_it_NON_greedy': False,

    'override_third_round_HUMAN_vs_HUMAN': False,
    'override_third_round_BOT_vs_HUMAN': False,

    'within_balance_desgin_BOT_vs_HUMAN_4_at_a_time': False,

    'use_bots': True,

    'llm_user': 'otree',
    'llm_pass': 'ped+GlubbomOnEc4',
    'llm_model': 'llama3',
    'llm_temp': 0.1,
    'llm_reader': 'reader',
    'llm_constraint': 'constrain_reader',

    "https://ollama1.src-automating.src.surf-hosted.nl": True,
    "https://ollama2.src-automating.src.surf-hosted.nl": False,
    "https://ollama3.src-automating.src.surf-hosted.nl": False,
    "https://ollama4.src-automating.src.surf-hosted.nl": True,
    "https://ollama5.src-automating.src.surf-hosted.nl": True,
    "https://ollama6.src-automating.src.surf-hosted.nl": True,
    "https://ollama7.src-automating.src.surf-hosted.nl": True,

    "Class A": True,
    "Class B": True,
    "Class C": True,
    "Class D": True,
    "Class E": True,
    "Class F": True,
    "Class G": True,
    "Class H": True,
    "Class I": True,
    
    'doc': ""
}

def is_class_active(session_config_details, _class) -> bool:
    return session_config_details.get(_class, False)

def initialize_negotiation_classes(config):
    negotiation_classes = {
        'Class A': {
            'market_price': 12,
            'production_cost': 3,
        },
        'Class B': {
            'market_price': 11,
            'production_cost': 3,
        },
        'Class C': {
            'market_price': 12,
            'production_cost': 4,
        },
        'Class D': {
            'market_price': 10,
            'production_cost': 3,
        },
        'Class E': {
            'market_price': 11,
            'production_cost': 4,
        },
        'Class F': {
            'market_price': 12,
            'production_cost': 5,
        },
        'Class G': {
            'market_price': 10,
            'production_cost': 4,
        },
        'Class H': {
            'market_price': 11,
            'production_cost': 5,
        },
        'Class I': {
            'market_price': 10,
            'production_cost': 5,
        },
    }

    active_classes = {}
    for class_name, params in negotiation_classes.items():
        if is_class_active(config, class_name):
            active_classes[class_name] = params
    return active_classes

SESSION_CONFIG_DEFAULTS['active_classes'] = initialize_negotiation_classes(SESSION_CONFIG_DEFAULTS)

tmp = SESSION_CONFIG_DEFAULTS
hostname = socket.gethostname()
if hostname in LOCAL_NAMES[:2]:
    tmp['timeout_bargain'] *= 10
    tmp['timeout_bargain_round1'] *= 10

if hostname in LOCAL_NAMES:
    # Each non-existent host adds 5 seconds to Session initialization
    for key in [k for k in tmp.keys() if k.startswith('http')]:
        tmp[key] = False
    # Otree on Awesom-o with Ollama on Glendronach
    if hostname == LOCAL_NAMES[1]:  # and False:
        tmp["http://192.168.199.13:11434"] = True
    else:
        tmp["http://localhost:11434"] = True

SESSION_CONFIGS = [
    dict(
        name='live_bargaining',
        display_name='Live Bargaining',
        app_sequence=['live_bargaining'],
        num_demo_participants=5,
    ),

    dict(
        name='Test',
        display_name='Test',
        app_sequence=['test'],
        num_demo_participants=1,
    ),

    dict(
        name='Reset',
        app_sequence=['reset'],
        num_demo_participants=1,
    ),
]

PARTICIPANT_FIELDS = []
SESSION_FIELDS = ['debug_log', 'llm_hosts']

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'en'

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'EUR'
USE_POINTS = True

ADMIN_USERNAME = 'admin'
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """ """

SECRET_KEY = '4548051812285'
