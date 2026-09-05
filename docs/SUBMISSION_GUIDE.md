# Atlas code submission guide

## Scope

This handoff contains the runnable Atlas proof of concept, source, dependency specifications, launchers, tests, selected evaluation reports and documentation. The organiser's code-package size limit is **5 GB**. The final slide deck (at most ten slides) and video (at most five minutes) are prepared and submitted separately; the included outlines do not replace them.

## Reviewer launch route

1. Extract the archive to a normal writable folder; do not run it from inside the ZIP.
2. Follow the three installation/start commands for your platform in the top-level [README](../README.md).
3. Run `python launch.py` using that project's virtual-environment Python. Demo is the default and requires no AWS credentials. Open the URL printed in the terminal.
4. Click **Use example learning goals / 填入演示学习需求**, inspect the supported example and generate a route. Follow the README's eight-step route through book identity, a reading path, conversations, mixed practice, progress and history. Use a new profile to try another goal without overwriting that route.
5. Run `python launch.py --check` for prerequisite checks; use `--port 8502` if the normal port is occupied. Stop the service with Ctrl+C.

The wrappers `start.ps1` and `start.sh` offer the same launch mode after dependencies are installed. Neither installs packages automatically. A clean machine needs internet access for dependency installation. Source websites and external book images/links may also need a network connection.

## 中文快速启动

1. 安装 Python 3.11 或更新版本，先解压代码包，再按 [README](../README.md) 开头对应系统的三条命令创建虚拟环境、安装依赖并启动。首次安装依赖需要联网。
2. 安装完成后，Windows 可运行 `powershell -File start.ps1`，macOS/Linux/WSL 可运行 `sh start.sh`。默认是明确标注的演示模式，不需要 AWS；它不是实时模型回答质量演示。
3. 打开终端显示的网址（默认 `http://localhost:8501`），在设置中切换中文，点击「填入演示学习需求」，再生成路径。可体验选书、进度、混合自测与历史方案；结束时按 Ctrl+C。
4. 若端口被占用，Windows 加 `-Port 8502`，其他系统加 `--port 8502`。真实模式需自行配置服务凭据，再使用虚拟环境 Python 运行 `launch.py --mode live`，会产生外部请求并可能计费。
5. 需要完整本地验收时，先用虚拟环境 Python 安装 `requirements-dev.txt`，再在项目根目录运行 `python -m scripts.preflight`。所有 `python -m scripts.<名称>` 命令都应从项目根目录执行；这里的 `python` 指该虚拟环境的解释器。

## Demonstration is not live AI

| Mode | What the reviewer sees | What it proves |
| --- | --- | --- |
| Default demo | Bundled catalogue examples, local rule-based behaviour, persistent UI, mixed objective practice and labelled limitations. | The product flow and local application behaviour are runnable without a developer's AWS account. It does not establish model response quality or live retrieval availability. |
| Live, explicitly selected | Actual catalogue/provider requests using the operator's configured services; unavailable sources or model calls are surfaced. | Behaviour for those requests at that time, not universal accuracy or uptime. |
| Included evaluation reports | Dated deterministic or historical live samples, each labelled. | Only the mode, sample and source version actually exercised. A proxy or passing schema is not a human relevance score. |

To exercise live mode, configure your own `.env`/AWS profile or environment as described in the README, then run `python launch.py --mode live`. Credentials and account access are intentionally not shipped. Live calls may cost money and transmit learner-supplied text to the configured model provider.

## Final-package checklist

- Verify the archive opens, its size is below 5 GB and its recorded checksum matches the file being delivered.
- Check that `README.md`, `launch.py`, both platform launchers, dependency files, `app.py`, `src/`, assets, data fixtures and the selected validation material are included.
- Exclude `.env`, `.streamlit/secrets.toml`, AWS credential/config files, private keys, all local/QA SQLite databases and sidecars, `.venv`, caches and private logs. **Never ZIP the development directory blindly.** `.gitignore` does not remove files from a ZIP.
- Do not ship `outputs/` or development `qa_*` scripts. Some dated QA notes refer to raw development results in `outputs/`; those raw artefacts are **not included in this submission package**.
- Ensure the final package contains no personal learning profiles or private conversation history. New runtime databases are created locally after launch.
- Install `requirements-dev.txt` (or use `uv sync --frozen`), run the local preflight against the final source and inspect every check. Keep the generated report, with its date and scope. Do not label a historical live report as a new acceptance run.
- Test startup from the extracted package in a clean environment. Passing tests in the developer's original virtual environment is not the same check.
- If providing a repository URL instead of or alongside the ZIP, verify the final files are committed and the intended reviewers can clone the repository. Do not publish secrets to make live mode easier to run.

The release process records the final size, checksum and validation outcome; this guide intentionally does not hardcode a pass count or claim a release gate has already passed.

## Implementation and quality disclosure

Atlas uses a fixed, bounded orchestration graph, model-assisted assessment and explicit learner-approved actions. It is not an unrestricted self-reflecting agent. Profile IDs organise local work; they do not authenticate users or isolate hostile tenants. Keep the demo on a trusted local machine and do not use real sensitive data in an unauthenticated public deployment.

Book identity checks and source labels are helpful product safeguards, not guarantees of relevance or full-book knowledge. Questions, answer keys and model explanations remain fallible. General fallback practice is not a successful specialised assessment, and correct objective marking does not establish that a generated key is factually right. No completed blind human study or validated learning-gain claim is implied.

For detail, read [architecture](architecture.md), [delivery readiness](hackathon_readiness.md), [Topic 4 cross-check](topic4_alignment.md) and the dated [learning/practice QA notes](qa-learning-focus-mixed-practice-2026-09-05.md). Older presentation notes and historical reports should be read with their dates and these current boundaries, not as automatic proof of final-package compliance.
