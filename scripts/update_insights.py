"""Generate profile insights from all public repositories owned by the account."""
import json
import os
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OWNER = 'DescomplicaDevDan'
COLORS = ['#32e64f', '#45b7ff', '#f4d35e', '#bc8cff', '#ff9478', '#4de0ca']


def api(path):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'profile-insights'}
    if os.environ.get('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    with urlopen(Request('https://api.github.com' + path, headers=headers), timeout=30) as response:
        return json.load(response)


def collect():
    repos = []
    page = 1
    while True:
        batch = api(f'/users/{OWNER}/repos?type=owner&per_page=100&page={page}')
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    languages = Counter()
    records = []
    for repo in repos:
        values = api(f'/repos/{OWNER}/{repo["name"]}/languages')
        languages.update(values)
        records.append({'name': repo['name'], 'fork': repo['fork'], 'languages': values})
    return {
        'updated_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
        'repositories': len(repos),
        'forks_included': sum(repo['fork'] for repo in repos),
        'stars': sum(repo['stargazers_count'] for repo in repos),
        'languages': dict(sorted(languages.items(), key=lambda item: (-item[1], item[0]))),
        'sources': records,
    }


def render(data):
    languages = data['languages']
    total = sum(languages.values())
    height = 260 + max(len(languages), 1) * 54
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="{height}" viewBox="0 0 1100 {height}" role="img" aria-labelledby="title desc">',
             '<title id="title">Linguagens e atividade dos repositórios públicos</title>',
             '<desc id="desc">Distribuição por bytes de código, incluindo forks. Valores disponíveis em texto no README.</desc>',
             f'<rect x="1" y="1" width="1098" height="{height-2}" rx="14" fill="#07140b" stroke="#174822"/>',
             '<g font-family="Consolas,monospace">']

    def text(x, y, value, size=20, color='#e6eee8'):
        parts.append(f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}">{escape(str(value))}</text>')

    text(30, 38, '&gt;_ github --insights'.replace('&gt;', '>'), 16, '#32e64f')
    for x, number, label in [(30, data['repositories'], 'REPOSITÓRIOS PÚBLICOS'), (395, len(languages), 'LINGUAGENS'), (760, data['stars'], 'ESTRELAS RECEBIDAS')]:
        text(x, 92, number, 38, '#32e64f')
        text(x, 122, label, 17, '#a4b5a8')
    parts.append('<path d="M30 148h1040" stroke="#174822"/>')
    text(30, 184, 'Linguagens em todo o meu GitHub público', 26)
    for i, (language, count) in enumerate(languages.items()):
        y = 222 + i * 54
        percentage = count / total * 100 if total else 0
        text(30, y, language, 19)
        text(938, y, f'{percentage:.2f}%', 19, '#a4b5a8')
        parts.append(f'<rect x="280" y="{y-17}" width="620" height="20" rx="5" fill="#14291b"/>')
        parts.append(f'<rect x="280" y="{y-17}" width="{620*percentage/100:.2f}" height="20" rx="5" fill="{COLORS[i % len(COLORS)]}"/>')
    if not languages:
        text(30, 222, 'Nenhuma linguagem detectada pelo GitHub.', 19)
    text(30, height-42, 'Proporção por bytes de código · inclui forks · não mede proficiência', 16, '#a4b5a8')
    text(30, height-17, 'Atualizado em ' + data['updated_at'], 15, '#a4b5a8')
    parts.append('</g></svg>')
    return '\n'.join(parts) + '\n'


def update(data):
    total = sum(data['languages'].values())
    rows = ['| Linguagem | Proporção do código |', '| :--- | ---: |']
    for language, count in data['languages'].items():
        rows.append(f'| {escape(language)} | {count/total*100:.2f}% |')
    if not data['languages']:
        rows.append('| Nenhuma linguagem detectada | — |')
    summary = (f"Atualizado em **{data['updated_at']}**. "
               f"**{data['repositories']} repositórios públicos**, **{len(data['languages'])} linguagens** "
               f"e **{data['stars']} estrelas recebidas**. Forks incluídos: **{data['forks_included']}**.\n\n" + '\n'.join(rows))
    readme = ROOT / 'README.md'
    content = readme.read_text(encoding='utf-8')
    start, end = '<!-- insights:start -->', '<!-- insights:end -->'
    before, rest = content.split(start, 1)
    _, after = rest.split(end, 1)
    # Only write after all API requests and marker validation succeed.
    (ROOT / 'github-insights.svg').write_text(render(data), encoding='utf-8')
    (ROOT / 'github-insights.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    readme.write_text(before + start + '\n' + summary + '\n' + end + after, encoding='utf-8')


if __name__ == '__main__':
    update(collect())
