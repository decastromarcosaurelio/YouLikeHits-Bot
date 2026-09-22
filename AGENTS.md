<!-- bmad:context -->
<!-- Verified 2026-09-20 against working tree after review session (base 613141f). Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## YouLikeHits-Bot

Bot em Python que automatiza tarefas de troca no YouLikeHits.com via Selenium com `undetected-chromedriver`, com GUI em customtkinter e menu CLI. É um fork de um repositório defasado em modernização completa. A landing page em `landing/` é um app Next.js 16 separado. Artefatos de planejamento BMAD ficam em `_bmad-output/` (local, fora do git).

## Política

- Mantenha `_bmad/`, `_bmad-output/`, `.agents/` e `.claude/` no `.gitignore`.

## Onde ficam as coisas

- Loops do bot: um módulo por tarefa em `bot_logic/`; fluxo comum de views/plays (timer na página) em `bot_logic/earn.py`; fluxo comum de likes/follows (ação no outro site + confirmação) em `bot_logic/engage.py`; fábrica do navegador em `bot_logic/utils.py`; GUI em `gui/app.py`; menu CLI em `main_cli.py`.
- Landing: `landing/`, com `package.json` próprio; rode os comandos npm de dentro dela, a raiz não tem `package.json`.

## Rodar e verificar

- Python 3.10+. Inicie pelo `./run.sh`: ele cria `venv/`, instala o tkinter do sistema e detecta o DISPLAY. `python main.py` direto instala dependências no interpretador que estiver ativo, seja ele qual for.
- O ambiente do projeto é `venv/` via pip; `uv run` serve só para `_bmad/scripts/`.
- Testes: `venv/bin/python -m unittest` roda a suíte em `tests/` contra um driver Selenium falso (sem navegador, sem rede, <1 s). Rode antes de qualquer mudança em `bot_logic/`. Não há linter nem CI. Verifique a landing com `npm run lint` e `npm run build` em `landing/`.
- Nos testes, nunca anule `time.sleep` sozinho: `wait_unless_stopped` usa `time.monotonic` e vira busy-wait real. Use o `_FakeClock` de `tests/test_tasks.py`, que avança o relógio a cada sleep.
- tkinter não vem do pip: `run.sh` instala o pacote da distro. Nunca o adicione ao `requirements.txt`.

## Convenções que fogem do padrão

- Cada módulo de `bot_logic/` expõe uma função de página `process_*_once(driver, log, is_stopped, limit)` e um loop `_run_*_task(driver, is_stopped, log_func, update_points_func)`. A GUI chama `_run_*_task` numa thread; o CLI chama o mesmo `_run_*_task` via `utils.run_cli_task`; `master.py` compõe os `process_*_once`. Lógica de página muda só em `process_*_once`. Nunca recrie o par duplicado GUI/CLI.
- `setup_browser` em `bot_logic/utils.py` é a única fábrica de navegador. Não crie outra.
- O major do Chrome é detectado em tempo de execução (`utils.detect_chrome_major` lê `chrome --version`) e passado como `version_main` ao uc. Não fixe número em código.
- Esperas longas usam `utils.wait_unless_stopped(segundos, is_stopped)`, nunca `time.sleep` direto, para que o Stop da GUI responda em ~1 s.
- Configuração do usuário fica em `settings.json` na raiz (ignorado pelo git), lida e validada por `bot_logic/settings.py`; nunca leia o arquivo direto. `_run_master_task` aceita `settings=`; a GUI salva o painel do Master Loop (tarefas marcadas + espera) ao iniciar o Master Loop, o CLI pergunta antes de iniciar.
- Quais tarefas o Master Loop roda vem de `settings["master_tasks"]` (lista de chaves de `settings.TASKS`, validada para a ordem canônica; ausente/lixo = todas, lista vazia = nenhuma e o master avisa e sai). `settings.TASKS` é a única fonte de chaves e rótulos: GUI (checkboxes no painel acima do log), CLI (`parse_task_selection`, números na ordem de `TASKS`) e `master._steps` derivam dela. Tarefa nova = módulo com `process_*_once` + entrada em `TASKS` + `*_per_cycle` em `DEFAULTS` + passo em `master._steps` + botão em `gui.LOOPS`/`_task_for` + opção no menu CLI.
- GUI: um loop por vez (`self.running_loop`). Toda atualização de widget a partir de thread passa por `self._ui(...)` (`root.after`). O navegador fica aberto durante o login; `_watch_browser` desabilita os loops se o usuário fechá-lo.
- Seletores do site foram verificados ao vivo em 2026-09-20 e estão como constantes no topo de cada módulo: login = `#logoutlink` presente (`#ylhloggedout` = sessão morta), pontos = `#currentpoints`, sites = `#wh-visit`/`.wh-result`, YouTube e SoundCloud = `#listall a.earn-btn` com `onclick="imageWin(id,'key','segundos',...)"` e resultado em `#showresult`, bônus = "N / M hits" + `.bonus-pill`. Lista vazia é o aviso do próprio site em `#listall` ("There are no more songs to play for points. Check back later!", visto ao vivo em 2026-09-21; `earn.NO_ITEMS_RE`) ou "no websites to visit" (`websites.NO_ITEMS_MARKERS`). Botão ausente é diagnosticado por `utils.why_no_item`: sessão morta (o site manda para `login.php`) vira "not logged in any more", aba sem resposta fica em silêncio (a vigia do navegador da GUI cuida disso), e só página legível, logada e sem aviso vira "... the site may have changed". Se o site mudar, esse é o sintoma; salve o HTML e ajuste as constantes.
- O site só credita pontos se o clique for confiável (`event.isTrusted`), e o timer roda no JavaScript da própria página. Clique sempre com `element.click()` do Selenium, nunca via `execute_script`, e espere o resultado (`.wh-result` / `#showresult`) em vez de dormir um tempo fixo. `bot_logic/earn.py` encapsula isso para YouTube e SoundCloud.
- Bônus resgatável (verificado ao vivo): `.bonus-pill--active` "Unclaimed Points: +N" e `a.buybutton` "Claim N Points Now" com `href="?step=get"`. Após o clique a página `?step=get` ainda mostra o total antigo no cabeçalho; releia os pontos numa navegação nova.
- Likes e follows (lidos ao vivo em 2026-09-21) não são `imageWin`: os pontos vêm de uma ação no outro site, verificada pelo YouLikeHits. YouTube Likes = `youtubelikes.php`, cartões `#listall .cards` com `a.followbutton` (`viewvideo(id,'video','t')`) que carrega um segundo estágio via AJAX; `#FBBox a.earn-btn` abre o vídeo em popup (via linkto.social) e vira `#ylhManualBtn`; o clique nele roda 8 s de "Hang tight" e escreve a resposta em `#FBPoints`. SoundCloud Followers = `soundcloud.php`, cartões `#getpoints .earn-card` (`id="follow<id>"`) com `a.earn-btn` que abre `soundcloud.com/<user>` em popup e revela `a.earn-confirm`; a resposta sai em `#txtHint` depois de "Verifying...". Vazio: "No more tasks at this time. Check back later for more." (`engage.NO_ITEMS_RE`). No outro site: like = `like-button-view-model button` com `aria-pressed`; follow = `.userInfoBar button.sc-button-follow` que ganha `sc-button-selected`; sessão SoundCloud = `.header__userNavUsernameButton` (deslogado = `.header__loginMenu`). Rótulos vêm em pt-BR ("Gostei", "Seguir"): nunca case por texto. O perfil do Chrome precisa estar logado no YouTube e no SoundCloud; `engage.NOT_SIGNED_IN` encerra a passada com aviso e o loop tenta de novo em 1 min. Cartão que falha não é removido pelo site: `engage` tenta cada cartão uma vez por passada (conjunto `tried`). Respostas de verificação vistas ao vivo (2026-09-21, sessão do Marco): sucesso "Success! You followed @user! You got 22 Points!" (SoundCloud) e "You got 21 Points for liking <título>!" (YouTube, título pode vir com `&amp;`, `engage.one_line` decodifica); enquanto o site rechecagem sozinho "Checking again. We couldn't confirm that follow just yet. SoundCloud may still be..."; falha final "Uh oh. We couldn't confirm that follow yet... give SoundCloud a moment and try again, or skip this one." `engage.classify` decide na ordem creditado > pendente > falha (um sucesso pode dizer "loading next video"; um pendente diz "couldn't confirm"); texto desconhecido vira final após 15 s sem mudar; espera total 90 s. YouTube e SoundCloud trocam o botão ANTES de a requisição terminar (UI otimista): fechar o popup na hora perdeu 3 de 4 follows ao vivo; `engage.settle_action` segura o popup 4 s e reconfere o estado antes de fechar.
- `:contains()` não é CSS válido no Selenium; um teste guarda isso.
- O bloqueador de popup do Chrome fica ligado (`--disable-popup-blocking` foi removido e um teste guarda isso): os popups do próprio site vêm do clique confiável e passam; a flag só servia aos pop-unders dos anunciantes. Sites visitados abrem pop-unders durante todo o timer, por isso `utils.WindowGuard` tira um snapshot antes do clique, aceita só a primeira janela nova e fecha o resto a cada poll do `wait_until`.
- `utils.browser_state` distingue `alive`, `unresponsive` e `closed`. Só erro de sessão morta ou processo do chromedriver encerrado é `closed`; timeout ou erro de aba é `unresponsive`, a GUI mostra "Browser Not Responding" e continua vigiando. Visto ao vivo em 2026-09-20: um site abriu 1.100 abas, `window_handles` falhou e a GUI declarou "Browser was closed" com o navegador aberto.

## Armadilhas conhecidas

- Em sessões RDP/VNC o DISPLAY é `:10.0`, não `:0`; `run.sh` o detecta pelos sockets em `/tmp/.X11-unix`. Nunca fixe `:0` em código.
- Para ler o site vivo sem tocar no driver da GUI, abra uma aba própria pela porta de depuração do Chrome do bot (`/json/new`, depois CDP `Runtime.evaluate`), só leitura, e feche-a ao fim. Essa aba NÃO serve para inspecionar o YouTube: em aba de fundo a página de vídeo fica presa em `#watch-page-skeleton` sem botão de like; só renderiza em janela nova (`Target.createTarget` com `newWindow`), que é o que o popup do site abre, então o bot não sofre disso.
- em `landing/`: `output: "export"` em `next.config.ts` foi removido só porque a Vercel o rejeitava. Ao migrar para hospedagem sem Vercel (decisão tomada), reative-o e remova `vercel.json`.

<!-- /bmad:context -->
