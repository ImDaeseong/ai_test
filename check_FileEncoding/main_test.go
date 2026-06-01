package main

import (
	"context"
	"os"
	"path/filepath"
	"testing"
)

func TestDetectEncoding(t *testing.T) {
	tests := []struct {
		name     string
		data     []byte
		encoding string
		bom      bool
	}{
		{
			name:     "utf8 bom",
			data:     []byte{0xEF, 0xBB, 0xBF, 'a'},
			encoding: "UTF-8 BOM",
			bom:      true,
		},
		{
			name:     "utf16 le bom",
			data:     []byte{0xFF, 0xFE, 'a', 0x00},
			encoding: "UTF-16 LE",
			bom:      true,
		},
		{
			name:     "utf16 be bom",
			data:     []byte{0xFE, 0xFF, 0x00, 'a'},
			encoding: "UTF-16 BE",
			bom:      true,
		},
		{
			name:     "utf8 no bom",
			data:     []byte("hello 한글"),
			encoding: "UTF-8 (No BOM)",
			bom:      false,
		},
		{
			name:     "non utf8",
			data:     []byte{0xB0, 0xA1},
			encoding: "EUC-KR (CP949)",
			bom:      false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			encoding, bom := detectEncoding(tt.data)
			if encoding != tt.encoding || bom != tt.bom {
				t.Fatalf("detectEncoding() = (%q, %v), want (%q, %v)", encoding, bom, tt.encoding, tt.bom)
			}
		})
	}
}

func TestCollectTargetFiles(t *testing.T) {
	dir := t.TempDir()
	sourcePath := filepath.Join(dir, "main.cpp")
	textPath := filepath.Join(dir, "memo.txt")

	if err := os.WriteFile(sourcePath, []byte("int main() {}"), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(textPath, []byte("skip"), 0644); err != nil {
		t.Fatal(err)
	}

	info, err := os.Stat(dir)
	if err != nil {
		t.Fatal(err)
	}

	files, walkErrors, err := collectTargetFiles(context.Background(), dir, info)
	if err != nil {
		t.Fatal(err)
	}
	if len(walkErrors) != 0 {
		t.Fatalf("walkErrors length = %d, want 0", len(walkErrors))
	}
	if len(files) != 1 || files[0] != sourcePath {
		t.Fatalf("files = %#v, want [%q]", files, sourcePath)
	}
}

func TestCollectTargetFilesRejectsUnsupportedSingleFile(t *testing.T) {
	dir := t.TempDir()
	textPath := filepath.Join(dir, "memo.txt")
	if err := os.WriteFile(textPath, []byte("skip"), 0644); err != nil {
		t.Fatal(err)
	}

	info, err := os.Stat(textPath)
	if err != nil {
		t.Fatal(err)
	}

	_, _, err = collectTargetFiles(context.Background(), textPath, info)
	if err == nil {
		t.Fatal("collectTargetFiles() error = nil, want unsupported file error")
	}
}
