# Dependency inventory

Baseline: `ai_test@31c5aa6`
Audit date: 2026-09-21

This inventory covers every Git-tracked dependency manifest and build manifest. It is release evidence, not a claim that every dependency license or vulnerability has been approved.

## Coverage summary

- Python: 11 requirements files contain 114 active requirement lines. Sixty-eight use exact `==`/`===` pins and 46 do not. The one `pyproject.toml` declares no runtime dependencies; its build backend requires `setuptools>=70`.
- npm: five `package.json` files declare 44 direct and development dependencies. Five lockfile-version-3 files cover 1,186 package entries across projects; 1,164 entries include a license metadata field. Counts are per lockfile and may include the same package more than once.
- Go: two `go.mod` files exist. `check_FileEncoding` declares no external modules. `mp3_daw` declares two direct and 24 indirect modules and has a `go.sum`.
- Visual C++: one `.vcxproj` declares the Windows SDK, Visual Studio v143 toolset, and static MFC. Vendored JsonCpp 1.7.2 is covered separately by `THIRD_PARTY_NOTICES.md` and its preserved notice.

## Release HOLDs

- Python environments are not fully reproducible while 46 requirement lines remain non-exact and most projects have no transitive lock or hash file.
- npm license metadata is incomplete for 22 lockfile package entries. A metadata field is evidence to review, not a verified license grant.
- Go module versions are pinned, but their upstream license texts and notices have not been collected into a distributable notice report.
- The Windows SDK, MFC, compiler/toolset terms, and the actual Windows build remain human/build-environment checks.
- Vulnerability status is time-sensitive and requires a fresh ecosystem-specific scan at release time.

## Manifest fingerprints

The release guard normalizes CRLF to LF before hashing. Any added, removed, or changed manifest requires this inventory to be reviewed and refreshed.

- `Analysis_music/requirements.txt` — `sha256:651a7e26356d4516a65116d54cf2a99fa447bef464386775b4a7a67d07ea6969`
- `Pexels/requirements.txt` — `sha256:fbf1ce769602b57196ab6985f41396cc6886a9e9461d303a08ebd4b1676a1e9f`
- `ai-webtoon/requirements.txt` — `sha256:29d747912fa04a9ba20ca24d303f991795b34209570706e76839406f9bd5c9a2`
- `ai-webtoon_capcut/pyproject.toml` — `sha256:d3bca9539fd5b3fb8b110780b19918da5d132a28b71e3bde737e29db5b7e1f2a`
- `ai-webtoon_capcut/remotion/package-lock.json` — `sha256:640f01d7677047f62c720767e613251e9aeaedde5f3f304f23b91a5e7e225b2f`
- `ai-webtoon_capcut/remotion/package.json` — `sha256:32e00e069a54e5ea5d98cf57274a32b7d90180a05f1a7c1746a6a99d61cd3fc8`
- `ai-webtoon_capcut/requirements-alignment.txt` — `sha256:4cb247ebbbdc7d70c7402e76a2003ba6153190c06e4794f0c2dff94ec12d1fc5`
- `ai_anime_production/package-lock.json` — `sha256:b3f1486243a504d6ae2d6159cbbf0c1915a3b8684d67ef6633ecf39b606e22ed`
- `ai_anime_production/package.json` — `sha256:884cc59f25969143b5802908b2bacce77eb221e075bd2fb78f93830b10251bcf`
- `check_FileEncoding/go.mod` — `sha256:47ef67dfba053fabda8b14dc0083f98288b4eb9d947dc8b99d8c6885c2e0b94e`
- `extensions/suno-lyric-downloader/package-lock.json` — `sha256:ada34cbb0ac03bc38260ae4f4f2a10786ea55a53a878924b4d39754710fadf80`
- `extensions/suno-lyric-downloader/package.json` — `sha256:bff46ca3c07a720e52c16784e124a394a7ec38ebc76e8c4faffd3d82e2f2d357`
- `imagevideo/package-lock.json` — `sha256:4b22e870a061ce014275d9590c76a131b30a7674222c634e4388610d4e6c598c`
- `imagevideo/package.json` — `sha256:21653f508a303ae77b5d92c41123971e5b3f0dc3ae63cbb8ca0c4dcb595dcc1e`
- `lyrics_tag/requirements.txt` — `sha256:05b055cad237ae3212058d5a2f632537c5bc4a0a6b4d67927778fd11382dd4f8`
- `lyricvideo/package-lock.json` — `sha256:aee90de20d1ec17ee3690376bad6be6a5710b9c40097e7571c5c8859ca65f429`
- `lyricvideo/package.json` — `sha256:4d6f726c5f6ffb5a78b4ec40ec6a08199540cef1a7041ab7407c5b15908c3e15`
- `master_tag/requirements.txt` — `sha256:bfecd982bc85580cc8d449856addf660b4239dd6f11196c869a19952ca64911e`
- `mp3_daw/go.mod` — `sha256:4b1f226fd923b39d5c3a90181b35247c771cbb6e6f2666f2b49325e7a17d3e08`
- `mp3_daw/go.sum` — `sha256:494fced8499befc04d8a0815f8c695a4f7378ef1a614c22b8915a1c51ffb9bed`
- `mp3_daw/requirements.txt` — `sha256:37b4127bcf43843be6f25d5ce216b475d7f59a4d950cdafb90c775c3917bf9e9`
- `mp4_tag/requirements.txt` — `sha256:b74e7a2d0c8a741389435bbfc660896e0a72438c8222a247a3004a81647a3b99`
- `run_game/run_game/run_game.vcxproj` — `sha256:8fe0123f3388b7d1ab57ef65a5d3659a159807c65103f68109b9c2aa7f240afd`
- `security_scanning/requirements.txt` — `sha256:6a6d1592c67a6924938aad78078aa12e2708840fee0eb23fd9f51e318df24758`
- `weather_alarm/requirements.txt` — `sha256:7b29840e2f59a12843a7fa4de3600bae7653e95b9346287e0f68a80c58b2b2c5`
- `windows-port-monitor/requirements.txt` — `sha256:a7308fd9fe79b71f142f646616c2fc8449217b9cd65e311b4fecaad106dd3af4`
