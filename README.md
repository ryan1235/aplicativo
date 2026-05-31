# GG Coalition

Primeira interface em Python para um painel inspirado em Foxhole.

## Rodar

```powershell
py -m pip install --target vendor -r requirements-python.txt
py felb_app.py
```

## Steam

O app tenta detectar automaticamente:

- pasta da Steam;
- SteamID local;
- nickname salvo em `config/loginusers.vdf`;
- avatar em cache quando existir na pasta local da Steam.

O nickname costuma funcionar sem internet. O avatar depende de a Steam ja ter baixado e mantido esse arquivo em cache no PC.

## Interface

O app comeca com o menu lateral fechado. Ele pode ser aberto ou fechado pelo botao hamburguer; o menu tem scroll, perfil Steam e secoes para `Inicio`, `Ferramentas`, `Overlay` e `Stockpile`.

Ao abrir, o GG Coalition mostra uma tela de carregamento com o GIF em `img/ggimege.gif`, verifica Steam e marca o usuario como ativo quando o perfil local for detectado. A tela inicial usa `img/wallpeper.png` como imagem de fundo.

Ao minimizar, o app fica em segundo plano na bandeja do Windows. Ao clicar em fechar, ele pergunta se voce quer fechar de verdade ou deixar em segundo plano; se marcar `Nao perguntar novamente`, essa escolha fica salva em `felb_settings.json`.

Os arquivos gravaveis do app ficam fora do executavel. Na primeira inicializacao, o app cria automaticamente:

```text
felb_settings.json
extracted/
```

Ele tenta usar `%LOCALAPPDATA%/GG Coalition`; se o Windows bloquear essa pasta, usa uma pasta gravavel alternativa automaticamente.

## Idiomas

O GG Coalition detecta o idioma do usuario automaticamente e carrega traducoes em `translations/pt`, `translations/en`, `translations/es` e `translations/fr`. Tambem da para mudar manualmente pelos botoes `PT`, `EN`, `ES` e `FR` no topo da janela.

## Auto update gratuito com GitHub Releases

O auto-update ja esta preparado nos arquivos `app_update.py` e `updater.py`. Ele fica desativado ate voce configurar o repositorio no topo de `felb_app.py`:

```python
APP_VERSION = "0.1.0"
UPDATE_REPO = "seu-usuario/gg-coalition"
```

Como publicar uma versao:

1. Crie um repositorio novo no GitHub, por exemplo `gg-coalition`.
2. Envie o projeto para esse repo.
3. Gere uma pasta ou build final do app.
4. Compacte os arquivos em um `.zip`, mantendo `felb_app.py`, `updater.py`, `app_update.py`, `img/`, `translations/`, `Content/` e os demais `.py` na raiz do zip.
5. No GitHub, abra `Releases` > `Draft a new release`.
6. Use uma tag maior que a versao atual, por exemplo `v0.1.1`.
7. Anexe o `.zip` nos assets da release e publique.
8. Atualize `APP_VERSION` no codigo para a mesma versao antes de gerar o zip.

Quando o app abrir, ele consulta a ultima release. Se a tag for maior que `APP_VERSION`, ele pergunta se deseja atualizar, baixa o zip, fecha o app, abre o `GG Updater.exe`, mostra uma janela de progresso da instalacao, substitui os arquivos e abre novamente.

## Gerar EXE

O jeito mais simples e rodar:

```powershell
.\build_exe.bat
```

Ou, se preferir pelo PowerShell:

```powershell
py build_exe.py --install --clean --zip
```

O script usa Nuitka, que compila o app para C/C++ e gera executavel `onefile`. Ele instala/atualiza `nuitka`, `customtkinter`, `pillow` e `pystray`, gera o executavel em:

```text
dist/GG Coalition.exe
```

Ele tambem compila o atualizador separado:

```text
dist/GG Updater.exe
```

E cria um zip pronto para enviar no GitHub Release:

```text
release/GG-Coalition.zip
```

Esse zip contem `GG Coalition.exe` e `GG Updater.exe`; e o arquivo que voce anexa na release para o auto-update.

## Stockpile API

A tela `API` deixa o app rodando sempre, observando o arquivo `*_MapData.sav` do Foxhole e consultando a API configurada internamente com `GET /data` e body `{"mode":"debug"}`. Para aparecer dado de stockpile, o usuario precisa fixar o stockpile no mapa dentro do Foxhole; o jogo salva esses dados no arquivo do mapa, e o GG Coalition atualiza o painel quando o arquivo muda.

A resposta da API e impressa no console como `[Stockpile API] HTTP ...`, alem de salvar uma copia JSON em `extracted/`.

Na tela inicial, o app tambem verifica se o Foxhole ja esta aberto. Quando encontra o processo do jogo, mostra ha quanto tempo ele foi iniciado; quando nao encontra, exibe o botao `Iniciar Foxhole`.

## Ferramentas

### Auto Clicker

Na aba `Ferramentas`, o Auto Clicker permite configurar:

- hotkey global, com `F3` como padrao;
- botao do mouse: esquerdo, direito ou meio;
- velocidade: devagar, normal ou rapido;
- captura a janela do Foxhole aberto;
- salvamento automatico em `felb_settings.json`.
- overlay flutuante visivel somente quando o Foxhole esta em foco.

### Overlay

Na aba `Overlay`, voce pode configurar:

- atalho do overlay, com `F8` como padrao;
- cor do overlay;
- campos exibidos, como perfil, Auto Clicker e janela alvo.

O Auto Clicker ja inicia ativo quando o app abre. A hotkey `F3` pausa ou retoma mesmo quando a janela do GG Coalition esta sem foco. Ele identifica a janela do Foxhole e envia cliques para um ponto virtual dentro dela, entao voce pode usar o mouse fisico em outra janela enquanto ele continua tentando clicar no jogo.

Quando voce clica em `Capturar Foxhole`, se o cursor estiver em cima da janela do jogo, esse ponto vira o local do clique virtual. Se o cursor estiver fora do jogo, o app usa o centro da janela como padrao.

## Organizacao

- `felb_app.py`: janela principal e layout base.
- `steam_profile.py`: leitura local da Steam, nickname e avatar em cache.
- `functions_category.py`: aba `Funcoes` da interface.
- `auto_clicker.py`: logica do Auto Clicker, hotkey global e clique automatico.
- `stockpiler.py`: leitura do arquivo `.sav`, conversao e envio para a API.
- `stockpile_category.py`: tela de configuracao do envio automatico.
- `i18n.py` e `translations/`: deteccao de idioma e catalogos de traducao.
- `settings_store.py`: leitura e salvamento das configuracoes.
- `app_update.py` e `updater.py`: checagem e instalacao de atualizacoes via GitHub Releases.
- `felb_settings.json`: criado automaticamente quando voce salva configuracoes.
