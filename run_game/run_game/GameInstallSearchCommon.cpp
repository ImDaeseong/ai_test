#include "stdafx.h"
#include "GameInstallSearchCommon.h"
#include "AppLog.h"
#include <shellapi.h>
#pragma comment(lib, "version.lib")

// 탐지된 게임 설치 결과 하나를 담는 컨테이너.
// SearchAll() 이후 CGameInstallArray에 플랫폼별로 추가된다.
CGameInstallInfo::CGameInstallInfo()
{
    m_eType = GAME_INSTALL_UNKNOWN;
    m_bInstalled = FALSE;
    m_bExeExists = FALSE;
}

// 파일·레지스트리·경로·실행 등 플랫폼 공통 유틸리티 정적 메서드 모음.
// 모든 메서드는 정적이며 인스턴스 없이 호출한다.
// 플랫폼 열거값에 해당하는 표시 이름 문자열을 반환한다.
CString CGameInstallSearchCommon::GetInstallTypeName(EGameInstallType eType)
{
    switch (eType)
    {
    case GAME_INSTALL_STEAM:
        return _T("Steam");
    case GAME_INSTALL_EPIC:
        return _T("Epic Games");
    case GAME_INSTALL_NETMARBLE:
        return _T("Netmarble");
    default:
        return _T("Unknown");
    }
}

static const REGSAM* GetRegistryReadSamViews(int& nCount)
{
    static const REGSAM s_samViews[] = {
        KEY_READ | KEY_WOW64_64KEY,
        KEY_READ | KEY_WOW64_32KEY,
        KEY_READ
    };

    nCount = sizeof(s_samViews) / sizeof(s_samViews[0]);
    return s_samViews;
}

// 경로가 파일로 존재하는지 확인한다 (디렉터리는 FALSE).
BOOL CGameInstallSearchCommon::FileExists(LPCTSTR lpszPath)
{
    if (lpszPath == NULL || lpszPath[0] == 0)
        return FALSE;

    DWORD dwAttr = GetFileAttributes(lpszPath);
    return (dwAttr != INVALID_FILE_ATTRIBUTES && (dwAttr & FILE_ATTRIBUTE_DIRECTORY) == 0);
}

// 경로가 디렉터리로 존재하는지 확인한다.
BOOL CGameInstallSearchCommon::DirectoryExists(LPCTSTR lpszPath)
{
    if (lpszPath == NULL || lpszPath[0] == 0)
        return FALSE;

    DWORD dwAttr = GetFileAttributes(lpszPath);
    return (dwAttr != INVALID_FILE_ATTRIBUTES && (dwAttr & FILE_ATTRIBUTE_DIRECTORY) != 0);
}

// 레지스트리에서 문자열 값을 읽는다. REG_EXPAND_SZ는 환경변수를 자동 확장한다.
BOOL CGameInstallSearchCommon::ReadStringValue(HKEY hRoot, LPCTSTR lpszSubKey, LPCTSTR lpszValueName, CString& strValue)
{
    int nSamCount = 0;
    const REGSAM* pSamViews = GetRegistryReadSamViews(nSamCount);

    for (int i = 0; i < nSamCount; ++i)
    {
        HKEY hKey = NULL;
        LONG lRet = RegOpenKeyEx(hRoot, lpszSubKey, 0, pSamViews[i], &hKey);
        if (lRet != ERROR_SUCCESS)
            continue;

        DWORD dwType = 0;
        DWORD dwSize = 0;
        lRet = RegQueryValueEx(hKey, lpszValueName, NULL, &dwType, NULL, &dwSize);
        if (lRet != ERROR_SUCCESS || (dwType != REG_SZ && dwType != REG_EXPAND_SZ))
        {
            RegCloseKey(hKey);
            continue;
        }

        LPTSTR pszBuffer = strValue.GetBuffer(dwSize / sizeof(TCHAR) + 2);
        ZeroMemory(pszBuffer, (dwSize / sizeof(TCHAR) + 2) * sizeof(TCHAR));
        lRet = RegQueryValueEx(hKey, lpszValueName, NULL, &dwType, (LPBYTE)pszBuffer, &dwSize);
        strValue.ReleaseBuffer();
        RegCloseKey(hKey);

        if (lRet != ERROR_SUCCESS)
        {
            strValue.Empty();
            continue;
        }

        if (dwType == REG_EXPAND_SZ)
        {
            TCHAR szExpanded[MAX_PATH * 4] = {0};
            ExpandEnvironmentStrings(strValue, szExpanded, sizeof(szExpanded) / sizeof(TCHAR));
            strValue = szExpanded;
        }

        return TRUE;
    }

    strValue.Empty();
    return FALSE;
}

// 레지스트리에서 DWORD 값을 읽는다.
BOOL CGameInstallSearchCommon::ReadDwordValue(HKEY hRoot, LPCTSTR lpszSubKey, LPCTSTR lpszValueName, DWORD& dwValue)
{
    int nSamCount = 0;
    const REGSAM* pSamViews = GetRegistryReadSamViews(nSamCount);

    for (int i = 0; i < nSamCount; ++i)
    {
        HKEY hKey = NULL;
        LONG lRet = RegOpenKeyEx(hRoot, lpszSubKey, 0, pSamViews[i], &hKey);
        if (lRet != ERROR_SUCCESS)
            continue;

        DWORD dwType = 0;
        DWORD dwSize = sizeof(DWORD);
        lRet = RegQueryValueEx(hKey, lpszValueName, NULL, &dwType, (LPBYTE)&dwValue, &dwSize);
        RegCloseKey(hKey);

        if (lRet == ERROR_SUCCESS && dwType == REG_DWORD)
            return TRUE;
    }

    return FALSE;
}

// 경로의 슬래시(/)를 백슬래시(\)로 정규화한다.
CString CGameInstallSearchCommon::NormalizePath(LPCTSTR lpszPath)
{
    CString strPath(lpszPath == NULL ? _T("") : lpszPath);
    strPath.Replace(_T('/'), _T('\\'));
    return strPath;
}

// 두 경로를 백슬래시로 결합한다. 양쪽 끝 중복 구분자를 처리한다.
CString CGameInstallSearchCommon::JoinPath(LPCTSTR lpszLeft, LPCTSTR lpszRight)
{
    CString strLeft = NormalizePath(lpszLeft);
    CString strRight = NormalizePath(lpszRight);

    if (strLeft.IsEmpty())
        return strRight;
    if (strRight.IsEmpty())
        return strLeft;
    if (strLeft.Right(1) == _T("\\"))
        return strLeft + strRight;
    return strLeft + _T("\\") + strRight;
}

// 경로에서 마지막 백슬래시 앞의 부모 경로를 반환한다.
CString CGameInstallSearchCommon::GetParentDirectory(LPCTSTR lpszPath)
{
    CString strPath = NormalizePath(lpszPath);
    int nPos = strPath.ReverseFind(_T('\\'));
    if (nPos < 0)
        return _T("");
    return strPath.Left(nPos);
}

// 텍스트 파일을 읽어 UTF-8 BOM 감지 후 CString으로 반환한다. 최대 4MB.
CString CGameInstallSearchCommon::ReadTextFile(LPCTSTR lpszPath)
{
    CFile file;
    CString strText;

    if (!file.Open(lpszPath, CFile::modeRead | CFile::shareDenyNone))
        return strText;

    ULONGLONG ullLen = file.GetLength();
    if (ullLen == 0 || ullLen > 1024 * 1024 * 4)
    {
        file.Close();
        return strText;
    }

    DWORD dwLen = (DWORD)ullLen;
    char* pszBuffer = new char[dwLen + 1];
    ZeroMemory(pszBuffer, dwLen + 1);

    try
    {
        file.Read(pszBuffer, dwLen);
    }
    catch (CFileException* e)
    {
        e->Delete();
        delete[] pszBuffer;
        file.Close();
        return strText;
    }
    file.Close();

    const char* pszContent = pszBuffer;
    if (dwLen >= 3 && (BYTE)pszBuffer[0] == 0xEF && (BYTE)pszBuffer[1] == 0xBB && (BYTE)pszBuffer[2] == 0xBF)
        pszContent = pszBuffer + 3;

#ifdef _UNICODE
    int nWideLen = MultiByteToWideChar(CP_UTF8, 0, pszContent, -1, NULL, 0);
    if (nWideLen > 1)
    {
        LPWSTR pszWide = new WCHAR[nWideLen + 1];
        ZeroMemory(pszWide, (nWideLen + 1) * sizeof(WCHAR));
        MultiByteToWideChar(CP_UTF8, 0, pszContent, -1, pszWide, nWideLen);
        strText = pszWide;
        delete[] pszWide;
    }
    else
    {
        strText = CString(pszContent);
    }
#else
    strText = pszContent;
#endif

    delete[] pszBuffer;
    return strText;
}

// JSON 텍스트에서 특정 키의 문자열 값을 간이 파싱으로 추출한다.
CString CGameInstallSearchCommon::ExtractJsonStringValue(const CString& strText, LPCTSTR lpszKey)
{
    CString strPattern;
    strPattern.Format(_T("\"%s\""), lpszKey);

    int nKey = strText.Find(strPattern);
    if (nKey < 0)
        return _T("");

    int nColon = strText.Find(_T(":"), nKey + strPattern.GetLength());
    if (nColon < 0)
        return _T("");

    int nStart = strText.Find(_T("\""), nColon + 1);
    if (nStart < 0)
        return _T("");

    int nEnd = strText.Find(_T("\""), nStart + 1);
    if (nEnd < 0)
        return _T("");

    CString strValue = strText.Mid(nStart + 1, nEnd - nStart - 1);
    strValue.Replace(_T("\\/"), _T("/"));
    strValue.Replace(_T("\\\\"), _T("\\"));
    return strValue;
}

// Steam ACF(VDF 형식) 텍스트에서 특정 키의 값을 추출한다.
CString CGameInstallSearchCommon::ExtractSteamAcfValue(const CString& strText, LPCTSTR lpszKey)
{
    CString strPattern;
    strPattern.Format(_T("\"%s\""), lpszKey);

    int nKey = strText.Find(strPattern);
    if (nKey < 0)
        return _T("");

    int nStart = strText.Find(_T("\""), nKey + strPattern.GetLength());
    if (nStart < 0)
        return _T("");

    int nEnd = strText.Find(_T("\""), nStart + 1);
    if (nEnd < 0)
        return _T("");

    return strText.Mid(nStart + 1, nEnd - nStart - 1);
}

// A~Z 드라이브(FIXED·REMOTE)에서 상대경로 목록을 순회하여 첫 번째 발견 경로를 반환한다.
// 목록은 NULL 포인터로 종료되어야 한다.
CString CGameInstallSearchCommon::SearchFileOnAllDrives(LPCTSTR const* pszRelPaths)
{
    DWORD dwMask = GetLogicalDrives();
    for (int nDrive = 0; nDrive < 26; ++nDrive)
    {
        if ((dwMask & (1 << nDrive)) == 0)
            continue;

        CString strRoot;
        strRoot.Format(_T("%c:\\"), (TCHAR)('A' + nDrive));

        UINT nType = GetDriveType(strRoot);
        if (nType != DRIVE_FIXED && nType != DRIVE_REMOTE)
            continue;

        for (int i = 0; pszRelPaths[i] != NULL; ++i)
        {
            CString strFull = JoinPath(strRoot, pszRelPaths[i]);
            if (FileExists(strFull))
                return strFull;
        }
    }

    return _T("");
}

// EXE 파일의 VERSIONINFO 리소스에서 버전 문자열("X.X.X.X")을 반환한다.
CString CGameInstallSearchCommon::GetExeFileVersion(LPCTSTR lpszExePath)
{
    CString strVersion;

    DWORD dwHandle = 0;
    DWORD dwSize = GetFileVersionInfoSize(lpszExePath, &dwHandle);
    if (dwSize == 0)
        return strVersion;

    BYTE* pBuffer = new BYTE[dwSize];
    ZeroMemory(pBuffer, dwSize);

    if (GetFileVersionInfo(lpszExePath, dwHandle, dwSize, pBuffer))
    {
        VS_FIXEDFILEINFO* pInfo = NULL;
        UINT nLen = 0;
        if (VerQueryValue(pBuffer, _T("\\"), (LPVOID*)&pInfo, &nLen) && pInfo != NULL)
        {
            strVersion.Format(_T("%u.%u.%u.%u"),
                HIWORD(pInfo->dwFileVersionMS),
                LOWORD(pInfo->dwFileVersionMS),
                HIWORD(pInfo->dwFileVersionLS),
                LOWORD(pInfo->dwFileVersionLS));
        }
    }

    delete[] pBuffer;
    return strVersion;
}

// 넷마블 런처를 통해 게임을 실행한다.
// 런처(m_strLauncherPath)가 존재하면 런처를 기동하고,
// 런처가 없으면 EXE를 직접 실행한다.
BOOL CGameInstallSearchCommon::LaunchNetmarble(const CGameInstallInfo& info, DWORD* pdwProcessId)
{
    if (pdwProcessId)
        *pdwProcessId = 0;

    AppLog(_T("LaunchNetmarble"), _T("type=%s launcher=%s exe=%s"),
        (LPCTSTR)info.m_strTypeName,
        (LPCTSTR)info.m_strLauncherPath,
        (LPCTSTR)info.m_strExePath);

    // 넷마블 런처가 있으면 런처를 기동한다 (정식 설치 경로)
    if (!info.m_strLauncherPath.IsEmpty() && FileExists(info.m_strLauncherPath))
    {
        AppLog(_T("LaunchNetmarble"), _T("via launcher=%s"), (LPCTSTR)info.m_strLauncherPath);
        HINSTANCE hInst = ShellExecute(NULL, _T("open"), info.m_strLauncherPath, NULL, NULL, SW_SHOWNORMAL);
        BOOL bOk = ((INT_PTR)hInst > 32);
        AppLog(_T("LaunchNetmarble"), _T("ShellExecute result=%s"), bOk ? _T("OK") : _T("FAIL"));
        return bOk;
    }

    // 런처 없음 — EXE 직접 실행
    if (info.m_bExeExists)
    {
        AppLog(_T("LaunchNetmarble"), _T("no launcher, direct exe=%s"), (LPCTSTR)info.m_strExePath);
        return LaunchExeDirect(info.m_strExePath, info.m_strInstallPath, pdwProcessId);
    }

    AppLog(_T("LaunchNetmarble"), _T("FAIL: no launcher and no exe"));
    return FALSE;
}

// 게임을 실행한다.
// bDirect=FALSE: 런처 경유(정상 실행) / bDirect=TRUE: EXE 직접 실행(진단용).
// Netmarble 타입은 내부적으로 LaunchNetmarble()을 호출한다.
BOOL CGameInstallSearchCommon::LaunchGame(const CGameInstallInfo& info, BOOL bDirect, DWORD* pdwProcessId)
{
    if (pdwProcessId)
        *pdwProcessId = 0;

    AppLog(_T("LaunchGame"), _T("platform=%s mode=%s"), (LPCTSTR)info.m_strTypeName, bDirect ? _T("Direct EXE") : _T("Launcher"));

    if (bDirect)
    {
        AppLog(_T("LaunchGame"), _T("direct exe=%s"), (LPCTSTR)info.m_strExePath);
        return LaunchExeDirect(info.m_strExePath, info.m_strInstallPath, pdwProcessId);
    }

    // 넷마블: 전용 런처 함수로 처리
    if (info.m_eType == GAME_INSTALL_NETMARBLE)
        return LaunchNetmarble(info, pdwProcessId);

    // 프로토콜 URL 실행 (Steam, Epic)
    if (!info.m_strLaunchCommand.IsEmpty())
    {
        AppLog(_T("LaunchGame"), _T("protocol command=%s"), (LPCTSTR)info.m_strLaunchCommand);
        HINSTANCE hInst = ShellExecute(NULL, _T("open"), info.m_strLaunchCommand, NULL, NULL, SW_SHOWNORMAL);
        BOOL bOk = ((INT_PTR)hInst > 32);
        AppLog(_T("LaunchGame"), _T("ShellExecute result=%s"), bOk ? _T("OK") : _T("FAIL"));
        return bOk;
    }

    AppLog(_T("LaunchGame"), _T("FAIL: no launcher available platform=%s"), (LPCTSTR)info.m_strTypeName);
    return FALSE;
}

// EXE를 ShellExecuteEx로 직접 실행하고 프로세스 ID를 채운다.
BOOL CGameInstallSearchCommon::LaunchExeDirect(LPCTSTR lpszExePath, LPCTSTR lpszInstallPath, DWORD* pdwProcessId)
{
    if (!FileExists(lpszExePath))
    {
        AppLog(_T("LaunchExeDirect"), _T("FAIL: exe not found path=%s"), lpszExePath);
        return FALSE;
    }

    SHELLEXECUTEINFO sei;
    ZeroMemory(&sei, sizeof(sei));
    sei.cbSize = sizeof(sei);
    sei.fMask = SEE_MASK_NOCLOSEPROCESS;
    sei.lpVerb = _T("open");
    sei.lpFile = lpszExePath;
    sei.lpDirectory = (lpszInstallPath && lpszInstallPath[0]) ? lpszInstallPath : NULL;
    sei.nShow = SW_SHOWNORMAL;

    BOOL bRet = ShellExecuteEx(&sei);
    if (bRet && sei.hProcess)
    {
        if (pdwProcessId)
		{
            *pdwProcessId = GetProcessId(sei.hProcess);
		}

        AppLog(_T("LaunchExeDirect"), _T("OK pid=%u exe=%s"), GetProcessId(sei.hProcess), lpszExePath);
        
		CloseHandle(sei.hProcess);
    }
    else
    {
        AppLog(_T("LaunchExeDirect"), _T("FAIL ShellExecuteEx exe=%s"), lpszExePath);
    }

    return bRet;
}
