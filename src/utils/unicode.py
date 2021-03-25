import re
import json
import requests

symfile = 'utils/symbols.json'
url = 'https://raw.githubusercontent.com/joom/latex-unicoder.vim/master/autoload/unicoder.vim'

try:
    with open(symfile, 'r', encoding='utf8') as f:
        symbols = json.load(f)
        
except FileNotFoundError:
    # print('Downloading latex symbols...')
    content = requests.get(url).content.decode()
            
    # read symbol dict
    content = content.replace("'", '"').replace('\\', '')
    dict_text = re.search(r'\{[\s\S]*?\}\s', content)[0]
    symbols = json.loads(dict_text)

    # cleaning
    for k, v in tuple(symbols.items()):
        if len(v.encode('unicode_escape')) > 8:
            del symbols[k]
    
    with open(symfile, 'w', encoding='utf8') as f:
        json.dump(symbols, f)

        
extra_mappings = {
    'sum': 'Sigma',
    'prod': 'Pi',
    '/\\': 'land',
    '\\/': 'lor',
    '->': 'rightarrow',
    '<-': 'leftarrow',
    '=>': 'Rightarrow',
    '<=': 'Leftarrow',
    '^T': 'ᵀ',
    '*': 'times',
    'i': 'ⅈ',
    'e': 'ℯ',
    'Z': 'mathbb{Z}',
    'Q': 'mathbb{Q}',
    'R': 'mathbb{R}',
    'C': 'mathbb{C}',
    'inf': 'infty',
    'ga': 'alpha',
    'gb': 'beta',
    'gd': 'delta',
    'ge': 'epsilon',
    'gg': 'gamma',
    'gi': 'iota',
    'gk': 'kappa',
    'gl': 'lambda',
    'go': 'omega',
    'gs': 'sigma',
    'gu': 'upsilon',
    'deg': '°',
    'ang': '∠',
    'dee': '∂',
    'E': 'exists',
    'A': 'forall',
    'grin': '😁',
    'haha': '😂',
    'smile': '🙂',
    'lol': '🤣',
    'fire': '🔥',
    'cow': '🐮',
    'monkey': '🐒',
    'horse': '🐴',
    'tree': '🌲',
    'cake': '🍰',
    'red': '🟥',
    'green': '🟩',
    'blue': '🟦',
    # 'white': '⬜',
    # 'black': '⬛'
}


def subst(s):
    """Substitute escaped characters."""
    t = extra_mappings.get(s, s)
    return symbols.get(t, t)


if __name__ == "__main__":
    print(subst(r'\alpha'))
