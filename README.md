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

### Linux e MacOS

1. Clonar o projeto.
Para isso, abrir o terminal e executar:
```bash
git clone https://github.com/andreavb/picapau-mvp.git
cd picapau-mvp
```

2. Criar o ambiente virtual e ativá-lo:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Instalar as dependências:
```bash
pip install -r requirements.txt
```

4. Inserir sua própria base de exercícios em `exercises.json`.

5. Executar o aplicativo:
```bash
python app.py
```

### Windows

1. Instalar o [Python](https://www.python.org/downloads/windows/) caso ainda não tenha.
IMPORTANTE: Durante a instalação, marcar `☑ Add Python to PATH`.

2. Clonar o projeto.
Para isso, abrir o terminal (`CMD`) e executar:
```bash
git clone https://github.com/andreavb/picapau-mvp.git
cd picapau-mvp
```

3. Criar o ambiente virtual e ativá-lo:
```bash
python -m venv .venv
.venv\Scripts\activate
```

4. Instalar as dependências:
```bash
pip install -r requirements.txt
```

5. Inserir sua própria base de exercícios em `exercises.json`.

6. Executar o aplicativo:
```bash
python3 app.py
```

## Acessando o aplicativo

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
    "title": "Mate em 1 #1",
    "description": "Brancas jogam.",
    "fen": "k7/8/K7/8/8/8/8/Q7 w - - 0 1",
    "solution": ["a1h8"]
}
```

## Próximos passos
- trocar `exercises.json` por PGN
- aceitar exercícios multi-lance com resposta automática do lado adversário
- ranking dos exercícios mais lentos ou com mais tentativas  erradas
- relatórios de evolução entre sessões
