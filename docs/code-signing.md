# Code signing with SignPath Foundation

Pinglish installers are built by the GitHub Actions workflow
[`build-installer.yml`](../.github/workflows/build-installer.yml) from the
public source code. Signing uses the free
[SignPath Foundation](https://signpath.org/) program for open-source projects.
Until SignPath is set up, the workflow builds the installer unsigned.

## One-time setup (maintainer)

1. Turn on two-factor authentication for GitHub (required by SignPath).
2. Apply at <https://signpath.org/apply>. After approval, SignPath creates an
   organization for the project and you get access to signpath.io.
3. In SignPath:
   - link the predefined trusted build system **GitHub.com** to the project,
   - install the **SignPath GitHub App** for this repository,
   - create the project with slug `pinglish` and a signing policy
     `release-signing` that requires manual approval,
   - use this artifact configuration (the workflow uploads the installer as a
     ZIP artifact; the installer's product name and version are set by
     `installer/pinglish.iss`):

     ```xml
     <?xml version="1.0" encoding="utf-8"?>
     <artifact-configuration xmlns="http://signpath.io/artifact-configuration/v1">
       <zip-file>
         <pe-file path="Pinglish-Setup-*.exe" product-name="Pinglish">
           <authenticode-sign/>
         </pe-file>
       </zip-file>
     </artifact-configuration>
     ```

   - create an API token for a user with submitter rights.
4. In GitHub, **Settings → Secrets and variables → Actions**:
   - secret `SIGNPATH_API_TOKEN`: the API token,
   - variable `SIGNPATH_ORGANIZATION_ID`: the SignPath organization ID,
   - optional variables `SIGNPATH_PROJECT_SLUG` and
     `SIGNPATH_SIGNING_POLICY_SLUG` if you chose other slugs.

## Releasing a new version

1. Update `APP_VERSION` in `main.py` and `CHANGELOG.md`, commit and push.
2. Create and push a tag, e.g. `git tag v1.03` and `git push origin v1.03`.
3. Create the GitHub release for that tag (or let the workflow attach the file
   to an existing one).
4. Approve the signing request on signpath.io. The workflow waits, then
   attaches the signed installer to the release.

## Requirements from SignPath Foundation that this project follows

- OSI-approved license (MIT), no proprietary components
- Builds only on GitHub-hosted runners from this repository
- Manual approval of every release
- A code signing policy on the project page (README)
- A privacy policy ([PRIVACY.md](../PRIVACY.md)) that the installer shows,
  with an installer option to turn off speech recognition, the only feature
  that sends data (mic audio to Google)
