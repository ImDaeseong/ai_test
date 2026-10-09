# Dependency inventory

Baseline: reviewed `ai_test` working tree after compatible-range dependency refresh
Audit date: 2026-10-09

This inventory covers every Git-tracked dependency manifest and build manifest. It is release evidence, not a claim that every dependency license or vulnerability has been approved.

## Coverage summary

- Python: 11 requirements files contain 114 active requirement lines. Sixty-eight use exact `==`/`===` pins and 46 do not. The one `pyproject.toml` declares no runtime dependencies; its build backend requires `setuptools>=70`.
- npm: five `package.json` files declare 45 direct and development dependencies. Five lockfile-version-3 files cover 1,191 package entries across projects; 1,164 entries include a license metadata field. Counts are per lockfile and may include the same package more than once.
- Go: two `go.mod` files exist. `check_FileEncoding` declares no external modules. `mp3_daw` declares two direct and 24 indirect modules and has a `go.sum`.
- Visual C++: one `.vcxproj` declares the Windows SDK, Visual Studio v143 toolset, and static MFC. Vendored JsonCpp 1.7.2 is covered separately by `THIRD_PARTY_NOTICES.md` and its preserved notice.

## Release HOLDs

- Python environments are not fully reproducible while 46 requirement lines remain non-exact and most projects have no transitive lock or hash file.
- npm license metadata is incomplete for 27 lockfile package entries. A metadata field is evidence to review, not a verified license grant.
- Go module versions are pinned, but their upstream license texts and notices have not been collected into a distributable notice report.
- The Windows SDK, MFC, compiler/toolset terms, and the actual Windows build remain human/build-environment checks.
- Vulnerability status is time-sensitive and requires a fresh ecosystem-specific scan at release time.

## Manifest fingerprints

The release guard normalizes CRLF to LF before hashing. Any added, removed, or changed manifest requires this inventory to be reviewed and refreshed.

- `Analysis_music/requirements.txt` — `sha256:651a7e26356d4516a65116d54cf2a99fa447bef464386775b4a7a67d07ea6969`
- `Pexels/requirements.txt` — `sha256:fbf1ce769602b57196ab6985f41396cc6886a9e9461d303a08ebd4b1676a1e9f`
- `ai-webtoon/requirements.txt` — `sha256:9b8e21ee219b27e7c454d096fc2dc55a8c340936c8b04516e98bb100c12a7993`
- `ai-webtoon_capcut/pyproject.toml` — `sha256:5b6f5e55b6d9dcba3730d947992de934537abd95fb5e3826a9464c367c507098`
- `ai-webtoon_capcut/remotion/package-lock.json` — `sha256:a58010d24258428e449f4044f7ec2b7f3a8794ac6e94735cb22859ae1ca5a1c7`
- `ai-webtoon_capcut/remotion/package.json` — `sha256:6d4f0e948b410b04a5a0c6e67a9704253458f44b930fa9d3f22d199065969671`
- `ai-webtoon_capcut/requirements-alignment.txt` — `sha256:4cb247ebbbdc7d70c7402e76a2003ba6153190c06e4794f0c2dff94ec12d1fc5`
- `ai_anime_production/package-lock.json` — `sha256:9d88814932f4a1153edffb442a0d65b81f6e7161ad977690e35a4cb663c69443`
- `ai_anime_production/package.json` — `sha256:474122468242f14e4ee278177cbd5c67239bee97b9ce4750a916f40e8aad736d`
- `check_FileEncoding/go.mod` — `sha256:47ef67dfba053fabda8b14dc0083f98288b4eb9d947dc8b99d8c6885c2e0b94e`
- `extensions/suno-lyric-downloader/package-lock.json` — `sha256:ada34cbb0ac03bc38260ae4f4f2a10786ea55a53a878924b4d39754710fadf80`
- `extensions/suno-lyric-downloader/package.json` — `sha256:bff46ca3c07a720e52c16784e124a394a7ec38ebc76e8c4faffd3d82e2f2d357`
- `imagevideo/package-lock.json` — `sha256:35aca42ace045eb41ed308ed3b28fa73cef3bfd4b727cbd7e9b977fed69b5285`
- `imagevideo/package.json` — `sha256:cb996c9fd487540d1f3aef94c927452c36d6b1d0105dd45d6262e43983fdd4be`
- `lyrics_tag/requirements.txt` — `sha256:05b055cad237ae3212058d5a2f632537c5bc4a0a6b4d67927778fd11382dd4f8`
- `lyricvideo/package-lock.json` — `sha256:f53ad212a0d183bb748641491e2e5492999acf4ea42f3061627edff80a4702b6`
- `lyricvideo/package.json` — `sha256:a111f2307b644bdd83db80b5eb9a3cca8ce4a532cd45e19e304421526ad632d5`
- `master_tag/requirements.txt` — `sha256:bfecd982bc85580cc8d449856addf660b4239dd6f11196c869a19952ca64911e`
- `mp3_daw/go.mod` — `sha256:4b1f226fd923b39d5c3a90181b35247c771cbb6e6f2666f2b49325e7a17d3e08`
- `mp3_daw/go.sum` — `sha256:494fced8499befc04d8a0815f8c695a4f7378ef1a614c22b8915a1c51ffb9bed`
- `mp3_daw/requirements.txt` — `sha256:37b4127bcf43843be6f25d5ce216b475d7f59a4d950cdafb90c775c3917bf9e9`
- `mp4_tag/requirements.txt` — `sha256:b74e7a2d0c8a741389435bbfc660896e0a72438c8222a247a3004a81647a3b99`
- `run_game/run_game/run_game.vcxproj` — `sha256:8fe0123f3388b7d1ab57ef65a5d3659a159807c65103f68109b9c2aa7f240afd`
- `security_scanning/requirements.txt` — `sha256:6a6d1592c67a6924938aad78078aa12e2708840fee0eb23fd9f51e318df24758`
- `weather_alarm/requirements.txt` — `sha256:7b29840e2f59a12843a7fa4de3600bae7653e95b9346287e0f68a80c58b2b2c5`
- `windows-port-monitor/requirements.txt` — `sha256:a7308fd9fe79b71f142f646616c2fc8449217b9cd65e311b4fecaad106dd3af4`
