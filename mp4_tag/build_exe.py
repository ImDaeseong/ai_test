import PyInstaller.__main__
import shutil
import os

def build():
    # 1. 이전 빌드 파일 정리 (실행 중인 exe 강제 종료 후 삭제)
    import subprocess, time
    subprocess.run(['taskkill', '/F', '/IM', 'VideoDownloader.exe'],
                   capture_output=True)
    time.sleep(2)  # Windows 파일 핸들 해제 대기
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)

    # 2. PyInstaller 실행 옵션 설정
    opts = [
        'run_app.py',                # 진입점 파일
        '--name=VideoDownloader',     # 생성될 파일명
        '--onefile',                  # 단일 파일로 생성
        '--noconfirm',
        '--clean',
        # 리소스 추가
        '--add-data=app.py;.',
        '--add-data=ffmpeg.exe;.',
        # Streamlit & Playwright 핵심 의존성 수집
        '--collect-all=streamlit',
        '--collect-all=playwright',
        '--collect-all=yt_dlp',
        '--collect-all=httpx',
        '--collect-all=httpcore',
        # 필요한 경우 추가 hook 폴더 지정
        '--additional-hooks-dir=.'
    ]

    PyInstaller.__main__.run(opts)

if __name__ == "__main__":
    build()