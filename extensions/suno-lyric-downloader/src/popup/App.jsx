import { useState, useEffect } from 'react'

const STEPS = [
  'Suno에 로그인 (suno.com)',
  '노래 상세 페이지 열기 (/song/...)',
  '커버 위의 LRC 또는 SRT 버튼 클릭',
]

const TROUBLESHOOTING = [
  '일부 노래는 동기화 타이밍이 없습니다.',
  '커버 이미지 로딩 후 새로고침 해보세요.',
  'Suno에 로그인 상태인지 확인하세요.',
  '홈/만들기 페이지가 아닌 /song/... URL을 이용하세요.',
]

const STATUS_CONFIG = {
  loading: {
    dot: 'bg-neutral-600',
    text: '탭 확인 중...',
    sub: '',
  },
  not_suno: {
    dot: 'bg-neutral-600',
    text: 'Suno 외 페이지',
    sub: 'Suno를 열고 노래 페이지를 선택하세요.',
  },
  suno_non_song: {
    dot: 'bg-yellow-500',
    text: 'Suno 열려 있음',
    sub: '/song/... URL의 노래 상세 페이지를 여세요.',
  },
  suno_song: {
    dot: 'bg-emerald-400',
    text: '노래 페이지 감지됨',
    sub: '커버 이미지 위에 다운로드 버튼이 표시됩니다.',
  },
}

function MusicIcon() {
  return (
    <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.8} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 9l10.5-3m0 6.553v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 11-.99-3.467l2.31-.66a2.25 2.25 0 001.632-2.163zm0 0V2.25L9 5v10.5m0 0v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 01-.99-3.467l2.31-.66A2.25 2.25 0 009 15.75z" />
    </svg>
  )
}

function ChevronIcon() {
  return (
    <svg className="w-3 h-3 transition-transform group-open:rotate-90" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
    </svg>
  )
}

function DownloadIcon() {
  return (
    <svg className="w-4 h-4 opacity-60" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
    </svg>
  )
}

export default function App() {
  const [status, setStatus] = useState('loading')
  const [tabId, setTabId] = useState(null)

  useEffect(() => {
    if (typeof chrome === 'undefined' || !chrome.tabs) {
      setStatus('not_suno')
      return
    }
    chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
      if (!tab?.url) { setStatus('not_suno'); return }
      setTabId(tab.id)
      try {
        const url = new URL(tab.url)
        if (!url.hostname.includes('suno.com')) {
          setStatus('not_suno')
        } else if (url.pathname.startsWith('/song/')) {
          setStatus('suno_song')
        } else {
          setStatus('suno_non_song')
        }
      } catch {
        setStatus('not_suno')
      }
    })
  }, [])

  function openSuno() {
    chrome.tabs.create({ url: 'https://suno.com' })
  }

  function findButtons() {
    if (!tabId) return
    chrome.tabs.sendMessage(tabId, { action: 'FIND_BUTTONS' }, () => {
      // ignore response
      void chrome.runtime.lastError
    })
  }

  const cfg = STATUS_CONFIG[status]

  return (
    <div className="flex flex-col gap-3 p-4 min-w-[360px] min-h-[520px] bg-neutral-950 text-neutral-100 select-none">

      {/* Header */}
      <div className="flex items-center gap-3 pb-1">
        <div className="w-9 h-9 rounded-xl bg-emerald-500/15 flex items-center justify-center flex-shrink-0">
          <MusicIcon />
        </div>
        <div>
          <h1 className="text-sm font-semibold leading-tight">Suno Lyric Downloader</h1>
          <p className="text-xs text-neutral-500 leading-tight mt-0.5">LRC · SRT 가사 다운로더</p>
        </div>
      </div>

      {/* Divider */}
      <div className="h-px bg-neutral-800" />

      {/* Status */}
      <div className="flex items-start gap-2.5 bg-neutral-900 rounded-xl p-3">
        <span className={`mt-1 w-2 h-2 rounded-full flex-shrink-0 ${cfg.dot}`} />
        <div>
          <p className="text-sm font-medium leading-tight">{cfg.text}</p>
          {cfg.sub && <p className="text-xs text-neutral-500 mt-0.5 leading-relaxed">{cfg.sub}</p>}
        </div>
      </div>

      {/* Usage Guide */}
      <div className="bg-neutral-900 rounded-xl p-3 flex flex-col gap-2.5">
        <p className="text-[11px] font-semibold text-neutral-500 uppercase tracking-widest">사용 방법</p>
        {STEPS.map((step, i) => (
          <div key={i} className="flex items-start gap-2.5">
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-emerald-500/15 text-emerald-400 text-[11px] flex items-center justify-center font-semibold">
              {i + 1}
            </span>
            <span className="text-sm text-neutral-300 leading-relaxed">{step}</span>
          </div>
        ))}
      </div>

      {/* Buttons */}
      <div className="flex gap-2">
        <button
          onClick={openSuno}
          className="flex-1 py-2 rounded-xl bg-neutral-800 hover:bg-neutral-700 active:bg-neutral-600 text-sm font-medium transition-colors"
        >
          Suno 열기
        </button>
        <button
          onClick={findButtons}
          disabled={status !== 'suno_song'}
          className="flex-1 py-2 rounded-xl bg-emerald-500/15 hover:bg-emerald-500/25 active:bg-emerald-500/30 text-emerald-300 text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-1.5"
        >
          <DownloadIcon />
          버튼 찾기
        </button>
      </div>

      {/* Tip */}
      <div className="bg-neutral-900/60 border border-neutral-800 rounded-xl p-3">
        <p className="text-[11px] text-neutral-500 text-center leading-relaxed">
          노래 커버 이미지 위에 <span className="text-emerald-400 font-medium">LRC</span> · <span className="text-emerald-400 font-medium">SRT</span> 버튼이 자동으로 나타납니다
        </p>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Troubleshooting */}
      <details className="group">
        <summary className="text-xs text-neutral-600 cursor-pointer hover:text-neutral-400 transition-colors list-none flex items-center gap-1">
          <ChevronIcon />
          문제 해결
        </summary>
        <ul className="mt-2 flex flex-col gap-1.5 pl-4">
          {TROUBLESHOOTING.map((item, i) => (
            <li key={i} className="text-[11px] text-neutral-600 flex items-start gap-1.5">
              <span className="text-neutral-700 flex-shrink-0">•</span>
              <span className="leading-relaxed">{item}</span>
            </li>
          ))}
        </ul>
      </details>
    </div>
  )
}
