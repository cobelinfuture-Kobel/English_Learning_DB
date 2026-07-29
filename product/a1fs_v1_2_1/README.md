# A1FS V1.2.1 Pull-To-Run Product

Start from the repository root:

```powershell
python -m product.a1fs_v1_2_1.runtime_server start
```

Stop:

```powershell
python -m product.a1fs_v1_2_1.runtime_server stop
```

Status:

```powershell
python -m product.a1fs_v1_2_1.runtime_server status
```

Required environment variables:

```text
A1FS_S11_AUTH_USERNAME
A1FS_S11_AUTH_PASSWORD
A1FS_S11_SESSION_SECRET
```

No install, upgrade, rebuild, PowerShell installer, root rename, pending root activation, or production migration script is required. First start creates `local_state/` from clean seeds when it does not already exist.
