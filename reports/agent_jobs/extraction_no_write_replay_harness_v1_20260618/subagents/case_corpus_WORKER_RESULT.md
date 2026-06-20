# Case Corpus Worker Result

Status: DONE_WITH_RISK

Read-only verification completed. No files were edited and no extraction was
run by this worker.

Verified all six source PDFs exist locally:

- WHC `9640d9f1-a45b-492d-8df5-9bad0f46431c`
- CTN `dec0b5f1-e6d2-48d8-ad9d-16ffd540ee39`
- HUB `419bcca8-213e-4706-8962-8e3bd8adf091`
- LBL `551c6b84-1053-405c-a833-4ecc018e2045`
- AZJ `488d6f1a-0180-4fca-8dcf-c4cdfc0f342e`
- NSR `f2240712-9dde-41e0-88fa-29c1a0080dab`

The worker recommended changing LBL from `hub_negative_guard` to a repaired
companion-period guard. That correction was applied in the manifest.

DATA_MISSING noted by worker: no current no-write replay was run by the worker;
CTN/HUB older saved-artifact inputs still lack some row-ref or extraction-run
fields, but this does not block source-path and period metadata certification.
