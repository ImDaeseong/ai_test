// main.go — Suno AI 음원 처리 DAW 시스템 (Go 제어 레이어)
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/fsnotify/fsnotify"
	"github.com/gin-gonic/gin"
)

// ──────────────────────────────────────────────
// Job 시스템
// ──────────────────────────────────────────────

type JobStatus struct {
	ID        string          `json:"id"`
	File      string          `json:"file"`
	Operation string          `json:"operation"` // "pipeline" | "analyze" | "master" | "separate"
	State     string          `json:"state"`     // "queued" | "running" | "done" | "error"
	StartedAt time.Time       `json:"started_at"`
	UpdatedAt time.Time       `json:"updated_at"`
	Result    json.RawMessage `json:"result,omitempty"`
	Error     string          `json:"error,omitempty"`
}

var (
	jobs       = make(map[string]*JobStatus)
	jobsMu     sync.RWMutex
	jobCounter int64

	// 파이프라인(자동감시) 전용 큐
	workQueue = make(chan string, 32)

	pythonBin = getEnvOrDefault("PYTHON_BIN", "python")
	watchDir  = getEnvOrDefault("WATCH_DIR", "./inbox")
	outDir    = getEnvOrDefault("OUT_DIR", "./output")
)

func nextJobID() string {
	return fmt.Sprintf("%d", atomic.AddInt64(&jobCounter, 1))
}

func newJob(id, file, operation string) *JobStatus {
	now := time.Now()
	return &JobStatus{
		ID:        id,
		File:      file,
		Operation: operation,
		State:     "queued",
		StartedAt: now,
		UpdatedAt: now,
	}
}

func setJobState(job *JobStatus, state string) {
	jobsMu.Lock()
	job.State = state
	job.UpdatedAt = time.Now()
	jobsMu.Unlock()
	log.Printf("📌 [Job %s][%s] %s → %s", job.ID, job.Operation, filepath.Base(job.File), state)
}

func setJobDone(job *JobStatus, result json.RawMessage) {
	jobsMu.Lock()
	job.State = "done"
	job.Result = result
	job.UpdatedAt = time.Now()
	jobsMu.Unlock()
	elapsed := time.Since(job.StartedAt).Seconds()
	log.Printf("🎉 [Job %s][%s] 완료 — %s (%.1f초)", job.ID, job.Operation, filepath.Base(job.File), elapsed)
}

func setJobError(job *JobStatus, errMsg string) {
	jobsMu.Lock()
	job.State = "error"
	job.Error = errMsg
	job.UpdatedAt = time.Now()
	jobsMu.Unlock()
	log.Printf("❌ [Job %s][%s] 오류: %s", job.ID, job.Operation, errMsg)
}

func storeJob(job *JobStatus) {
	jobsMu.Lock()
	jobs[job.ID] = job
	jobsMu.Unlock()
}

func getJob(id string) (*JobStatus, bool) {
	jobsMu.RLock()
	defer jobsMu.RUnlock()
	j, ok := jobs[id]
	return j, ok
}

// ──────────────────────────────────────────────
// 유틸리티
// ──────────────────────────────────────────────

func getEnvOrDefault(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func isAudioFile(path string) bool {
	ext := strings.ToLower(filepath.Ext(path))
	if ext != ".mp3" && ext != ".wav" && ext != ".flac" && ext != ".m4a" {
		return false
	}
	// 마스터링 결과물이 inbox로 돌아와 재처리되는 루프 방지
	base := strings.ToLower(filepath.Base(path))
	return !strings.Contains(base, "_mastered")
}

func ensureDir(dir string) {
	if err := os.MkdirAll(dir, 0755); err != nil {
		log.Fatalf("❌ 디렉토리 생성 실패: %s — %v", dir, err)
	}
}

// ──────────────────────────────────────────────
// Python 엔진 호출
// ──────────────────────────────────────────────

// runPythonEngine: engine.py를 호출하고 마지막 JSON 블록을 반환한다.
// PYTHONUTF8=1 과 PYTHONIOENCODING=utf-8 을 설정해 한글 깨짐을 방지한다.
func runPythonEngine(args ...string) (json.RawMessage, error) {
	// -u: 출력 버퍼링 비활성화 (실시간 로그)
	cmdArgs := append([]string{"-u", "engine.py"}, args...)
	cmd := exec.Command(pythonBin, cmdArgs...)
	cmd.Stderr = os.Stderr

	// Windows CP949 → UTF-8 강제
	cmd.Env = append(os.Environ(),
		"PYTHONUTF8=1",
		"PYTHONIOENCODING=utf-8",
	)

	var stdoutBuf bytes.Buffer
	cmd.Stdout = io.MultiWriter(&stdoutBuf, os.Stdout)

	log.Printf("▶ Python: %s %s", pythonBin, strings.Join(cmdArgs, " "))
	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("Python 프로세스 오류: %w", err)
	}

	raw := extractLastJSON(stdoutBuf.Bytes())
	if raw == nil {
		return nil, fmt.Errorf("Python 출력에서 JSON을 찾을 수 없음")
	}
	return raw, nil
}

// extractLastJSON: stdout에서 마지막 JSON 객체({...})를 추출한다.
func extractLastJSON(data []byte) json.RawMessage {
	// 줄 단위로 역방향 탐색하여 JSON 객체 시작점 찾기
	lines := bytes.Split(data, []byte("\n"))
	for i := len(lines) - 1; i >= 0; i-- {
		line := bytes.TrimSpace(lines[i])
		if !bytes.HasPrefix(line, []byte("{")) {
			continue
		}
		// 이 줄부터 끝까지 합쳐서 파싱 시도
		rest := bytes.TrimSpace(bytes.Join(lines[i:], []byte("\n")))
		if json.Valid(rest) {
			return json.RawMessage(rest)
		}
	}
	// 전체를 JSON으로 시도
	trimmed := bytes.TrimSpace(data)
	if json.Valid(trimmed) {
		return json.RawMessage(trimmed)
	}
	return nil
}

// ──────────────────────────────────────────────
// 비동기 Job 실행 헬퍼
// ──────────────────────────────────────────────

// runJobAsync: job을 고루틴에서 실행하고 상태를 업데이트한다.
func runJobAsync(job *JobStatus, pythonArgs ...string) {
	go func() {
		setJobState(job, "running")
		result, err := runPythonEngine(pythonArgs...)
		if err != nil {
			setJobError(job, err.Error())
			return
		}
		setJobDone(job, result)
	}()
}

// ──────────────────────────────────────────────
// 파이프라인 처리 (파일 감시 → 자동 분석+마스터링)
// ──────────────────────────────────────────────

func processFile(filePath string) {
	abs, err := filepath.Abs(filePath)
	if err != nil {
		log.Printf("❌ 경로 변환 실패: %v", err)
		return
	}

	// 동일 파일의 파이프라인이 이미 실행 중이면 건너뜀
	jobsMu.Lock()
	for _, j := range jobs {
		if j.File == abs && j.Operation == "pipeline" &&
			(j.State == "queued" || j.State == "running") {
			jobsMu.Unlock()
			log.Printf("⏭️  이미 처리 중: %s", filepath.Base(abs))
			return
		}
	}
	id := nextJobID()
	job := newJob(id, abs, "pipeline")
	jobs[id] = job
	jobsMu.Unlock()

	setJobState(job, "running")

	// 1단계: 분석
	log.Printf("🔍 [파이프라인 %s] 1/2 분석: %s", id, filepath.Base(abs))
	analysisResult, err := runPythonEngine("analyze", abs)
	if err != nil {
		setJobError(job, "분석 실패: "+err.Error())
		return
	}

	// 2단계: 마스터링 (출력은 output/ 폴더로 → inbox 재처리 루프 방지)
	log.Printf("🎛️  [파이프라인 %s] 2/2 마스터링: %s", id, filepath.Base(abs))
	stem := strings.TrimSuffix(filepath.Base(abs), filepath.Ext(abs))
	masterOut := filepath.Join(outDir, stem+"_mastered.wav")
	masterResult, err := runPythonEngine("master", abs, "--lufs", "-14", "--output", masterOut)
	if err != nil {
		setJobError(job, "마스터링 실패: "+err.Error())
		return
	}

	combined := map[string]json.RawMessage{
		"analysis":  analysisResult,
		"mastering": masterResult,
	}
	combinedJSON, _ := json.Marshal(combined)
	setJobDone(job, json.RawMessage(combinedJSON))
}

func worker(id int) {
	log.Printf("👷 워커 #%d 시작", id)
	for filePath := range workQueue {
		log.Printf("👷 워커 #%d 수신: %s", id, filepath.Base(filePath))
		processFile(filePath)
	}
}

// ──────────────────────────────────────────────
// 파일 감시
// ──────────────────────────────────────────────

func watchFolder() {
	ensureDir(watchDir)
	watcher, err := fsnotify.NewWatcher()
	if err != nil {
		log.Fatalf("❌ 파일 감시자 생성 실패: %v", err)
	}
	defer watcher.Close()

	if err := watcher.Add(watchDir); err != nil {
		log.Fatalf("❌ 감시 폴더 등록 실패: %v", err)
	}
	log.Printf("👁️  파일 감시 시작: %s", watchDir)

	recentEvents := make(map[string]time.Time)
	var reMu sync.Mutex
	const cooldown = 3 * time.Second

	for {
		select {
		case event, ok := <-watcher.Events:
			if !ok {
				return
			}
			if !(event.Has(fsnotify.Create) || event.Has(fsnotify.Write)) {
				continue
			}
			path := event.Name
			if !isAudioFile(path) {
				continue
			}
			reMu.Lock()
			if last, seen := recentEvents[path]; seen && time.Since(last) < cooldown {
				reMu.Unlock()
				continue
			}
			recentEvents[path] = time.Now()
			reMu.Unlock()

			log.Printf("🎵 신규 오디오 파일 감지: %s", filepath.Base(path))
			select {
			case workQueue <- path:
			default:
				log.Printf("⚠️  큐 가득 참: %s", filepath.Base(path))
			}

		case err, ok := <-watcher.Errors:
			if !ok {
				return
			}
			log.Printf("⚠️  감시 오류: %v", err)
		}
	}
}

// ──────────────────────────────────────────────
// 웹 서버
// ──────────────────────────────────────────────

func startServer() {
	ensureDir(outDir)
	gin.SetMode(gin.ReleaseMode)
	r := gin.New()
	r.Use(gin.Logger(), gin.Recovery())

	// CORS
	r.Use(func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Content-Type")
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		c.Next()
	})

	r.Static("/audio", outDir)
	r.StaticFile("/", "./static/index.html")
	r.Static("/static", "./static")

	// ── Job 조회 ──

	// GET /api/jobs — 전체 목록
	r.GET("/api/jobs", func(c *gin.Context) {
		jobsMu.RLock()
		list := make([]*JobStatus, 0, len(jobs))
		for _, j := range jobs {
			list = append(list, j)
		}
		jobsMu.RUnlock()
		c.JSON(http.StatusOK, gin.H{"jobs": list, "total": len(list)})
	})

	// GET /api/job/:id — 단일 Job 폴링용
	r.GET("/api/job/:id", func(c *gin.Context) {
		id := c.Param("id")
		job, ok := getJob(id)
		if !ok {
			c.JSON(http.StatusNotFound, gin.H{"error": "존재하지 않는 Job ID"})
			return
		}
		c.JSON(http.StatusOK, job)
	})

	// ── 파일 업로드 ──

	// POST /api/upload
	r.POST("/api/upload", func(c *gin.Context) {
		file, err := c.FormFile("file")
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "파일 없음: " + err.Error()})
			return
		}
		if !isAudioFile(file.Filename) {
			c.JSON(http.StatusBadRequest, gin.H{"error": "지원하지 않는 형식 (mp3/wav/flac/m4a)"})
			return
		}
		dst := filepath.Join(watchDir, filepath.Base(file.Filename))
		if err := c.SaveUploadedFile(file, dst); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "저장 실패: " + err.Error()})
			return
		}
		abs, _ := filepath.Abs(dst)
		log.Printf("📤 업로드 완료: %s (%d bytes)", file.Filename, file.Size)
		c.JSON(http.StatusOK, gin.H{"path": abs, "filename": file.Filename, "size": file.Size})
	})

	// ── 오디오 처리 API ──

	// POST /api/analyze — 동기 (빠름, 수 초)
	r.POST("/api/analyze", func(c *gin.Context) {
		var req struct {
			File string `json:"file" binding:"required"`
		}
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		result, err := runPythonEngine("analyze", req.File)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		c.Data(http.StatusOK, "application/json; charset=utf-8", result)
	})

	// POST /api/master — 비동기 (Job ID 반환 → 클라이언트가 폴링)
	r.POST("/api/master", func(c *gin.Context) {
		var req struct {
			File string  `json:"file" binding:"required"`
			LUFS float64 `json:"lufs"`
		}
		req.LUFS = -14.0
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		id := nextJobID()
		job := newJob(id, req.File, "master")
		storeJob(job)

		lufsStr := fmt.Sprintf("%.1f", req.LUFS)
		stem := strings.TrimSuffix(filepath.Base(req.File), filepath.Ext(req.File))
		outFile := filepath.Join(outDir, stem+"_mastered.wav")
		runJobAsync(job, "master", req.File, "--lufs", lufsStr, "--output", outFile)

		c.JSON(http.StatusAccepted, gin.H{"job_id": id, "status": "queued"})
	})

	// POST /api/separate — 비동기 (Demucs는 수 분 소요)
	r.POST("/api/separate", func(c *gin.Context) {
		var req struct {
			File  string `json:"file" binding:"required"`
			Model string `json:"model"`
		}
		req.Model = "htdemucs"
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		id := nextJobID()
		job := newJob(id, req.File, "separate")
		storeJob(job)

		stemsOut := filepath.Join(outDir, "stems")
		runJobAsync(job, "separate", req.File, "--model", req.Model, "--output", stemsOut)

		c.JSON(http.StatusAccepted, gin.H{
			"job_id": id,
			"status": "queued",
			"note":   "htdemucs 최초 실행 시 모델 다운로드 (~1.5GB) 필요",
		})
	})

	// POST /api/pipeline — 비동기 전체 파이프라인
	r.POST("/api/pipeline", func(c *gin.Context) {
		var req struct {
			File string `json:"file" binding:"required"`
		}
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		if !isAudioFile(req.File) {
			c.JSON(http.StatusBadRequest, gin.H{"error": "지원하지 않는 파일 형식"})
			return
		}
		select {
		case workQueue <- req.File:
			c.JSON(http.StatusAccepted, gin.H{"status": "queued", "file": req.File})
		default:
			c.JSON(http.StatusServiceUnavailable, gin.H{"error": "처리 큐 가득 참"})
		}
	})

	// GET /api/check — 의존성 확인
	r.GET("/api/check", func(c *gin.Context) {
		result, err := runPythonEngine("check")
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		c.Data(http.StatusOK, "application/json; charset=utf-8", result)
	})

	log.Printf("🌐 웹 서버 시작: http://localhost:8080")
	if err := r.Run(":8080"); err != nil {
		log.Fatalf("❌ 서버 시작 실패: %v", err)
	}
}

// ──────────────────────────────────────────────
// main
// ──────────────────────────────────────────────

func main() {
	log.SetFlags(log.Ltime | log.Lshortfile)
	log.Println("🚀 Suno DAW 시스템 시작")
	log.Printf("   감시 폴더  : %s", watchDir)
	log.Printf("   출력 폴더  : %s", outDir)
	log.Printf("   Python 경로: %s", pythonBin)

	ensureDir(watchDir)
	ensureDir(outDir)

	// 파이프라인 워커 2개
	for i := 1; i <= 2; i++ {
		go worker(i)
	}

	// 파일 감시
	go watchFolder()

	// 기존 inbox 파일 재처리
	go func() {
		time.Sleep(2 * time.Second)
		entries, err := os.ReadDir(watchDir)
		if err != nil {
			return
		}
		for _, e := range entries {
			if !e.IsDir() && isAudioFile(e.Name()) {
				path := filepath.Join(watchDir, e.Name())
				log.Printf("📂 기존 파일 처리 예약: %s", e.Name())
				workQueue <- path
			}
		}
	}()

	startServer()
}
