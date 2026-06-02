package main

import (
	"encoding/json"
	"strings"
	"testing"
)

// ── extractLastJSON ──────────────────────────────

func TestExtractLastJSON_singleObject(t *testing.T) {
	input := []byte(`{"status":"ok","value":1}`)
	got := extractLastJSON(input)
	if got == nil {
		t.Fatal("want non-nil, got nil")
	}
	var m map[string]any
	if err := json.Unmarshal(got, &m); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}
	if m["status"] != "ok" {
		t.Errorf("status = %v, want ok", m["status"])
	}
}

func TestExtractLastJSON_logLinesBeforeJSON(t *testing.T) {
	input := []byte("INFO loading file\nINFO done\n{\"status\":\"analyzed\"}\n")
	got := extractLastJSON(input)
	if got == nil {
		t.Fatal("want non-nil, got nil")
	}
	var m map[string]any
	if err := json.Unmarshal(got, &m); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}
	if m["status"] != "analyzed" {
		t.Errorf("status = %v, want analyzed", m["status"])
	}
}

func TestExtractLastJSON_multilineJSON(t *testing.T) {
	input := []byte("log line\n{\n  \"a\": 1,\n  \"b\": 2\n}\n")
	got := extractLastJSON(input)
	if got == nil {
		t.Fatal("want non-nil, got nil")
	}
	var m map[string]any
	if err := json.Unmarshal(got, &m); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}
}

func TestExtractLastJSON_noJSON(t *testing.T) {
	input := []byte("no json here\njust plain text\n")
	got := extractLastJSON(input)
	if got != nil {
		t.Errorf("want nil, got %s", string(got))
	}
}

func TestExtractLastJSON_empty(t *testing.T) {
	got := extractLastJSON([]byte{})
	if got != nil {
		t.Errorf("want nil for empty input, got %s", string(got))
	}
}

func TestExtractLastJSON_picksLast(t *testing.T) {
	// 여러 JSON 블록 중 마지막이 선택되어야 한다.
	input := []byte("{\"step\":1}\nsome log\n{\"step\":2}\n")
	got := extractLastJSON(input)
	if got == nil {
		t.Fatal("want non-nil, got nil")
	}
	var m map[string]any
	if err := json.Unmarshal(got, &m); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}
	if m["step"].(float64) != 2 {
		t.Errorf("step = %v, want 2", m["step"])
	}
}

// ── isAudioFile ──────────────────────────────────

func TestIsAudioFile(t *testing.T) {
	cases := []struct {
		path string
		want bool
	}{
		{"song.mp3", true},
		{"track.wav", true},
		{"album.flac", true},
		{"clip.m4a", true},
		{"song.MP3", true},  // 대소문자 무관
		{"doc.pdf", false},
		{"image.jpg", false},
		{"song_mastered.mp3", false},  // 마스터링 결과물 제외
		{"마스터링_song.wav", false},
		{"", false},
	}
	for _, c := range cases {
		got := isAudioFile(c.path)
		if got != c.want {
			t.Errorf("isAudioFile(%q) = %v, want %v", c.path, got, c.want)
		}
	}
}

// ── safeUploadName ───────────────────────────────

func TestSafeUploadName_keepsExtension(t *testing.T) {
	name := safeUploadName("my song.mp3")
	if !strings.HasSuffix(name, ".mp3") {
		t.Errorf("expected .mp3 suffix, got %q", name)
	}
}

func TestSafeUploadName_sanitizesSpecialChars(t *testing.T) {
	name := safeUploadName("../evil/../path.wav")
	if strings.Contains(name, "/") || strings.Contains(name, "\\") {
		t.Errorf("sanitized name contains path separator: %q", name)
	}
}

func TestSafeUploadName_emptyBaseFallback(t *testing.T) {
	name := safeUploadName(".mp3")
	if !strings.HasPrefix(name, "audio_") {
		t.Errorf("expected audio_ prefix for empty base, got %q", name)
	}
}

func TestSafeUploadName_uniqueSuffix(t *testing.T) {
	a := safeUploadName("track.mp3")
	b := safeUploadName("track.mp3")
	if a == b {
		t.Errorf("expected unique names, both got %q", a)
	}
}

// ── allowedCORSOrigin ────────────────────────────

func TestAllowedCORSOrigin_localhostPassthrough(t *testing.T) {
	cases := []string{
		"http://localhost:3000",
		"http://localhost:5173",
		"http://127.0.0.1:8080",
	}
	for _, origin := range cases {
		got := allowedCORSOrigin(origin)
		if got != origin {
			t.Errorf("allowedCORSOrigin(%q) = %q, want passthrough", origin, got)
		}
	}
}

func TestAllowedCORSOrigin_externalOriginBlocked(t *testing.T) {
	got := allowedCORSOrigin("https://evil.com")
	if got == "https://evil.com" {
		t.Errorf("external origin should not be echoed back, got %q", got)
	}
}

func TestAllowedCORSOrigin_emptyOriginDefault(t *testing.T) {
	got := allowedCORSOrigin("")
	if got == "" {
		t.Error("empty origin should return a default, got empty string")
	}
}

func TestAllowedCORSOrigin_envOverride(t *testing.T) {
	original := corsOrigin
	corsOrigin = "https://myapp.example.com"
	defer func() { corsOrigin = original }()

	got := allowedCORSOrigin("http://localhost:3000")
	if got != "https://myapp.example.com" {
		t.Errorf("CORS_ORIGIN env override not respected, got %q", got)
	}
}
