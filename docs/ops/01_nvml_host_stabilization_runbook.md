# 01 - NVML Host Stabilization Runbook (Headless, Production-Safe)

Target host:
- Ubuntu 22.04.5 LTS
- Kernel 6.8.x
- Dual GPU: Tesla M40 24GB + GT1030
- Symptom: `nvidia-smi` -> `Failed to initialize NVML: Unknown Error`

Principle: host stability over experimentation.

## Decision Tree (Symptom -> Checks -> Actions)

### Root Symptom
`nvidia-smi` fails with NVML error.

### Branch 1: Kernel Module Mismatch
- Check:
  - Running kernel vs NVIDIA kernel module version
  - Whether loaded NVIDIA modules were built for current kernel
  - Boot history showing kernel recently changed
- Interpret:
  - If kernel moved forward and module is stale, NVML fails even with installed packages.
- Action:
  - Rebuild/reinstall driver packages via Ubuntu package manager for the current kernel.
  - Reboot and verify module load under the active kernel.

### Branch 2: DKMS Build/Install Failure
- Check:
  - DKMS status output for nvidia modules
  - Package logs showing build error, missing headers, or failed install hooks
- Interpret:
  - Installed driver package exists but no usable module is present.
- Action:
  - Ensure matching kernel headers/toolchain are installed.
  - Re-run package-managed driver reinstall path.
  - Confirm DKMS state becomes "installed" for active kernel.

### Branch 3: Secure Boot / Module Signing Rejection
- Check:
  - Firmware Secure Boot state
  - Kernel logs for module verification/signature errors
- Interpret:
  - Unsigned module blocked -> driver partially installed but nonfunctional.
- Action:
  - Either disable Secure Boot for this host profile or complete MOK signing flow for NVIDIA modules.
  - Reboot and verify modules load without signature rejection.

### Branch 4: nouveau Conflict
- Check:
  - Whether `nouveau` is loaded
  - Initramfs/module blacklist state
  - Kernel log showing nouveau binding before nvidia
- Interpret:
  - Competing driver claims devices before NVIDIA stack stabilizes.
- Action:
  - Apply canonical nouveau blacklist for production NVIDIA hosts.
  - Regenerate initramfs and reboot.
  - Verify only NVIDIA stack drives the GPUs.

### Branch 5: User-Space Library Mismatch
- Check:
  - NVML userspace library paths and package ownership
  - Mixed library versions from stale/manual installs
- Interpret:
  - Kernel module and user-space libs disagree on ABI.
- Action:
  - Remove mixed-source remnants and return to single-source Ubuntu package lineage.
  - Reinstall consistent driver/NVML userspace packages.

### Branch 6: Persistence Daemon / Device Node Issues
- Check:
  - `nvidia-persistenced` status
  - `/dev/nvidia*` node presence/permissions
  - Service logs for startup failures
- Interpret:
  - NVML may fail if device nodes or persistence handling is broken.
- Action:
  - Restore device node creation path from packaged components.
  - Ensure persistence service is enabled for headless operation.

### Branch 7: Dual-GPU Headless Pitfalls (M40 + GT1030)
- Check:
  - GPU enumeration is stable across reboot
  - No unintended display-manager coupling to compute GPU
  - No repeated PCIe/Xid/NVRM errors for either card
- Interpret:
  - Mixed graphics+compute deployments can produce intermittent NVML failures.
- Action:
  - Keep display responsibilities isolated from compute intent where possible.
  - Validate stable GPU ordering and no recurring NVRM faults.

## Evidence Matrix (What to Collect and How to Interpret)

Collect these before changes and after each remediation branch:
- OS/kernel identity and boot history
- NVIDIA package versions and provenance
- DKMS state and recent package hook logs
- Kernel log excerpts: NVRM/Xid/signature/nouveau conflicts
- Loaded module list and versions
- Device nodes under `/dev/nvidia*`
- Persistence service status/log snippets
- `nvidia-smi` stdout/stderr

Healthy indicators:
- NVIDIA modules loaded cleanly for active kernel
- No signature rejection and no nouveau binding conflicts
- `/dev/nvidiactl`, `/dev/nvidia-uvm`, per-GPU nodes exist
- `nvidia-smi` succeeds repeatedly
- No repeated NVRM or Xid errors after stabilization window

Broken indicators:
- Module version mismatch vs running kernel
- DKMS build missing/failed for active kernel
- Secure Boot verification failures
- Mixed NVML library versions outside package manager
- Recurrent NVRM/Xid or disappearing device nodes

## Minimal Remediation Path Per Branch

1. Always snapshot evidence before changes.
2. Apply one branch at a time, reboot if branch requires it.
3. Re-run deterministic verification checklist (below).
4. If failed, continue to next branch in root-cause order.

## Clean Purge + Reinstall (Ubuntu Packages Only)

Use only if branch-level repairs fail.
- Remove NVIDIA user-space and kernel components installed via apt lineage.
- Remove stale residual config that forces incompatible module/library state.
- Reinstall a single, pinned Ubuntu driver branch (535 family unless policy changes).
- Ensure kernel headers and DKMS dependencies are present.
- Reboot and re-verify.

Escalation note:
- `.run` installer is disallowed in baseline operations.
- Only consider it as a formally approved last resort after package-path exhaustion and rollback plan approval.

## Verification Checklist (Must Pass, Deterministic)

Run after every remediation and across at least one reboot; final acceptance requires three clean boots.

1. `nvidia-smi` returns successfully with both GPUs enumerated.
2. NVIDIA kernel modules are loaded and version-consistent with installed package branch.
3. `nouveau` is not active.
4. No Secure Boot module rejection events in kernel logs.
5. `/dev/nvidia*` nodes exist and are stable.
6. Persistence daemon is active and not flapping.
7. No repeated NVRM/Xid error pattern over a defined observation window.

Pass criteria:
- All seven checks pass on three consecutive reboots.

## Good State Definition (Headless + Dual GPU)
- Stable NVIDIA module stack for active kernel
- Stable NVML across reboots
- Tesla M40 visible and usable for compute workloads
- GT1030 coexists without recurring driver contention
- Persistence enabled and no repetitive kernel-level GPU errors

## Do Not Do These (Foot-Guns)
- Do not mix Ubuntu-packaged driver with manual `.run` install artifacts.
- Do not partially purge packages without clearing stale libs/config.
- Do not skip kernel-header alignment on DKMS hosts.
- Do not assume one successful `nvidia-smi` is enough; require multi-boot stability.
- Do not introduce Docker GPU runtime during NVML instability investigation.
- Do not change multiple branches at once (prevents root-cause isolation).
