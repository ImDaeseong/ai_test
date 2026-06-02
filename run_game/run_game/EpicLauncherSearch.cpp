#include "stdafx.h"
#include "EpicLauncherSearch.h"
#include "AppLog.h"

// Epic Games 플랫폼에서 게임 설치 정보를 탐지한다.
// 탐지 순서: 레지스트리(ModSdkCommand) → 드라이브 전수 탐색 → ProgramData .item 매니페스트 파싱
// gameInfo: 탐지 대상 게임 설정 정보 (참조로 보관, 호출자의 수명과 동일해야 한다)
CEpicLauncherSearch::CEpicLauncherSearch(const CGameInfo& gameInfo) : m_GameInfo(gameInfo)
{
}

// Epic 설치 정보를 수집하여 info를 채운다.
// 런치 URL(m_strLaunchCommand) 구성에 성공한 경우에만 TRUE를 반환한다.
BOOL CEpicLauncherSearch::Search(CGameInstallInfo& info)
{
    CString strLauncher;
    CString strInstallPath;
    CString strVersion;
    CString strLaunchCommand;
    CString strAppId;

    TCHAR szProgramData[MAX_PATH] = {0};
    GetEnvironmentVariable(_T("ProgramData"), szProgramData, MAX_PATH);

    CString strManifestDir = CGameInstallSearchCommon::JoinPath(szProgramData[0] ? szProgramData : _T("C:\\ProgramData"), _T("Epic\\EpicGamesLauncher\\Data\\Manifests"));

    if (!CGameInstallSearchCommon::ReadStringValue(HKEY_CURRENT_USER, _T("SOFTWARE\\Epic Games\\EOS"), _T("ModSdkCommand"), strLauncher))
        strLauncher.Empty();

    if (strLauncher.IsEmpty())
    {
        static LPCTSTR s_pszEpicRel[] = {
            _T("Program Files (x86)\\Epic Games\\Launcher\\Portal\\Binaries\\Win32\\EpicGamesLauncher.exe"),
            _T("Program Files\\Epic Games\\Launcher\\Portal\\Binaries\\Win64\\EpicGamesLauncher.exe"),
            _T("Epic Games\\Launcher\\Portal\\Binaries\\Win64\\EpicGamesLauncher.exe"),
            NULL
        };
        strLauncher = CGameInstallSearchCommon::SearchFileOnAllDrives(s_pszEpicRel);
    }

    WIN32_FIND_DATA findData;
    CString strFind = CGameInstallSearchCommon::JoinPath(strManifestDir, _T("*.item"));
    HANDLE hFind = FindFirstFile(strFind, &findData);
    if (hFind != INVALID_HANDLE_VALUE)
    {
        // TRY/CATCH로 감싸 ReadTextFile 등에서 예외 발생 시에도 FindClose가 반드시 호출되도록 한다.
        TRY
        {
            do
            {
                if ((findData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) == 0)
                {
                    CString strManifestPath = CGameInstallSearchCommon::JoinPath(strManifestDir, findData.cFileName);
                    CString strText = CGameInstallSearchCommon::ReadTextFile(strManifestPath);
                    CString strLaunchExe = CGameInstallSearchCommon::ExtractJsonStringValue(strText, _T("LaunchExecutable"));
                    CString strFoundInstall = CGameInstallSearchCommon::ExtractJsonStringValue(strText, _T("InstallLocation"));

                    if (strLaunchExe.CompareNoCase(m_GameInfo.m_strExeName) == 0 || (!m_GameInfo.m_strEpicManifestKeyword.IsEmpty() && strText.Find(m_GameInfo.m_strEpicManifestKeyword) >= 0))
                    {
                        if (!strFoundInstall.IsEmpty())
                            strInstallPath = strFoundInstall;

                        strVersion = CGameInstallSearchCommon::ExtractJsonStringValue(strText, _T("AppVersionString"));
                        strAppId = CGameInstallSearchCommon::ExtractJsonStringValue(strText, _T("CatalogItemId"));

                        CString strNs = CGameInstallSearchCommon::ExtractJsonStringValue(strText, _T("CatalogNamespace"));
                        CString strAppName = CGameInstallSearchCommon::ExtractJsonStringValue(strText, _T("AppName"));

                        if (!strNs.IsEmpty() && !strAppId.IsEmpty() && !strAppName.IsEmpty())
                        {
                            strLaunchCommand.Format(_T("com.epicgames.launcher://apps/%s%%3A%s%%3A%s?action=launch&silent=true"), (LPCTSTR)strNs, (LPCTSTR)strAppId, (LPCTSTR)strAppName);
                        }
                        break;
                    }
                }
            }
            while (FindNextFile(hFind, &findData));
        }
        CATCH_ALL(e)
        {
            e->Delete();
        }
        END_CATCH_ALL

        FindClose(hFind);
    }

    CString strExePath = CGameInstallSearchCommon::JoinPath(strInstallPath, m_GameInfo.m_strExeName);

    info.m_eType = GAME_INSTALL_EPIC;
    info.m_strTypeName = CGameInstallSearchCommon::GetInstallTypeName(info.m_eType);
    info.m_strInstallPath = CGameInstallSearchCommon::NormalizePath(strInstallPath);
    info.m_strExePath = CGameInstallSearchCommon::NormalizePath(strExePath);
    info.m_strLauncherPath = CGameInstallSearchCommon::NormalizePath(strLauncher);
    info.m_strLaunchCommand = strLaunchCommand;
    info.m_strVersion = strVersion;
    info.m_strAppId = strAppId;
    info.m_strSource = _T("HKCU\\SOFTWARE\\Epic Games\\EOS, ProgramData Epic manifest");
    info.m_bInstalled = CGameInstallSearchCommon::DirectoryExists(info.m_strInstallPath);
    info.m_bExeExists = CGameInstallSearchCommon::FileExists(info.m_strExePath);

    BOOL bResult = !info.m_strLaunchCommand.IsEmpty();

    AppLog(_T("CEpicLauncherSearch::Search"), _T("result=%s installed=%s exeExists=%s"), bResult ? _T("FOUND") : _T("NOT FOUND"),info.m_bInstalled ? _T("YES") : _T("NO"), info.m_bExeExists ? _T("YES") : _T("NO"));
    AppLog(_T("CEpicLauncherSearch::Search"), _T("launcher=%s"), (LPCTSTR)info.m_strLauncherPath);
    AppLog(_T("CEpicLauncherSearch::Search"), _T("install =%s"), (LPCTSTR)info.m_strInstallPath);
    AppLog(_T("CEpicLauncherSearch::Search"), _T("exe     =%s"), (LPCTSTR)info.m_strExePath);
    AppLog(_T("CEpicLauncherSearch::Search"), _T("command =%s"), (LPCTSTR)info.m_strLaunchCommand);
    AppLog(_T("CEpicLauncherSearch::Search"), _T("appId   =%s version=%s"), (LPCTSTR)info.m_strAppId, (LPCTSTR)info.m_strVersion);
    
    return bResult;
}
