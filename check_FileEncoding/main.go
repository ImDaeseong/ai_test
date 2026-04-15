package main

import (
	_ "embed"
	"encoding/json"
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

func scanHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req ScanRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "잘못된 요청 형식입니다.", http.StatusBadRequest)
		return
	}

	scanPath := strings.TrimSpace(req.Path)
	if scanPath == "" {
		http.Error(w, "경로를 입력하세요.", http.StatusBadRequest)
		return
	}

	// 경로 존재 여부 확인
	if _, err := os.Stat(scanPath); err != nil {
		http.Error(w, fmt.Sprintf("경로를 찾을 수 없습니다: %s", scanPath), http.StatusBadRequest)
		return
	}

	// 대상 파일 목록 수집
	var files []string
	walkErr := filepath.Walk(scanPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			// 접근 불가 경로는 건너뜀
			return nil
		}
		if !info.IsDir() {
			ext := strings.ToLower(filepath.Ext(path))
			if targetExtensions[ext] {
				files = append(files, path)
			}
		}
		return nil
	})
	if walkErr != nil {
		http.Error(w, fmt.Sprintf("디렉토리 탐색 오류: %v", walkErr), http.StatusInternalServerError)
		return
	}

	// 병렬 처리: goroutine + semaphore
	results := make([]FileResult, len(files))
	var wg sync.WaitGroup
	sem := make(chan struct{}, 64) // 최대 64개 동시 처리

	for i, filePath := range files {
		wg.Add(1)
		sem <- struct{}{}
		go func(idx int, fp string) {
			defer wg.Done()
			defer func() { <-sem }()

			// 파일을 raw byte로 읽음 (절대 string 변환하거나 수정하지 않음)
			data, err := os.ReadFile(fp)
			if err != nil {
				results[idx] = FileResult{
					Name:  filepath.Base(fp),
					Path:  fp,
					Error: err.Error(),
				}
				return
			}

			encoding, hasBOM := detectEncoding(data)
			results[idx] = FileResult{
				Name:     filepath.Base(fp),
				Path:     fp,
				Encoding: encoding,
				BOM:      hasBOM,
			}
		}(i, filePath)
	}

	wg.Wait()

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
		w.Write(indexHTML)
	})
	http.HandleFunc("/scan", scanHandler)

	const addr = ":8080"
	const url = "http://localhost:8080"

	fmt.Println("========================================")
	fmt.Println("  파일 인코딩 검사 도구 v1.0")
	fmt.Println("========================================")
	fmt.Printf("  서버 주소 : %s\n", url)
	fmt.Println("  브라우저가 자동으로 열립니다.")
	fmt.Println("  종료      : Ctrl+C")
	fmt.Println("========================================")

	go openBrowser(url)

	if err := http.ListenAndServe(addr, nil); err != nil {
		log.Fatalf("서버 시작 실패: %v", err)
	}
}
