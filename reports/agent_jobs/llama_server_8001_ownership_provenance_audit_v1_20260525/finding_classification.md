# Finding Classification

| Finding | Class | Follow-up |
|---|---|---|
| Live `:8001` process exists and parent/child topology is recorded. | NO_FOLLOWUP | Audit evidence preserved. |
| Expected user units are inactive/dead with `MainPID=0`. | FOLLOWUP_REQUIRED | #113 |
| Definitive launcher/owner beyond PPID 996 remains unresolved. | DATA_MISSING | #113 |
| GPU guard could not obtain `nvidia-smi` memory details, but exited 0. | DATA_MISSING | #113 if owner audit needs VRAM correlation. |
