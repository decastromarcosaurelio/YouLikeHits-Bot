<!-- bmad:context -->
<!-- Verified 2026-09-20 against working tree after review session (base 613141f). Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## YouLikeHits-Bot

Bot em Python que automatiza tarefas de troca no YouLikeHits.com via Selenium com `undetected-chromedriver`, com GUI em customtkinter e menu CLI. É um fork de um repositório defasado em modernização completa. A landing page em `landing/` é um app Next.js 16 separado. Artefatos de planejamento BMAD ficam em `_bmad-output/` (local, fora do git).

## Política

- Mantenha `_bmad/`, `_bmad-output/`, `.agents/` e `.claude/` no `.gitignore`.

## Onde ficam as coisas

- Loops do bot: um módulo por tarefa em `bot_logic/`; fluxo comum YouTube/SoundCloud em `bot_logic/earn.py`; fábrica do navegador em `bot_logic/utils.py`; GUI em `gui/app.py`; menu CLI em `main_cli.py`.
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
- Configuração do usuário fica em `settings.json` na raiz (ignorado pelo git), lida e validada por `bot_logic/settings.py`; nunca leia o arquivo direto. `_run_master_task` aceita `settings=`; a GUI salva os campos de espera ao iniciar o Master Loop, o CLI pergunta antes de iniciar.
- GUI: um loop por vez (`self.running_loop`). Toda atualização de widget a partir de thread passa por `self._ui(...)` (`root.after`). O navegador fica aberto durante o login; `_watch_browser` desabilita os loops se o usuário fechá-lo.
- Seletores do site foram verificados ao vivo em 2026-09-20 e estão como constantes no topo de cada módulo: login = `#logoutlink` presente (`#ylhloggedout` = sessão morta), pontos = `#currentpoints`, sites = `#wh-visit`/`.wh-result`, YouTube e SoundCloud = `#listall a.earn-btn` com `onclick="imageWin(id,'key','segundos',...)"` e resultado em `#showresult`, bônus = "N / M hits" + `.bonus-pill`. Se o site mudar, o sintoma é "Not logged in" ou "No ... available" com a página visivelmente cheia; salve o HTML e ajuste as constantes.
- O site só credita pontos se o clique for confiável (`event.isTrusted`), e o timer roda no JavaScript da própria página. Clique sempre com `element.click()` do Selenium, nunca via `execute_script`, e espere o resultado (`.wh-result` / `#showresult`) em vez de dormir um tempo fixo. `bot_logic/earn.py` encapsula isso para YouTube e SoundCloud.
- Bônus resgatável (verificado ao vivo): `.bonus-pill--active` "Unclaimed Points: +N" e `a.buybutton` "Claim N Points Now" com `href="?step=get"`. Após o clique a página `?step=get` ainda mostra o total antigo no cabeçalho; releia os pontos numa navegação nova.
- `:contains()` não é CSS válido no Selenium; um teste guarda isso.
- O bloqueador de popup do Chrome fica ligado (`--disable-popup-blocking` foi removido e um teste guarda isso): os popups do próprio site vêm do clique confiável e passam; a flag só servia aos pop-unders dos anunciantes. Sites visitados abrem pop-unders durante todo o timer, por isso `utils.WindowGuard` tira um snapshot antes do clique, aceita só a primeira janela nova e fecha o resto a cada poll do `wait_until`.
- `utils.browser_state` distingue `alive`, `unresponsive` e `closed`. Só erro de sessão morta ou processo do chromedriver encerrado é `closed`; timeout ou erro de aba é `unresponsive`, a GUI mostra "Browser Not Responding" e continua vigiando. Visto ao vivo em 2026-09-20: um site abriu 1.100 abas, `window_handles` falhou e a GUI declarou "Browser was closed" com o navegador aberto.

## Armadilhas conhecidas

- Em sessões RDP/VNC o DISPLAY é `:10.0`, não `:0`; `run.sh` o detecta pelos sockets em `/tmp/.X11-unix`. Nunca fixe `:0` em código.
- em `landing/`: `output: "export"` em `next.config.ts` foi removido só porque a Vercel o rejeitava. Ao migrar para hospedagem sem Vercel (decisão tomada), reative-o e remova `vercel.json`.

<!-- /bmad:context -->
