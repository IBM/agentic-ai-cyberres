Given the outputs of executed tools and a corresponding acceptance profile, compute a pass/fail status and an overall score.

* For VM checks:
  * ``vm_linux_fs_usage``: for each filesystem, if ``use_pct`` > ``fs_max_pct`` from the acceptance profile, mark FAIL for that filesystem.
  * ``vm_linux_uptime_load_mem``: parse ``MemTotal`` and ``MemFree`` from the output; compute free percentage. If free percentage < ``mem_min_free_pct``, mark FAIL.
  * ``vm_linux_services``: if any ``required_services`` are reported as missing, mark FAIL.
* For Oracle DB checks:
  * ``db_oracle_connect``: if ``ok`` is false, mark FAIL.
  * ``db_oracle_tablespaces``: for each tablespace, if ``free_mb`` / total MB < ``tablespace_min_free_pct``, mark FAIL.
* For MongoDB checks:
  * ``db_mongo_connect``: if ``ok`` is false, mark FAIL.
  * ``db_mongo_rs_status``: if ``myState`` is not in ``allowed_states`` from the acceptance profile, mark FAIL.

Compute an integer score (0–100) by dividing the number of passed checks by the total number of checks and multiplying by 100. List failures with a short message explaining the reason.