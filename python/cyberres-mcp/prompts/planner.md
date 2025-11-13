Given a ValidationRequest JSON, choose a minimal ordered set of tools to validate the target.

1. Always check basic network reachability using ``tcp_portcheck`` for the relevant ports (SSH for VMs, 1521 for Oracle, 27017 for Mongo).
2. Based on the ``resourceType`` field, include only the tools that apply:
   * ``vm``: ``vm_linux_uptime_load_mem`` → ``vm_linux_fs_usage`` → ``vm_linux_services``.
   * ``oracle``: ``db_oracle_connect`` → ``db_oracle_tablespaces``.
   * ``mongo``: ``db_mongo_connect`` → (optionally) ``db_mongo_rs_status`` if a URI is provided.

Output your plan as JSON in the form ``{"steps":[{"tool":"tool_name","args":{...}}, ...]}`` with the tool names and arguments filled in.