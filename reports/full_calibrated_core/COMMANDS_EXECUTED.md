# Commands Executed

- `source .venv/bin/activate`
- `git branch --show-current`
- `git rev-parse HEAD`
- `git status --short`
- `python --version`
- `df -h .`
- `python -m py_compile reports/full_calibrated_core/scripts/run_phase0_phase1.py reports/full_calibrated_core/scripts/full_calibration_utils.py reports/full_calibrated_core/scripts/run_full_calibrated_core.py`
- `python -u reports/full_calibrated_core/scripts/run_full_calibrated_core.py --estimate-only`
- `tmux has-session -t full_calibrated_core 2>/dev/null`
- `tmux new-session -d -s full_calibrated_core "cd /home/soroush/consistency-aware-llm-rankin && source .venv/bin/activate && PYTHONUNBUFFERED=1 python -u reports/full_calibrated_core/scripts/run_full_calibrated_core.py 2>&1 | tee reports/full_calibrated_core/logs/full_calibrated_core.log"`
- `tmux capture-pane -pt full_calibrated_core -S -200`
- `tail -f reports/full_calibrated_core/logs/full_calibrated_core.log`
- `python -m py_compile reports/full_calibrated_core/scripts/run_full_calibrated_core.py`
- `tmux new-session -d -s full_calibrated_core "cd /home/soroush/consistency-aware-llm-rankin && source .venv/bin/activate && PYTHONUNBUFFERED=1 python -u reports/full_calibrated_core/scripts/run_full_calibrated_core.py 2>&1 | tee reports/full_calibrated_core/logs/full_calibrated_core.log"`
