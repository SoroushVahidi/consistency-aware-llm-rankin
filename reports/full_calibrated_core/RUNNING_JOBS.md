# Running Jobs

- Session: `full_calibrated_core`
- Status: `completed`
- Notes: `initial launch completed all dataset/protocol computations but failed during CSV export because leave-one-out rows used a mixed schema; the runner was patched to normalize that table and relaunched.`
- Initial launch start time: `2026-07-13T11:54:53-04:00`
- Relaunch start time: `2026-07-13T11:56:43-04:00`
- Completed at: `2026-07-13T11:57:40-04:00`
- Repository root: `/home/soroush/consistency-aware-llm-rankin`
- Branch: `failure-mining-full-records`
- HEAD: `3644801ec4148c70eb018a5a8ea15274685a79ea`
- Environment activation: `source .venv/bin/activate`
- Python executable: `/home/soroush/consistency-aware-llm-rankin/.venv/bin/python`
- Python version: `3.12.3`
- Disk space: `/dev/nvme0n1p5 700G size, 238G used, 428G available, 36% used`
- Estimated runtime: `51.09 seconds` (`0.85 minutes`)
- Estimated output size: `459.2 MB`
- Successful relaunch runtime: `73.11 seconds`
- Log: `reports/full_calibrated_core/logs/full_calibrated_core.log`
- Exact command: `tmux new-session -d -s full_calibrated_core "cd /home/soroush/consistency-aware-llm-rankin && source .venv/bin/activate && PYTHONUNBUFFERED=1 python -u reports/full_calibrated_core/scripts/run_full_calibrated_core.py 2>&1 | tee reports/full_calibrated_core/logs/full_calibrated_core.log"`
