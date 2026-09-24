<!-- bmad:context -->
<!-- Verified 2026-09-24 against the working tree (4 new tasks uncommitted, base baaa3df). Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## YouLikeHits-Bot

Bot em Python que automatiza tarefas de troca no YouLikeHits.com via Selenium com `undetected-chromedriver`, com GUI em customtkinter e menu CLI. É um fork de um repositório defasado em modernização completa. A landing page em `landing/` é um app Next.js 16 separado. Artefatos de planejamento BMAD ficam em `_bmad-output/` (local, fora do git).

## Política

- Mantenha `_bmad/`, `_bmad-output/`, `.agents/` e `.claude/` no `.gitignore`.

## Ferramentas MCP

- Ao trabalhar no código, use o Serena MCP para navegação e edição simbólica em vez de reler arquivos inteiros: `get_symbols_overview`/`find_symbol` para localizar, `find_referencing_symbols` antes de mudar uma assinatura, e os editores simbólicos (`replace_symbol_body`, `insert_after_symbol`, `replace_in_files`) para as edições. Ative o projeto uma vez por sessão (`activate_project`).
- Para ler o site vivo, use o browsermcp (ele já se conecta ao Chrome logado do bot): `browser_navigate` + `browser_snapshot` dão a árvore de acessibilidade. O snapshot NÃO traz ids/classes/onclick crus; quando precisar deles, aí sim abra uma aba própria pela porta de depuração do Chrome (`/json/new` via PUT, WebSocket com `suppress_origin`, CDP `Runtime.evaluate`), só leitura, e feche-a ao fim. A porta muda a cada restart do Chrome (`ps aux | grep remote-debugging-port`).

## Onde ficam as coisas

- Loops do bot: um módulo por tarefa em `bot_logic/`; fluxo comum de views/plays (timer na página) em `bot_logic/earn.py`; fluxo comum de likes/follows (ação no outro site + confirmação) em `bot_logic/engage.py`, usado por `youtube_likes`, `soundcloud_follows`, `instagram_follows`, `instagram_likes`, `twitter_follows` e `twitter_likes`; fábrica do navegador em `bot_logic/utils.py`; GUI em `gui/app.py`; menu CLI em `main_cli.py`.
- Os seletores ao vivo de cada tarefa moram como constantes no topo do próprio módulo, com a data em que foram lidos no docstring; leia o módulo antes de mexer nele. Não os duplique aqui.
- Landing: `landing/`, com `package.json` próprio; rode os comandos npm de dentro dela, a raiz não tem `package.json`.

## Rodar e verificar

- Python 3.10+. Inicie pelo `./run.sh`: ele cria `venv/`, instala o tkinter do sistema e detecta o DISPLAY. `python main.py` direto instala dependências no interpretador que estiver ativo, seja ele qual for.
- O ambiente do projeto é `venv/` via pip; `uv run` serve só para `_bmad/scripts/`.
- Testes: `venv/bin/python -m unittest` roda a suíte em `tests/` contra um driver Selenium falso (sem navegador, sem rede, ~1 s). Rode antes de qualquer mudança em `bot_logic/`. Não há linter nem CI. Verifique a landing com `npm run lint` e `npm run build` em `landing/`.
- Nos testes, nunca anule `time.sleep` sozinho: `wait_unless_stopped` usa `time.monotonic` e vira busy-wait real. Use o `_FakeClock` de `tests/test_tasks.py`, que avança o relógio a cada sleep.
- Fakes de teste (`tests/fakes.py`): as chaves de `elements` são casadas por parte — o `FakeDriver` faz `split(',')` no seletor e busca cada parte, então registre sob UMA das partes, nunca sob o seletor com vírgula inteiro.
- tkinter não vem do pip: `run.sh` instala o pacote da distro. Nunca o adicione ao `requirements.txt`.

## Convenções que fogem do padrão

- Cada módulo de `bot_logic/` expõe uma função de página `process_*_once(driver, log, is_stopped, limit)` e um loop `_run_*_task(driver, is_stopped, log_func, update_points_func)`. A GUI chama `_run_*_task` numa thread; o CLI chama o mesmo `_run_*_task` via `utils.run_cli_task`; `master.py` compõe os `process_*_once`. Lógica de página muda só em `process_*_once`. Nunca recrie o par duplicado GUI/CLI.
- `setup_browser` em `bot_logic/utils.py` é a única fábrica de navegador. Não crie outra.
- O major do Chrome é detectado em tempo de execução (`utils.detect_chrome_major` lê `chrome --version`) e passado como `version_main` ao uc. Não fixe número em código.
- Esperas longas usam `utils.wait_unless_stopped(segundos, is_stopped)`, nunca `time.sleep` direto, para que o Stop da GUI responda em ~1 s.
- Configuração do usuário fica em `settings.json` na raiz (ignorado pelo git), lida e validada por `bot_logic/settings.py`; nunca leia o arquivo direto. `_run_master_task` aceita `settings=`; a GUI salva o painel do Master Loop (tarefas marcadas + espera) ao iniciar o Master Loop, o CLI pergunta antes de iniciar.
- Quais tarefas o Master Loop roda vem de `settings["master_tasks"]` (lista de chaves de `settings.TASKS`, validada para a ordem canônica; ausente/lixo = todas, lista vazia = nenhuma e o master avisa e sai). `settings.TASKS` é a única fonte de chaves e rótulos: GUI (checkboxes no painel acima do log), CLI (`parse_task_selection`, números na ordem de `TASKS`) e `master._steps` derivam dela. Tarefa nova = módulo com `process_*_once` + entrada em `TASKS` + `*_per_cycle` em `DEFAULTS` + passo em `master._steps` + botão em `gui.LOOPS`/`_task_for` + opção no menu CLI.
- GUI: um loop por vez (`self.running_loop`). Toda atualização de widget a partir de thread passa por `self._ui(...)` (`root.after`). O navegador fica aberto durante o login; `_watch_browser` desabilita os loops se o usuário fechá-lo.
- O site só credita pontos se o clique for confiável (`event.isTrusted`), e o timer roda no JavaScript da própria página. Clique sempre com `element.click()` do Selenium, nunca via `execute_script`, e espere o resultado em vez de dormir um tempo fixo. `earn.py` encapsula isso para views/plays; `engage.py` para likes/follows.
- Fluxo `engage.py` (likes/follows): a ação acontece no outro site (YouTube/SoundCloud/Instagram/X), verificada pelo YouLikeHits. `engage.classify` decide creditado > pendente > falha; texto desconhecido vira final após 15 s estável; espera total 90 s. Rótulos dos sites externos vêm localizados (pt-BR): nunca case por texto, use `data-testid`/estrutura/`aria-label`. `engage.NOT_SIGNED_IN` encerra a passada com aviso quando o site externo pede login (ou a conta está em challenge/suspensa) e o loop tenta de novo em 1 min.
- UI otimista (verificado ao vivo): YouTube/SoundCloud/Instagram/X trocam o botão ANTES de a requisição terminar. Fechar o popup na hora perdeu follows ao vivo. Os follows esperam a página estabilizar antes de clicar e reconferem que a ação SEGUROU (`engage.settle_action`; `_follow_held` no X/IG) antes de contar.
- Lista que desliza vs recarrega (`engage.Flow.reload_between_cards`): páginas de likes do YouTube/SoundCloud recarregam entre cartões (default `True`); as páginas de follow do Instagram/Twitter deslizam a própria lista via AJAX, então usam `False` — recarregar reembaralha e o usuário vê a lista "pular pra trás".
- Já-feito → Skip, não reload (`engage.is_already_done`/`ALREADY_RE`): quando o YLH reexibe um perfil já seguido, o confirm devolve "tap the Follow link first / already followed". Esse veredito nunca credita; o bot clica o Skip do cartão (`skipuser`, tira da lista) em vez de recarregar (que reenfileira). Falha genuína (rate limit, revert) NÃO é skipada.
- Cartão que falha não é removido pelo site: `engage` tenta cada cartão uma vez por passada (conjunto `tried`).
- Bônus resgatável (verificado ao vivo): `.bonus-pill--active` + `a.buybutton` `href="?step=get"`. Após o clique a página ainda mostra o total antigo no cabeçalho; releia os pontos numa navegação nova.
- `:contains()` não é CSS válido no Selenium; um teste guarda isso.
- O bloqueador de popup do Chrome fica ligado (`--disable-popup-blocking` foi removido e um teste guarda isso): os popups do próprio site vêm do clique confiável e passam; a flag só servia aos pop-unders dos anunciantes. Sites visitados abrem pop-unders durante todo o timer, por isso `utils.WindowGuard` tira um snapshot antes do clique, aceita só a primeira janela nova e fecha o resto a cada poll do `wait_until`.
- `utils.browser_state` distingue `alive`, `unresponsive` e `closed`. Só erro de sessão morta ou processo do chromedriver encerrado é `closed`; timeout ou erro de aba é `unresponsive`, a GUI mostra "Browser Not Responding" e continua vigiando. Visto ao vivo em 2026-09-20: um site abriu 1.100 abas, `window_handles` falhou e a GUI declarou "Browser was closed" com o navegador aberto.

## Armadilhas conhecidas

- Em sessões RDP/VNC o DISPLAY é `:10.0`, não `:0`; `run.sh` o detecta pelos sockets em `/tmp/.X11-unix`. Nunca fixe `:0` em código.
- Instagram: o post NÃO fica em `<article>` e cada comentário tem um "Curtir" também — o like do post é o `svg[aria-label]` com `height="24"` (comentários são 16). O botão Seguir do perfil é o `header button[type=button]` sem svg (Seguindo tem svg de seta); os outros header buttons são link da bio/mensagem. Nunca case por texto. Uma conta em challenge ("Confirme que você é humano") derruba tudo: o `act` detecta e vira `NOT_SIGNED_IN`.
- X (Twitter): follow = `button[data-testid$='-follow']` (vira `-unfollow`); like = `button[data-testid='like']` (vira `unlike`), o primeiro no DOM numa página `/status/` é o do tweet. Aviso de conteúdo sensível esconde o header: clique `button[data-testid='empty_state_button_text']` ("Yes, view profile") antes de procurar o follow.
- Ler o YouTube ao vivo: em aba de fundo a página de vídeo fica presa em `#watch-page-skeleton` sem botão de like; só renderiza em janela nova (`Target.createTarget` com `newWindow`), que é o que o popup do site abre, então o bot não sofre disso. O X, ao contrário, renderiza normalmente em aba de fundo.
- em `landing/`: `output: "export"` em `next.config.ts` foi removido só porque a Vercel o rejeitava. Ao migrar para hospedagem sem Vercel (decisão tomada), reative-o e remova `vercel.json`.

<!-- /bmad:context -->
