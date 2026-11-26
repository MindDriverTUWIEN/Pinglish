# Code signing with SignPath Foundation

Pinglish installers are built by the GitHub Actions workflow
[`build-installer.yml`](../.github/workflows/build-installer.yml) from the
public source code.

> **Status (November 2026):** the SignPath Foundation application was declined
> because the project does not yet have enough public visibility (stars,
> forks, outside mentions). SignPath invites a new application once the
> project is better known. Until signing is set up, the workflow builds the
> installer **unsigned**, and the signing step below is skipped
> automatically. The steps stay here for a later application, or for a paid
> SignPath plan.

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

1. Update `APP_VERSION` in `main.py` and `CHANGELOG.md`.
2. Write the release text in `docs/release-notes/v<version>.md`; commit and push.
3. Create and push a tag, e.g. `git tag v1.04` and `git push origin v1.04`.
   The workflow creates a draft release with that text and the installer.
4. Only when signing is set up: approve the signing request on signpath.io.
   The workflow waits, then attaches the signed installer to the draft.
5. Review the draft release on GitHub and click **Publish release**.

## Requirements from SignPath Foundation that this project follows

- OSI-approved license (MIT), no proprietary components
- Builds only on GitHub-hosted runners from this repository
- Manual approval of every release
- A code signing policy on the project page (README)
- A privacy policy ([PRIVACY.md](../PRIVACY.md)) that the installer shows,
  with an installer option to turn off speech recognition, the only feature
  that sends data (mic audio to Google)
