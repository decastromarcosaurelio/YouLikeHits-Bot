<!-- bmad:context -->
<!-- Verified 2026-09-20 against working tree after review session (base 613141f). Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## YouLikeHits-Bot

Bot em Python que automatiza tarefas de troca no YouLikeHits.com via Selenium com `undetected-chromedriver`, com GUI em customtkinter e menu CLI. É um fork de um repositório defasado em modernização completa. A landing page em `landing/` é um app Next.js 16 separado. Artefatos de planejamento BMAD ficam em `_bmad-output/` (local, fora do git).

## Política

- Nunca apague nem comite `chrome_profile/`; ele guarda a sessão logada do YouLikeHits e o login é sempre manual no navegador.
- Mantenha `_bmad/`, `_bmad-output/`, `.agents/` e `.claude/` fora do git; não use `git add -A` na raiz.

## Onde ficam as coisas

- Loops do bot: um módulo por tarefa em `bot_logic/`; fábrica do navegador em `bot_logic/utils.py`; GUI em `gui/app.py`; menu CLI em `main_cli.py`.
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
- GUI: um loop por vez (`self.running_loop`). Toda atualização de widget a partir de thread passa por `self._ui(...)` (`root.after`). O navegador fica aberto durante o login; `_watch_browser` desabilita os loops se o usuário fechá-lo.
- Seletores CSS do site (`.followbutton`, `.buybutton`, `[class*='point']`, textos "you have made", "no websites currently") não foram validados contra o YouLikeHits ao vivo nesta base; ao mexer neles, teste com sessão real. `:contains()` não é CSS válido no Selenium; um teste guarda isso.

## Armadilhas conhecidas

- Em sessões RDP/VNC o DISPLAY é `:10.0`, não `:0`; `run.sh` o detecta pelos sockets em `/tmp/.X11-unix`. Nunca fixe `:0` em código.
- em `landing/`: `output: "export"` em `next.config.ts` foi removido só porque a Vercel o rejeitava. Ao migrar para hospedagem sem Vercel (decisão tomada), reative-o e remova `vercel.json`.

<!-- /bmad:context -->
