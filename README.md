# Pica-Pau MVP

## O que este protótipo faz
- carrega os exercícios locais de `exercises.json`
- mostra um exercício por vez
- impede lances ilegais com `python-chess`
- aceita apenas a linha correta
- joga automaticamente a resposta do adversário quando existir
- mede o tempo por exercício e tempo da sessão
- salva as tentativas em SQLite
- emite um relatório simples ao final

## Como rodar
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Depois, abra `http://127.0.0.1:5000`, caso esteja rodando o servidor localmente.
Caso esteja usando uma máquina remota (por exemplo, EC2), abra `http://[IP_DA_MÁQUINA]:5000`.

## Estrutura dos exercícios
Os exercícios ficam salvos em `exercises.json`.
Cada exercício usa a seguinte estrutura:
- `id`
- `title`
- `description`
- `fen`
- `solution`: lista de lances UCI

Exemplo:
```json
{
  "id": "ex001",
  "title": "Mate em 1",
  "description": "Brancas jogam.",
  "fen": "6k1/5ppp/8/8/8/8/5PPP/6KQ w - - 0 1",
  "solution": ["h1h8"]
}
```

## Próximos passos
- trocar `exercises.json` por PGN
- aceitar exercícios multi-lance com resposta automática do lado adversário
- ranking dos exercícios mais lentos ou com mais tentativas  erradas
- relatórios de evolução entre sessões
