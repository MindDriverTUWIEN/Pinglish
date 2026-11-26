# Publishing Pinglish on winget

[winget](https://learn.microsoft.com/windows/package-manager/) is the package
manager built into Windows 10 and 11. Once Pinglish is in the winget catalog,
anyone can install or update it with:

```powershell
winget install pinglish        # or: winget install MindDriverTUWIEN.Pinglish
winget upgrade pinglish
```

Installs through winget do not show the SmartScreen "Windows protected your
PC" warning, even though the installer is not code-signed.

The files in `manifests/` describe one Pinglish version for winget. They are
in the same folder layout as Microsoft's catalog repository
[microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs).

## Submit a version (first time and every update)

On a Windows PC, in PowerShell:

1. Install Microsoft's submission tool (once):
   ```powershell
   winget install Microsoft.WingetCreate
   ```
2. Get this repository's files: `git clone https://github.com/MindDriverTUWIEN/Pinglish.git`,
   or on GitHub **Code → Download ZIP** and unzip it.
3. Optional, check the files:
   ```powershell
   winget validate --manifest .\Pinglish\packaging\winget\manifests\m\MindDriverTUWIEN\Pinglish\1.04
   ```
4. Submit:
   ```powershell
   wingetcreate submit .\Pinglish\packaging\winget\manifests\m\MindDriverTUWIEN\Pinglish\1.04
   ```
   The first time, a browser window asks you to sign in to GitHub and allow
   WingetCreate. The tool then forks microsoft/winget-pkgs under your account
   and opens a pull request there.
5. Microsoft's checks run on the pull request (download, virus scan, a test
   install in a virtual machine). A moderator then reviews and merges it.
   This usually takes a few days. Follow the pull request for questions.

## Later versions

After a new release (for example 1.05) has its installer attached:

```powershell
wingetcreate update MindDriverTUWIEN.Pinglish --version 1.05 `
  --urls https://github.com/MindDriverTUWIEN/Pinglish/releases/download/v1.05/Pinglish-Setup-1.05.exe `
  --submit
```

WingetCreate downloads the installer, works out the new checksum and opens the
pull request. Then copy the new files into `manifests/` here as a record.

## Notes

- winget installs silently, for the current user (`/CURRENTUSER`), with the
  installer's default options: speech recognition on, desktop icon on,
  start with Windows off. Speech still sends audio to Google only while the
  mic button is on; see [PRIVACY.md](../../PRIVACY.md).
- The installer's "already installed" questions are answered with their
  defaults in silent mode: reinstall or update goes ahead, a downgrade is
  refused.
- If the checksum in `MindDriverTUWIEN.Pinglish.installer.yaml` no longer
  matches (for example after re-uploading the installer), winget refuses to
  install. Never replace the file of a published release; make a new version.
