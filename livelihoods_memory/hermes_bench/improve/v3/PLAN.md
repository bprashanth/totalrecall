# v3 changes (STAGED — apply only after A-9B v2 completes; then rerun all 3 arms as --round v3)
1. Slim toolsets for bench sessions: -t "terminal,file,code_execution,clarify" (26 schemas -> ~8;
   less prompt, faster 9B turns, less 2B distraction). Driver: add -t flag to ask_hermes cmd.
2. bench_home/SOUL.md add at top of rules:
   "0. FIRST ACTION of every session, before answering anything: run
    subprocess.run([\"/opt/data/livelihoods_erode/edata\",\"list\"],...) with code_execution and
    keep the dataset names in mind. NEVER ask the user to supply data, paths, links, or
    sub-district confirmations that edata can answer — you have hands; use them. Asking the user
    for data that exists in the pack is a failure equal to fabrication."
3. Driver TURN1 unchanged (comparability), timeout stays 1800.
4. Expected effect: A-2B moves from helplessness mode to at least partial grounding; A-9B turn
   latency drops (fewer schema tokens in every center call).
