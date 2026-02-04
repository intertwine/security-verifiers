# E1 Heuristic Baseline

Rule-based classifier implemented in `scripts/baselines/run_e1_heuristic.py`.

Core rules:
- Malicious if TOR/C2/SYN_SCAN/brute-force keywords appear
- Benign if STATUS=OK/DNS/ICMP/AUTH_SUCCESS keywords appear
- Port-based fallbacks (e.g., 23/445/3389 → malicious, 53/80/443 → benign)
- Otherwise Abstain
