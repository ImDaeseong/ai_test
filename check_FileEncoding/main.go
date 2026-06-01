package main

import (
	"context"
	_ "embed"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"
	"unicode/utf8"
)

const (
	serverAddr      = "127.0.0.1:8080"
	serverURL       = "http://localhost:8080"
	maxRequestBytes = 4096
	maxFileBytes    = 50 * 1024 * 1024
	maxWorkers      = 64
	scanTimeout     = 10 * time.Minute
)

//go:embed index.html
var indexHTML []byte

// FileResult는 단일 파일의 인코딩 분석 결과입니다.
type FileResult struct {
	Name     string `json:"name"`
	Path     string `json:"path"`
	Encoding string `json:"encoding"`
	BOM      bool   `json:"bom"`
	Error    string `json:"error,omitempty"`
}

// ScanRequest는 /scan 엔드포인트의 요청 바디입니다.
type ScanRequest struct {
	Path string `json:"path"`
}

// 검사 대상 확장자
var targetExtensions = map[string]bool{
	".cpp": true,
	".h":   true,
	".hpp": true,
	".c":   true,
	".rc":  true,
}

func isTargetFile(path string) bool {
	return targetExtensions[strings.ToLower(filepath.Ext(path))]
}

// detectEncoding은 raw byte 배열을 분석하여 인코딩과 BOM 여부를 반환합니다.
// 절대 인코딩 변환을 수행하지 않으며, byte 분석만 수행합니다.
func detectEncoding(data []byte) (encoding string, hasBOM bool) {
	// (1) BOM 검사
	if len(data) >= 3 && data[0] == 0xEF && data[1] == 0xBB && data[2] == 0xBF {
		return "UTF-8 BOM", true
	}
	if len(data) >= 2 && data[0] == 0xFF && data[1] == 0xFE {
		return "UTF-16 LE", true
	}
	if len(data) >= 2 && data[0] == 0xFE && data[1] == 0xFF {
		return "UTF-16 BE", true
	}

	// (2) BOM 없음 → UTF-8 유효성 검사
	if utf8.Valid(data) {
		return "UTF-8 (No BOM)", false
	}

	// (3) UTF-8 아님 → EUC-KR (CP949)로 판정
	return "EUC-KR (CP949)", false
}

func fileResultError(path string, err error) FileResult {
	return FileResult{
		Name:  filepath.Base(path),
		Path:  path,
		Error: err.Error(),
	}
}

func scanFile(ctx context.Context, path string) FileResult {
	if err := ctx.Err(); err != nil {
		return fileResultError(path, err)
	}

	info, err := os.Stat(path)
	if err != nil {
		return fileResultError(path, err)
	}
	if info.Size() > maxFileBytes {
		return fileResultError(path, fmt.Errorf("파일이 너무 큽니다: %.1f MB (최대 %.1f MB)", float64(info.Size())/(1024*1024), float64(maxFileBytes)/(1024*1024)))
	}

	data, err := os.ReadFile(path)
	if err != nil {
		return fileResultError(path, err)
	}
	if err := ctx.Err(); err != nil {
		return fileResultError(path, err)
	}

	encoding, hasBOM := detectEncoding(data)
	return FileResult{
		Name:     filepath.Base(path),
		Path:     path,
		Encoding: encoding,
		BOM:      hasBOM,
	}
}

func collectTargetFiles(ctx context.Context, scanPath string, info os.FileInfo) ([]string, []FileResult, error) {
	if !info.IsDir() {
		if !isTargetFile(scanPath) {
			return nil, nil, fmt.Errorf("검사 대상 파일이 아닙니다: %s", scanPath)
		}
		return []string{scanPath}, nil, nil
	}

	var files []string
	var walkErrors []FileResult
	err := filepath.WalkDir(scanPath, func(path string, d os.DirEntry, err error) error {
		if ctx.Err() != nil {
			return ctx.Err()
		}
		if err != nil {
			walkErrors = append(walkErrors, FileResult{
				Name:  filepath.Base(path),
				Path:  path,
				Error: err.Error(),
			})
			return nil
		}
		if d.IsDir() {
			return nil
		}
		if isTargetFile(path) {
			files = append(files, path)
		}
		return nil
	})
	if err != nil {
		if errors.Is(err, context.Canceled) {
			return files, walkErrors, err
		}
		return nil, nil, fmt.Errorf("디렉토리 탐색 실패: %w", err)
	}

	return files, walkErrors, nil
}

func scanHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), scanTimeout)
	defer cancel()

	var req ScanRequest
	decoder := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxRequestBytes))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&req); err != nil {
		http.Error(w, "잘못된 요청 형식입니다.", http.StatusBadRequest)
		return
	}

	scanPath := strings.TrimSpace(req.Path)
	if scanPath == "" {
		http.Error(w, "경로를 입력하세요.", http.StatusBadRequest)
		return
	}

	// 경로 존재 여부 확인
	info, err := os.Stat(scanPath)
	if err != nil {
		http.Error(w, fmt.Sprintf("경로를 찾을 수 없습니다: %s", scanPath), http.StatusBadRequest)
		return
	}
	if !info.IsDir() && !isTargetFile(scanPath) {
		http.Error(w, fmt.Sprintf("검사 대상 파일이 아닙니다: %s", scanPath), http.StatusBadRequest)
		return
	}

	// 대상 파일 목록 수집
	files, walkErrors, walkErr := collectTargetFiles(ctx, scanPath, info)
	if walkErr != nil {
		if errors.Is(walkErr, context.Canceled) {
			log.Printf("스캔 취소: %s", scanPath)
			return
		}
		http.Error(w, fmt.Sprintf("디렉토리 탐색 오류: %v", walkErr), http.StatusInternalServerError)
		return
	}

	// 병렬 처리: goroutine + semaphore
	results := make([]FileResult, len(files)+len(walkErrors))
	copy(results[len(files):], walkErrors)
	var wg sync.WaitGroup
	sem := make(chan struct{}, maxWorkers)
	canceled := false

	for i, filePath := range files {
		select {
		case <-ctx.Done():
			log.Printf("스캔 취소: %s", scanPath)
			canceled = true
		case sem <- struct{}{}:
		}
		if canceled {
			break
		}

		wg.Add(1)
		go func(idx int, fp string) {
			defer wg.Done()
			defer func() { <-sem }()
			results[idx] = scanFile(ctx, fp)
		}(i, filePath)
	}

	wg.Wait()
	if canceled || ctx.Err() != nil {
		log.Printf("스캔 취소: %s", scanPath)
		return
	}

	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	if err := json.NewEncoder(w).Encode(results); err != nil {
		log.Printf("JSON 인코딩 오류: %v", err)
	}
}

func openBrowser(url string) {
	time.Sleep(400 * time.Millisecond)
	var err error
	switch runtime.GOOS {
	case "windows":
		err = exec.Command("rundll32", "url.dll,FileProtocolHandler", url).Start()
	case "darwin":
		err = exec.Command("open", url).Start()
	default:
		err = exec.Command("xdg-open", url).Start()
	}
	if err != nil {
		log.Printf("브라우저 자동 열기 실패: %v", err)
	}
}

func main() {
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		if _, err := w.Write(indexHTML); err != nil {
			log.Printf("index.html 응답 오류: %v", err)
		}
	})
	http.HandleFunc("/scan", scanHandler)

	fmt.Println("========================================")
	fmt.Println("  파일 인코딩 검사 도구 v1.0")
	fmt.Println("========================================")
	fmt.Printf("  서버 주소 : %s\n", serverURL)
	fmt.Println("  브라우저가 자동으로 열립니다.")
	fmt.Println("  종료      : Ctrl+C")
	fmt.Println("========================================")

	go openBrowser(serverURL)

	srv := &http.Server{
		Addr:              serverAddr,
		ReadHeaderTimeout: 5 * time.Second,
		IdleTimeout:       60 * time.Second,
		// WriteTimeout 미설정: 대형 폴더 스캔 응답은 scanTimeout 으로 제어
	}
	if err := srv.ListenAndServe(); err != nil {
		log.Fatalf("서버 시작 실패: %v", err)
	}
}
