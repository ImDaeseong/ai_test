"""전체 산출물 검증. 재생성은 --regenerate를 지정할 때만 수행한다."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json, os, re, subprocess, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
from policy_safety import policy_risk_hits

# Windows 콘솔 한글/특수문자 출력 보장
_reconfigure = getattr(sys.stdout, "reconfigure", None)
if _reconfigure:
    try:
        _reconfigure(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        pass

# 최신 mp3 포함 곡 (중복 제거)
SONG_INPUTS = [
    ("그대로 접힌 양말", "output/web_inputs/20260607-071112"),
    ("들리잖아", "output/web_inputs/20260607-071626"),
    ("오늘은 좀 괜찮아", "output/web_inputs/20260607-072451"),
    ("환승역", "output/web_inputs/20260607-073033"),
    ("아직 우리", "output/web_inputs/20260607-072207"),
    ("사랑이 다가올 때", "output/web_inputs/20260607-072038"),
    ("이별을 배운다", "output/web_inputs/20260607-072631"),
    ("하나야", "output/web_inputs/20260607-073008"),
    ("차가운 안녕", "output/web_inputs/20260607-072852"),
    ("날개짓", "output/web_inputs/20260607-071312"),
    ("다시 마주한 순간", "output/web_inputs/20260607-071602"),
    ("위험해", "output/web_inputs/20260607-072546"),
    ("떠나고 싶어", "output/web_inputs/20260607-071643"),
    ("오늘도 네 곁을 맴돌아", "output/web_inputs/20260607-072432"),
    ("헤어진 날", "output/web_inputs/20260607-073027"),
    ("100 Seconds", "output/web_inputs/20260607-070846"),
    ("아무 일도 일어나지 않는 하루", "output/web_inputs/20260607-072153"),
    ("우산 없는 날", "output/web_inputs/20260607-072522"),
    ("나 혼자", "output/web_inputs/20260607-071212"),
    ("너는 완벽했어", "output/web_inputs/20260607-071407"),
    ("그 시절이 그립다", "output/web_inputs/20260607-071030"),
    ("같은 하늘 다른 세상", "output/web_inputs/20260607-070939"),
    ("별빛 미소", "output/web_inputs/20260607-071947"),
    ("너한테 가고 있어", "output/web_inputs/20260607-071458"),
    ("가끔 하늘을 봐", "output/web_inputs/20260607-070925"),
    ("감기", "output/web_inputs/20260607-070932"),
    ("고백", "output/web_inputs/20260607-070950"),
    ("구독취소", "output/web_inputs/20260607-071019"),
    ("그냥 걸어", "output/web_inputs/20260607-071048"),
    ("기억나", "output/web_inputs/20260607-071148"),
    ("10년 후에도", "output/web_inputs/20260607-070851"),
    ("Lazy Afternoon", "output/web_inputs/20260607-070856"),
    ("Off-Line", "output/web_inputs/20260607-070904"),
    ("Routine", "output/web_inputs/20260607-070910"),
    ("UPGRADE", "output/web_inputs/20260607-070917"),
    ("계절의 끝에서", "output/web_inputs/20260607-070944"),
    ("골목길 돌아서", "output/web_inputs/20260607-070956"),
    ("괜찮다 했는데", "output/web_inputs/20260607-071002"),
    ("괜찮아, 잘 지내 다 잊은 척", "output/web_inputs/20260607-071008"),
    ("괜찮아", "output/web_inputs/20260607-071013"),
    ("그 소녀", "output/web_inputs/20260607-071025"),
    ("그 조각", "output/web_inputs/20260607-071037"),
    ("그게 사랑이었어", "output/web_inputs/20260607-071043"),
    ("그냥 살아", "output/web_inputs/20260607-071054"),
    ("그녀가 알고 싶다", "output/web_inputs/20260607-071059"),
    ("그녀를 기다리며", "output/web_inputs/20260607-071104"),
    ("그대로의 나로", "output/web_inputs/20260607-071119"),
    ("그때의 우린 참 예뻤는데", "output/web_inputs/20260607-071125"),
    ("그래도 와줘", "output/web_inputs/20260607-071129"),
    ("기분 좋은 날", "output/web_inputs/20260607-071143"),
    ("기억의 숲에서 춤추다", "output/web_inputs/20260607-071154"),
    ("나 혼자 이 길을 걷고 있어", "output/web_inputs/20260607-071206"),
    ("나는 다시", "output/web_inputs/20260607-071220"),
    ("나는 쉬는 중", "output/web_inputs/20260607-071227"),
    ("나를 안아 주세요", "output/web_inputs/20260607-071233"),
    ("나만 빼고", "output/web_inputs/20260607-071239"),
    ("나만 아는 너", "output/web_inputs/20260607-071246"),
    ("나만 홀로", "output/web_inputs/20260607-071252"),
    ("나만의 세상", "output/web_inputs/20260607-071258"),
    ("나의 속도", "output/web_inputs/20260607-071305"),
    ("남겨진 우산", "output/web_inputs/20260607-071318"),
    ("내 방식대로", "output/web_inputs/20260607-071322"),
    ("내 선 안에 있어", "output/web_inputs/20260607-071327"),
    ("내가 사는 법", "output/web_inputs/20260607-071332"),
    ("내려놔", "output/web_inputs/20260607-071338"),
    ("너 이미 빛나고 있어", "output/web_inputs/20260607-071344"),
    ("너는 내 장마였나 봐", "output/web_inputs/20260607-071351"),
    ("너는 모르겠지", "output/web_inputs/20260607-071356"),
    ("너는 어쩌다", "output/web_inputs/20260607-071401"),
    ("너라는 완성", "output/web_inputs/20260607-071413"),
    ("너라는 정답", "output/web_inputs/20260607-071418"),
    ("너를 사랑하게 됐어", "output/web_inputs/20260607-071424"),
    ("너를 지우려해", "output/web_inputs/20260607-071430"),
    ("너무 좋아", "output/web_inputs/20260607-071435"),
    ("너에게 가는 길", "output/web_inputs/20260607-071440"),
    ("너와 나 사이", "output/web_inputs/20260607-071446"),
    ("너의 여름", "output/web_inputs/20260607-071452"),
    ("넌 나의 햇살", "output/web_inputs/20260607-071504"),
    ("네 일상 한구석에 내가 있기를", "output/web_inputs/20260607-071511"),
    ("눈물이 난다", "output/web_inputs/20260607-071521"),
    ("늘 가던 카페 같은 시간에", "output/web_inputs/20260607-071529"),
    ("다 뱉어", "output/web_inputs/20260607-071545"),
    ("다가오지마", "output/web_inputs/20260607-071550"),
    ("다른 사람", "output/web_inputs/20260607-071557"),
    ("다시 사랑해 줘", "output/web_inputs/20260607-071607"),
    ("대답 없는 이름", "output/web_inputs/20260607-071614"),
    ("덜 마신 커피처럼", "output/web_inputs/20260607-071620"),
    ("디저트", "output/web_inputs/20260607-071632"),
    ("따뜻한 겨울", "output/web_inputs/20260607-071637"),
    ("또 네 생각이 나", "output/web_inputs/20260607-071650"),
    ("또 일어서", "output/web_inputs/20260607-071710"),
    ("마트에서 네 우산을", "output/web_inputs/20260607-071718"),
    ("만약에 우리", "output/web_inputs/20260607-071727"),
    ("말하지 못한 그리움", "output/web_inputs/20260607-071734"),
    ("멈추지 마", "output/web_inputs/20260607-071755"),
    ("멈춘 채로", "output/web_inputs/20260607-071801"),
    ("멈출 수 없어", "output/web_inputs/20260607-071807"),
    ("멋대로 간다", "output/web_inputs/20260607-071816"),
    ("모든 게 좋았어", "output/web_inputs/20260607-071824"),
    ("모르겠어", "output/web_inputs/20260607-071833"),
    ("모르는 척", "output/web_inputs/20260607-071842"),
    ("무너져 내려", "output/web_inputs/20260607-071849"),
    ("문 앞에 두고 온 나의 미련들", "output/web_inputs/20260607-071855"),
    ("미완성된 어른", "output/web_inputs/20260607-071900"),
    ("미쳐버려", "output/web_inputs/20260607-071906"),
    ("믿어봐요", "output/web_inputs/20260607-071912"),
    ("발걸음", "output/web_inputs/20260607-071919"),
    ("버스 창 얼굴", "output/web_inputs/20260607-071931"),
    ("번지는 여름", "output/web_inputs/20260607-071938"),
    ("보이지 않아도, 여기 있어", "output/web_inputs/20260607-071955"),
    ("봄에 내리는 비", "output/web_inputs/20260607-072001"),
    ("북극성", "output/web_inputs/20260607-072008"),
    ("비겁한 변명", "output/web_inputs/20260607-072014"),
    ("비밀번호", "output/web_inputs/20260607-072021"),
    ("사랑에 빠져", "output/web_inputs/20260607-072026"),
    ("사랑을 놓아", "output/web_inputs/20260607-072034"),
    ("사랑하면 안 되냐고", "output/web_inputs/20260607-072046"),
    ("산책", "output/web_inputs/20260607-072053"),
    ("상처", "output/web_inputs/20260607-072059"),
    ("새로운 시작", "output/web_inputs/20260607-072105"),
    ("생각대로 안 돼서 더", "output/web_inputs/20260607-072110"),
    ("생각의 지도", "output/web_inputs/20260607-072117"),
    ("서툰 연인", "output/web_inputs/20260607-072122"),
    ("슈퍼맨도 아프다", "output/web_inputs/20260607-072127"),
    ("습관처럼", "output/web_inputs/20260607-072133"),
    ("시원한 바람", "output/web_inputs/20260607-072139"),
    ("식어버린 커피처럼", "output/web_inputs/20260607-072145"),
    ("아직 안 읽은 톡", "output/web_inputs/20260607-072200"),
    ("아직도 그 버스는", "output/web_inputs/20260607-072215"),
    ("아직은", "output/web_inputs/20260607-072223"),
    ("안아줘", "output/web_inputs/20260607-072230"),
    ("알람 소리", "output/web_inputs/20260607-072240"),
    ("알람 소리에 또 눈을 떠", "output/web_inputs/20260607-072246"),
    ("어느 별에서 왔니", "output/web_inputs/20260607-072252"),
    ("어쩌다 마주친", "output/web_inputs/20260607-072257"),
    ("어쩌면 행복은", "output/web_inputs/20260607-072303"),
    ("언제나 너", "output/web_inputs/20260607-072310"),
    ("여름 끝나기 전에", "output/web_inputs/20260607-072316"),
    ("여름밤의 별", "output/web_inputs/20260607-072328"),
    ("여름아 부탁해", "output/web_inputs/20260607-072335"),
    ("영원한 지금", "output/web_inputs/20260607-072346"),
    ("예의 있게 이별하는 법", "output/web_inputs/20260607-072352"),
    ("오고 간다", "output/web_inputs/20260607-072357"),
    ("오늘 나는 조금 달랐다", "output/web_inputs/20260607-072403"),
    ("오늘 너의 마음은 맑음", "output/web_inputs/20260607-072409"),
    ("오늘 여기", "output/web_inputs/20260607-072416"),
    ("오늘 참 예쁘다", "output/web_inputs/20260607-072421"),
    ("오늘도 너야", "output/web_inputs/20260607-072428"),
    ("오늘도 반했어", "output/web_inputs/20260607-072437"),
    ("오늘따라 더", "output/web_inputs/20260607-072445"),
    ("오늘이 가장 좋아", "output/web_inputs/20260607-072458"),
    ("오후의 여백", "output/web_inputs/20260607-072503"),
    ("우리가 건너는 겨울", "output/web_inputs/20260607-072510"),
    ("우리들의 발걸음", "output/web_inputs/20260607-072516"),
    ("우울한 아침", "output/web_inputs/20260607-072527"),
    ("운이 없게", "output/web_inputs/20260607-072534"),
    ("웃어본다", "output/web_inputs/20260607-072540"),
    ("유일한 사랑", "output/web_inputs/20260607-072554"),
    ("이 사랑 결제 되나요", "output/web_inputs/20260607-072600"),
    ("이 정도면 괜찮아", "output/web_inputs/20260607-072607"),
    ("이건 미련이야", "output/web_inputs/20260607-072614"),
    ("이방인", "output/web_inputs/20260607-072619"),
    ("이벤트", "output/web_inputs/20260607-072625"),
    ("이상한 세상", "output/web_inputs/20260607-072637"),
    ("이상한 소문", "output/web_inputs/20260607-072642"),
    ("이제는 남이 된 우리", "output/web_inputs/20260607-072648"),
    ("이제는 안녕", "output/web_inputs/20260607-072653"),
    ("일요일이 싫어", "output/web_inputs/20260607-072658"),
    ("자동문 앞에서", "output/web_inputs/20260607-072703"),
    ("작은 비누", "output/web_inputs/20260607-072709"),
    ("잘 가", "output/web_inputs/20260607-072714"),
    ("잘못된 선택", "output/web_inputs/20260607-072720"),
    ("점심", "output/web_inputs/20260607-072730"),
    ("젖은 신발끝", "output/web_inputs/20260607-072736"),
    ("젖은 운동화", "output/web_inputs/20260607-072743"),
    ("제발 사랑한다고 말해", "output/web_inputs/20260607-072750"),
    ("제자리", "output/web_inputs/20260607-072756"),
    ("조금 더 있어", "output/web_inputs/20260607-072802"),
    ("종이 한 장", "output/web_inputs/20260607-072809"),
    ("주파수", "output/web_inputs/20260607-072815"),
    ("중력", "output/web_inputs/20260607-072821"),
    ("지나간 이야기", "output/web_inputs/20260607-072827"),
    ("지나친 향기에 너를 느꼈어", "output/web_inputs/20260607-072833"),
    ("지우개", "output/web_inputs/20260607-072839"),
    ("지워진 지문", "output/web_inputs/20260607-072845"),
    ("창밖을 봐 — 날씨 너무 좋아", "output/web_inputs/20260607-072904"),
    ("첫 번째 봄", "output/web_inputs/20260607-072912"),
    ("첫눈은 날리고", "output/web_inputs/20260607-072918"),
    ("첫눈의 설렘", "output/web_inputs/20260607-072925"),
    ("충분한 오늘", "output/web_inputs/20260607-072932"),
    ("층 사이에서", "output/web_inputs/20260607-072939"),
    ("침대가 나를 잡아", "output/web_inputs/20260607-072945"),
    ("텅 빈 레코드", "output/web_inputs/20260607-072951"),
    ("투명한 마음", "output/web_inputs/20260607-072957"),
    ("하나뿐인 취미", "output/web_inputs/20260607-073004"),
    ("행복을 찾아서", "output/web_inputs/20260607-073015"),
    ("헐거운 이어폰", "output/web_inputs/20260607-073020"),
    ("횡단보도", "output/web_inputs/20260607-073040"),
    ("휴가 모드", "output/web_inputs/20260607-073046"),
    ("흐르는 대로 -f", "output/web_inputs/20260607-073051"),
    ("흐르는 대로", "output/web_inputs/20260607-073058"),
    ("흔적", "output/web_inputs/20260607-073110"),
    ("힘들때웃어본다", "output/web_inputs/20260607-073116"),
    ("녹슨 자전거", "output/web_inputs/20260607-071516"),
    ("늘어진 카세트처럼", "output/web_inputs/20260607-071537"),
    ("여름밤", "output/web_inputs/20260607-072322"),
    ("여섯 시", "output/web_inputs/20260607-072341"),
    ("창밖에 눈이 와", "output/web_inputs/20260607-072858"),
    ("흐린 밤", "output/web_inputs/20260607-073105"),
    ("맞잡은 두 손", "output/web_inputs/20260607-071741"),
    ("방과 후", "output/web_inputs/20260607-071925"),
    ("또 눈치만 보네", "output/web_inputs/20260607-071658"),
    ("그래서 더 좋아", "output/web_inputs/20260607-215349"),
    ("길을 잃은 별", "output/web_inputs/20260607-071159"),
]

def validate_scene_list(name):
    path = "storyboard/scene_list.json"
    if not os.path.exists(path):
        return 0, [f"scene_list.json 없음"]
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    scenes = data.get("scenes", [])
    issues = []
    for s in scenes:
        n = s.get("scene_number", "?")
        for field in ["lighting", "image_prompt", "video_prompt"]:
            val = s.get(field, "")[:300]
            if "neon magenta" in val.lower() or "cyber pink" in val.lower():
                issues.append(f"Sc{n}: RAW COLOR in {field}")
            risk_hits = policy_risk_hits(s.get(field, ""))
            if risk_hits:
                issues.append(f"Sc{n}: POLICY RISK in {field}: {', '.join(risk_hits[:5])}")
        for field in ["lighting", "movement", "scene_action"]:
            val = s.get(field, "")
            m = re.search(r"(\b\w{4,}\b) \1\b", val)
            if m:
                issues.append(f"Sc{n}: DOUBLE WORD [{m.group(0)}] in {field}")
    return len(scenes), issues

def validate_output(name):
    issues = []
    for ptype in ["image_prompts", "video_prompts"]:
        pdir = f"output/{name}/{ptype}"
        if not os.path.exists(pdir):
            issues.append(f"{ptype} 폴더 없음")
            continue
        for fname in sorted(os.listdir(pdir)):
            with open(f"{pdir}/{fname}", encoding="utf-8") as _fh:
                content = _fh.read()
            if "neon magenta" in content.lower() or "cyber pink" in content.lower():
                issues.append(f"{ptype}/{fname}: RAW COLOR")
            risk_hits = policy_risk_hits(content)
            if risk_hits:
                issues.append(f"{ptype}/{fname}: POLICY RISK {', '.join(risk_hits[:5])}")
            if ptype == "video_prompts":
                # Kling
                m = re.search(r"## Kling AI\r?\n(.*?)(\r?\n\r?\n>|\r?\n##)", content, re.DOTALL)
                if m:
                    k = m.group(1).strip()
                    wc = len(k.split())
                    if wc > 65:
                        issues.append(f"{fname} [Kling]: {wc}단어>65")
                    if not k.endswith("."):
                        issues.append(f"{fname} [Kling]: 마침표없음")
                # Sora
                for sec in ["**Scene:**","**Cinematography:**","**Actions:**","**Style:**","**Sound:**"]:
                    if sec not in content:
                        issues.append(f"{fname} [Sora]: 누락 {sec}")
                # Wan Negative
                if "## Wan 2.1" in content and "Negative prompt" not in content:
                    issues.append(f"{fname} [Wan]: Negative prompt 없음")
    return issues

import shutil, tempfile

INPUT_DIR = os.path.join(os.path.dirname(__file__), "input")
_AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


def _resolve_input_path(name: str, rel_path: str) -> tuple[str, object]:
    """web_inputs 경로가 없으면 input/<name>.txt 기반 임시 디렉토리를 반환."""
    abs_path = os.path.join(os.path.dirname(__file__), rel_path)
    if os.path.isdir(abs_path):
        return abs_path, None  # 원본 경로 사용

    # input/<name>.txt 탐색
    txt_path = None
    for suffix in ("", "_"):
        cand = os.path.join(INPUT_DIR, f"{name}{suffix}.txt")
        if os.path.exists(cand):
            txt_path = cand
            break
    if txt_path is None:
        lower = name.lower()
        for f in os.listdir(INPUT_DIR):
            if f.lower().endswith(".txt") and f.lower().rstrip("_").rsplit(".", 1)[0] == lower:
                txt_path = os.path.join(INPUT_DIR, f)
                break

    if txt_path is None:
        return abs_path, None  # 탐색 실패 시 원본(없는) 경로 유지

    tmp = tempfile.mkdtemp(prefix="validate_")
    shutil.copy2(txt_path, os.path.join(tmp, "raw_song.txt"))
    stem = os.path.splitext(os.path.basename(txt_path))[0]
    for ext in list(_AUDIO_EXTS) + [".lrc", ".srt"]:
        for s in (stem, stem + "_"):
            cand = os.path.join(INPUT_DIR, f"{s}{ext}")
            if os.path.exists(cand):
                shutil.copy2(cand, os.path.join(tmp, os.path.basename(cand)))
                break
    return tmp, tmp  # 두 번째 값이 None이 아니면 나중에 cleanup


def validate_existing(name):
    """곡별 output을 수정하지 않고 검증한다."""
    video_dir = os.path.join("output", name, "video_prompts")
    scene_count = 0
    if os.path.isdir(video_dir):
        scene_count = sum(
            1 for filename in os.listdir(video_dir)
            if filename.lower().endswith(".md")
        )
    return name, scene_count, validate_output(name)


def regenerate_and_validate(item):
    """한 곡을 재생성한 뒤 현재 storyboard와 곡별 output을 검증한다."""
    name, path = item
    resolved_path, tmp_handle = _resolve_input_path(name, path)
    try:
        result = subprocess.run(
            [sys.executable, "scripts/run_pipeline.py", "--input", resolved_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    finally:
        if tmp_handle:
            shutil.rmtree(tmp_handle, ignore_errors=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()[:500]
        return name, -1, [f"파이프라인 실패: {detail}"]

    scene_count, scene_issues = validate_scene_list(name)
    return name, scene_count, scene_issues + validate_output(name)


def parse_args():
    parser = argparse.ArgumentParser(
        description=f"{len(SONG_INPUTS)}곡 산출물을 빠르게 검사하거나 명시적으로 재생성 후 검사합니다."
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="각 곡의 파이프라인을 다시 실행합니다. 지정하지 않으면 기존 output만 검사합니다.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=min(8, os.cpu_count() or 1),
        help="기존 output 읽기 검증의 병렬 작업 수(기본 최대 8).",
    )
    parser.add_argument("--limit", type=int, help="앞에서부터 지정한 곡 수만 검사합니다.")
    parser.add_argument(
        "--song",
        action="append",
        default=[],
        help="정확한 곡명만 검사합니다. 여러 번 지정할 수 있습니다.",
    )
    return parser.parse_args()


def select_inputs(args):
    selected = SONG_INPUTS
    if args.song:
        requested = set(args.song)
        selected = [item for item in selected if item[0] in requested]
        missing = sorted(requested - {name for name, _ in selected})
        if missing:
            raise SystemExit(f"등록되지 않은 곡명: {', '.join(missing)}")
    if args.limit is not None:
        if args.limit < 1:
            raise SystemExit("--limit은 1 이상이어야 합니다.")
        selected = selected[:args.limit]
    return selected


def print_summary(results):
    print(f"\n{'='*65}")
    print("최종 결과")
    print(f"{'='*65}")
    pass_count = sum(1 for _, _, issues in results if not issues)
    fail_count = len(results) - pass_count
    print(f"PASS {pass_count}곡 / FAIL {fail_count}곡")
    print()
    for name, scene_count, issues in results:
        status = "PASS" if not issues else "FAIL"
        print(f"  [{status}] {name}: {scene_count}씬, 문제 {len(issues)}건")
        for issue in issues:
            print(f"         - {issue}")
    return fail_count


def main():
    args = parse_args()
    selected = select_inputs(args)
    mode = "파이프라인 재생성 + 검증" if args.regenerate else "기존 output 읽기 검증"
    print(f"{'='*65}")
    print(f"전체 {len(selected)}곡 {mode}")
    print(f"{'='*65}")

    if args.regenerate:
        results = []
        for index, item in enumerate(selected, 1):
            print(f"[{index:03d}/{len(selected)}] {item[0]}", flush=True)
            results.append(regenerate_and_validate(item))
    else:
        workers = max(1, args.workers)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(lambda item: validate_existing(item[0]), selected))

    raise SystemExit(1 if print_summary(results) else 0)


if __name__ == "__main__":
    main()
